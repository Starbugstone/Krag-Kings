# Host crash investigation — 5 October 2026

Status: cause not yet established. The user chose to continue without dump analysis for now. Preserve this distinction from observed application memory exhaustion.

## Evidence

- Windows System event 1001 at 22:13:07 CEST records bugcheck `0x000000EF`, parameters `ffff808683d62080, 0, ffff808683d62080, 0`, and `C:\Windows\Minidump\100526-21937-01.dmp`.
- Boot was recorded at 22:12:45 CEST. Event 6008 reports an unexpected previous shutdown at 21:57:44. Saved application output continued around 22:00, so that timestamp alone does not establish the exact failure sequence.
- [Microsoft defines 0xEF as CRITICAL_PROCESS_DIED](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0xef--critical-process-died). Parameter 2 being zero means a process terminated. Identifying that process and its failing dependency requires dump analysis.
- The Nib Blender generation/export/render log contains explicit `Error: out of memory` messages. Several heavy application tasks had overlapped. This is a concrete pipeline defect and a possible contributor; it is not proof of the Windows kernel failure's root cause.
- Unity's first startup timed out connecting to its package manager. A retry connected, resolved the correct license client, then ended with a disconnected package-manager stream and cancelled package resolution. No playable Unity build or benchmark completed.
- Post-reboot Windows Error Reporting flushed older GPU watchdog/blue-screen reports dated September and earlier. Those are not evidence of a new GPU error during this incident.
- Minidump reading is denied to the current session. The user deferred copying/analysis and asked work to continue. Microsoft-signed debugging tools are available locally if analysis is resumed. System-event extracts are retained locally, not committed with machine-identifying diagnostic data.

## Workflow correction

Run only one heavy job at a time. Split Blender source generation, export and rendering into fresh processes; consolidate runtime meshes without discarding editable source detail. Avoid retaining exporter copies while rendering. Use four CPU render threads for the next checks.

`tools/Run-HeavyTask.ps1` serializes benchmark heavy jobs through a mutex and logs memory. It requires 10 GiB available memory and no more than 75% system commit before starting. It terminates its own task tree if available memory falls below 2 GiB, commit exceeds 90%, or the configured per-task private-memory limit is exceeded. This is a workload guard, not a fix or diagnosis of Windows/driver stability.

Do not modify BIOS, drivers, Windows protections or system services based on this stop code alone. Resume saved work under the bounded workflow while collecting the missing diagnostic evidence.
