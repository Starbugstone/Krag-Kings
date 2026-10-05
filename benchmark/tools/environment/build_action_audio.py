"""Prepare candidate action sounds from preserved CC0 recordings.

Separate light pistol/heavy report; no voice synthesis or third-party music.
The deterministic crop removes leading silence and other shots in the source.
"""
from pathlib import Path
import array, hashlib, json, shutil, subprocess, wave

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'benchmark/art/audio/combat'
OUT = ROOT / 'benchmark/shared/audio'
FFMPEG = shutil.which('ffmpeg')
if not FFMPEG:
    raise RuntimeError('FFmpeg is required')
OUT.mkdir(parents=True, exist_ok=True)

def decode(path):
    data = subprocess.check_output([FFMPEG, '-hide_banner', '-loglevel', 'error', '-i', str(path),
        '-af', 'pan=mono|c0=0.5*c0+0.5*c1' if path.suffix == '.wav' else 'anull',
        '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'])
    samples = array.array('f'); samples.frombytes(data)
    return samples

recipes = [
    ('Krag_Shot', 'FreeFirearm_K17.wav', True, 2.3, 'asetrate=40800,aresample=48000,highpass=f=45,bass=g=3:f=100:w=0.8'),
    ('Nib_Shot', 'FreeFirearm_A42.wav', True, 1.6, 'highpass=f=110'),
    ('Krag_Hit', 'impactPunch_heavy_000.ogg', False, .9, 'asetrate=43200,aresample=48000,highpass=f=45'),
    ('Nib_Hit', 'impactSoft_medium_000.ogg', False, .65, 'highpass=f=110'),
]
manifest = {'schemaVersion': 1, 'status': 'Candidate action effects; actual game mix and listening review pending',
    'source': '../../../art/audio/combat/source.json', 'sampleRate': 48000, 'channels': 1,
    'timing': 'Shots use each character weapon.fireTimesNormalized; Hit uses normalized 0.22, provisional tuning.', 'effects': []}
for name, source_name, shot, duration, filters in recipes:
    source = SOURCE / source_name
    samples = decode(source)
    threshold = .12 if shot else .015
    onset = next((i for i, value in enumerate(samples) if abs(value) > threshold), None)
    if onset is None:
        raise RuntimeError(f'No onset found: {source}')
    start = max(0, onset / 48000 - .006)
    fade = max(.02, duration - .16)
    recipe = f'atrim=start={start:.6f}:duration={duration},asetpts=PTS-STARTPTS,{filters},afade=t=out:st={fade}:d=0.16,alimiter=limit=0.72:level=false:latency=true'
    path = OUT / (name + '.wav')
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
        '-af', 'pan=mono|c0=0.5*c0+0.5*c1,'+recipe if source.suffix=='.wav' else recipe,
        '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', str(path)], check=True)
    with wave.open(str(path)) as handle:
        params = handle.getparams(); pcm = array.array('h'); pcm.frombytes(handle.readframes(handle.getnframes()))
    peak = max(abs(value) for value in pcm) / 32768
    if peak >= .999 or params.nchannels != 1 or params.framerate != 48000:
        raise RuntimeError(f'Invalid output: {path}')
    manifest['effects'].append({'name': name, 'file': path.name, 'source': source_name,
        'sourceOnsetSeconds': onset/48000, 'filterRecipe': recipe,
        'durationSeconds': params.nframes/params.framerate, 'peakLinear': peak,
        'runtimeGain': .55 if shot else .6, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'action-audio.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('ACTION_AUDIO_READY', len(manifest['effects']))
