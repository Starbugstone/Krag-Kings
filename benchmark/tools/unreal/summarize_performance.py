"""Archive completed native runs and summarize only sampled-window telemetry."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def summarize(run, output, timezone):
    result_path = run / "run-result-recovered.json"
    if not result_path.exists():
        result_path = run / "run-result.json"
    result = read_json(result_path)
    if not result.get("comparisonComplete"):
        raise ValueError(f"Run is incomplete: {run}")
    metrics = result["metrics"]
    if not metrics["completed_sample_window"]:
        raise ValueError(f"Native sample window is incomplete: {run}")
    mode = result["mode"].lower()
    name = f"{result['profile'].lower()}-{mode}"
    target = output / name
    target.mkdir(parents=True, exist_ok=True)
    for filename in (result_path.name, "run-conditions.json", "package-result.json", "job.json", "gpu.csv", "memory.csv", f"performance-{mode}.json", f"performance-{mode}-frames.csv"):
        # Keep native originals untouched; archive semantic text with canonical
        # LF/UTF-8 so these evidence hashes survive Git's line-ending handling.
        (target / filename).write_text((run / filename).read_text(encoding="utf-8-sig"), encoding="utf-8")
    log = (run / "runtime.log").read_text(encoding="utf-8-sig")
    match = re.search(r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\].*KK_READY", log)
    if not match:
        raise ValueError(f"Missing native readiness timestamp: {run}")
    ready = dt.datetime.strptime(match[1], "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=dt.timezone.utc)
    start = ready + dt.timedelta(seconds=15)
    end = ready + dt.timedelta(seconds=45)
    gpu = []
    with (run / "gpu.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            stamp = dt.datetime.strptime(row["timestamp"].strip(), "%Y/%m/%d %H:%M:%S.%f").replace(tzinfo=timezone)
            if start <= stamp <= end:
                gpu.append(row)
    ranges = {}
    for field in ("memory.used.MiB", "utilization.gpu.percent", "temperature.gpu.C", "power.draw.W", "clocks.current.graphics.MHz"):
        values = [float(row[field]) for row in gpu]
        ranges[field] = {"min": min(values), "max": max(values), "first": values[0], "last": values[-1]} if values else None
    with (run / "memory.csv").open(encoding="utf-8-sig", newline="") as stream:
        memory = [row for row in csv.DictReader(stream) if start <= dt.datetime.fromisoformat(row["time"]) <= end]
    conditions = read_json(run / "run-conditions.json")
    archived = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}
    return {
        "name": name, "sourceRun": str(run), "metrics": metrics,
        "runConditions": conditions, "nativeExeSha256": result["exeSha256"],
        "guardExit": result["guardExit"], "foregroundAcquiredUtc": result["foregroundAcquiredUtc"],
        "windowLeaseRestored": result["windowLeaseRestored"],
        "telemetryWindow": {"approximateStartUtc": start.isoformat(), "approximateEndUtc": end.isoformat(),
                            "derivation": "Native KK_READY log timestamp +15 to +45 seconds; BenchmarkStartTime is assigned immediately before this log. Native monotonic sample times remain authoritative.",
                            "nvidiaTimestampTimezone": str(timezone), "gpuSampleCount": len(gpu), "gpuDeviceWideRanges": ranges,
                            "peakGamePrivateMiB": max(float(row["privateMB"]) for row in memory) if memory else None},
        "archivedFileSha256": archived, "archiveRepresentation": "UTF-8 without BOM, LF; native originals remain in sourceRun",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu-timezone", default="Europe/Paris")
    parser.add_argument("--source-fingerprint", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = [summarize(path, args.output, ZoneInfo(args.gpu_timezone)) for path in args.run]
    payload = {
        "engine": "Unreal", "sourceFingerprintCompatibleWithUnity": args.source_fingerprint,
        "source": "Actual packaged Windows native1080p runs; no screenshots/state writes during sampling",
        "artisticAcceptance": False, "locked60FpsClaim": False, "engineWinnerClaim": False,
        "limitations": ["One short sample per profile/workload, not a sustained thermal equilibrium test.",
                        "Laptop clocks and thermals vary; telemetry is device-wide, not process-attributed.",
                        "Full vs Balanced changes only software Lumen GI/reflections from Epic to High; native pixels remain unchanged.",
                        "Moving measurements include animation, movement, effects and game audio.",
                        "Current generic subsurface skin and character art remain visually unaccepted."],
        "runs": rows,
    }
    (args.output / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        m = row["metrics"]
        print(f"{row['name']}: {m['average_fps']:.3f} FPS, p95 {m['p95_frame_ms']:.3f} ms; {row['telemetryWindow']['gpuSampleCount']} GPU samples")


if __name__ == "__main__":
    main()
