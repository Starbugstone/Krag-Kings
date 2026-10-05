param([Parameter(Mandatory=$true)][string]$JobSpec)
$ErrorActionPreference='Stop'
$spec=Get-Content -Raw $JobSpec | ConvertFrom-Json
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$local=Join-Path $repo 'benchmark\local'
New-Item -ItemType Directory -Force $local | Out-Null
function Preserve-PreviousTelemetry([string]$Path) {
    if(Test-Path $Path){
        $history=Join-Path $local 'telemetry-history'
        New-Item -ItemType Directory -Force $history | Out-Null
        $file=Get-Item $Path
        $name=$file.BaseName+'-'+$file.LastWriteTimeUtc.ToString('yyyyMMdd-HHmmss-fffffff')+$file.Extension
        Copy-Item -LiteralPath $Path -Destination (Join-Path $history $name) -ErrorAction Stop
    }
}
$mutex=New-Object System.Threading.Mutex($false,'Local\KragKingsBenchmarkHeavyJob')
$locked=$false
try {
    try { $locked=$mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $locked=$true }
    if(-not $locked) { throw 'Another benchmark heavy job is running. Queue this task; do not launch a parallel renderer/editor.' }
    $memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $minimum=if($spec.minAvailableGB){[double]$spec.minAvailableGB}else{10.0}
    if($memory.AvailableMBytes -lt ($minimum*1024) -or $memory.PercentCommittedBytesInUse -gt 75) { throw ('Not enough memory headroom to start: availableMB='+$memory.AvailableMBytes+' commit='+$memory.PercentCommittedBytesInUse+'%') }
    $maxPrivate=if($spec.maxPrivateGB){[double]$spec.maxPrivateGB}else{10.0}
    $quoted=@($spec.arguments | ForEach-Object { if($_ -match '[\s"]') { '"'+($_ -replace '"','\"')+'"' } else { $_ } })
    $params=@{FilePath=$spec.executable;ArgumentList=$quoted;PassThru=$true}
    if($spec.workingDirectory){$params.WorkingDirectory=$spec.workingDirectory}
    if($spec.stdout){$params.RedirectStandardOutput=$spec.stdout}
    if($spec.stderr){$params.RedirectStandardError=$spec.stderr}
    $gpuTool=$null
    if($spec.gpuTelemetry){$gpuTool=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue}
    $gpuLog=Join-Path $local (($spec.name -replace '[^a-zA-Z0-9_-]','_')+'-gpu.csv')
    if($gpuTool){
        Preserve-PreviousTelemetry $gpuLog
        'phase,timestamp,index,name,memory.used.MiB,memory.total.MiB,utilization.gpu.percent,temperature.gpu.C,power.draw.W,clocks.current.graphics.MHz' | Set-Content $gpuLog
        & $gpuTool.Source --query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,clocks.current.graphics --format=csv,noheader,nounits | ForEach-Object {('before,'+$_)|Add-Content $gpuLog}
    }
    $safeName=$spec.name -replace '[^a-zA-Z0-9_-]','_'
    $telemetry=Join-Path $local ($safeName+'-memory.csv')
    Preserve-PreviousTelemetry $telemetry
    'time,processId,availableMB,commitPercent,privateMB,workingSetMB' | Set-Content $telemetry
    $process=Start-Process @params
    # Cache the native handle before the process can exit, so ExitCode remains readable.
    $null=$process.Handle
    try {$process.PriorityClass='BelowNormal'} catch {}
    Write-Output ('HEAVY_JOB_STARTED '+$safeName+' PID='+$process.Id)
    $terminated=$false
    while(-not $process.HasExited) {
        $process.Refresh()
        $memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
        $privateMB=[math]::Round($process.PrivateMemorySize64/1MB)
        $workingMB=[math]::Round($process.WorkingSet64/1MB)
        ((Get-Date).ToString('o')+','+$process.Id+','+$memory.AvailableMBytes+','+$memory.PercentCommittedBytesInUse+','+$privateMB+','+$workingMB) | Add-Content $telemetry
        if($gpuTool){
            & $gpuTool.Source --query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,clocks.current.graphics --format=csv,noheader,nounits | ForEach-Object {('running,'+$_)|Add-Content $gpuLog}
        }
        if(-not $process.HasExited -and ($memory.AvailableMBytes -lt 2048 -or $memory.PercentCommittedBytesInUse -gt 90 -or $privateMB -gt ($maxPrivate*1024))) {
            Write-Output ('HEAVY_JOB_MEMORY_LIMIT availableMB='+$memory.AvailableMBytes+' commit='+$memory.PercentCommittedBytesInUse+'% privateMB='+$privateMB)
            & taskkill.exe /PID $process.Id /T /F | Out-Null
            $terminated=$true
            break
        }
        Start-Sleep -Seconds 3
    }
    $process.WaitForExit()
    if($terminated){exit 88}
    if($null -eq $process.ExitCode){throw 'Task ended but its exit code was unavailable; inspect the task log before treating it as successful.'}
    Write-Output ('HEAVY_JOB_FINISHED '+$safeName+' exit='+$process.ExitCode)
    exit $process.ExitCode
} finally {
    if($locked){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
