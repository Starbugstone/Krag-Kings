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
function Get-TaskProcessTree([int]$RootProcessId) {
    # Query identifiers only. Wrapper jobs include their compiler/cooker children;
    # ordinary direct game runs avoid this extra enumeration entirely.
    $links=@(Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId)
    $ids=[System.Collections.Generic.HashSet[int]]::new()
    $null=$ids.Add($RootProcessId)
    do {
        $added=$false
        foreach($link in $links){
            if($ids.Contains([int]$link.ParentProcessId) -and $ids.Add([int]$link.ProcessId)){$added=$true}
        }
    } while($added)
    @(Get-Process -Id @($ids) -ErrorAction SilentlyContinue)
}
function Get-TaskCompletionFailure([string]$Path,[string]$Marker) {
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){return 'Completion log was not created.'}
    if(-not(Select-String -LiteralPath $Path -Pattern $Marker -SimpleMatch -Quiet)){
        return ('Native process exited successfully, but required completion marker is absent: '+$Marker)
    }
    return $null
}
$hasCompletionLog=-not[string]::IsNullOrWhiteSpace([string]$spec.successLog)
$hasCompletionMarker=-not[string]::IsNullOrWhiteSpace([string]$spec.successMarker)
if($hasCompletionLog -ne $hasCompletionMarker){throw 'successLog and successMarker must be specified together.'}
$mutex=New-Object System.Threading.Mutex($false,'Local\KragKingsBenchmarkHeavyJob')
$locked=$false
try {
    try { $locked=$mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $locked=$true }
    if(-not $locked) { throw 'Another benchmark heavy job is running. Queue this task; do not launch a parallel renderer/editor.' }
    $memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $minimum=if($spec.minAvailableGB){[double]$spec.minAvailableGB}else{10.0}
    if($memory.AvailableMBytes -lt ($minimum*1024) -or $memory.PercentCommittedBytesInUse -gt 75) { throw ('Not enough memory headroom to start: availableMB='+$memory.AvailableMBytes+' commit='+$memory.PercentCommittedBytesInUse+'%') }
    $maxPrivate=if($spec.maxPrivateGB){[double]$spec.maxPrivateGB}else{10.0}
    $trackTree=[bool]$spec.trackProcessTree -or [bool]$spec.maxTreePrivateGB
    $maxTreePrivate=if($spec.maxTreePrivateGB){[double]$spec.maxTreePrivateGB}else{$maxPrivate}
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
    'time,processId,availableMB,commitPercent,privateMB,workingSetMB,treeTracked,treePrivateMB,treeWorkingSetMB,treeProcessCount' | Set-Content $telemetry
    if($hasCompletionLog){
        # This is an explicitly designated task output, not an arbitrary user log.
        # Archive and clear it before launch so a stale success token cannot pass.
        if(Test-Path -LiteralPath $spec.successLog){
            $history=Join-Path $local 'completion-log-history'
            New-Item -ItemType Directory -Force $history | Out-Null
            $previous=Get-Item -LiteralPath $spec.successLog
            $archive=$safeName+'-'+(Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fffffff')+'-'+$previous.Name
            Copy-Item -LiteralPath $spec.successLog -Destination (Join-Path $history $archive)
            Clear-Content -LiteralPath $spec.successLog
        }
    }
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
        $treePrivateMB=$privateMB;$treeWorkingMB=$workingMB;$treeCount=1
        if($trackTree){
            $members=@(Get-TaskProcessTree $process.Id)
            $treePrivateMB=[math]::Round(($members|Measure-Object -Property PrivateMemorySize64 -Sum).Sum/1MB)
            # Working sets may share pages; their sum is diagnostic, not unique RAM.
            $treeWorkingMB=[math]::Round(($members|Measure-Object -Property WorkingSet64 -Sum).Sum/1MB)
            $treeCount=$members.Count
        }
        ((Get-Date).ToString('o')+','+$process.Id+','+$memory.AvailableMBytes+','+$memory.PercentCommittedBytesInUse+','+$privateMB+','+$workingMB+','+$trackTree+','+$treePrivateMB+','+$treeWorkingMB+','+$treeCount) | Add-Content $telemetry
        if($gpuTool){
            & $gpuTool.Source --query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,clocks.current.graphics --format=csv,noheader,nounits | ForEach-Object {('running,'+$_)|Add-Content $gpuLog}
        }
        if(-not $process.HasExited -and ($memory.AvailableMBytes -lt 2048 -or $memory.PercentCommittedBytesInUse -gt 90 -or $privateMB -gt ($maxPrivate*1024) -or ($trackTree -and $treePrivateMB -gt ($maxTreePrivate*1024)))) {
            Write-Output ('HEAVY_JOB_MEMORY_LIMIT availableMB='+$memory.AvailableMBytes+' commit='+$memory.PercentCommittedBytesInUse+'% privateMB='+$privateMB+' treeTracked='+$trackTree+' treePrivateMB='+$treePrivateMB+' treeProcesses='+$treeCount)
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
    if($process.ExitCode -eq 0 -and $hasCompletionLog){
        $failure=Get-TaskCompletionFailure $spec.successLog $spec.successMarker
        if($failure){Write-Output ('HEAVY_JOB_COMPLETION_FAILED '+$failure);exit 89}
        Write-Output ('HEAVY_JOB_COMPLETION_VERIFIED '+$spec.successMarker)
    }
    exit $process.ExitCode
} finally {
    if($locked){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
