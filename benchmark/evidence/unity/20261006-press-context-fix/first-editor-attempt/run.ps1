$ErrorActionPreference='Stop'
$repo='D:\Dev\Krag-Kings'
$plan=Get-Content -Raw (Join-Path $PSScriptRoot 'plan.json')|ConvertFrom-Json
foreach($file in $plan.sourceFiles.PSObject.Properties){
    if((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $file.Name)).Hash.ToLower() -ne $file.Value.sha256){throw ('Frozen Unity source changed: '+$file.Name)}
}
if(Test-Path (Join-Path $PSScriptRoot 'result.json')){throw 'Preserve the prior build result before another run.'}
$result=[ordered]@{scope=$plan.scope;startedUtc=[DateTime]::UtcNow.ToString('o');completed=$false;nativeWindowsInputSent=$false;artisticAcceptance=$false}
try {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repo 'benchmark\tools\Run-HeavyTask.ps1') -JobSpec (Join-Path $PSScriptRoot 'job.json') 2>&1 | Tee-Object -FilePath (Join-Path $PSScriptRoot 'guard.log')
    $result.guardExitCode=$LASTEXITCODE
    $events=Get-Content -Raw (Join-Path $PSScriptRoot 'queued-event-report.json')|ConvertFrom-Json
    $result.queuedEventsPassed=$events.completed
    $result.queuedEventCheckCount=@($events.checks).Count
    if($LASTEXITCODE -ne 0 -or -not $events.completed){throw 'Real queued-event verification or Windows build failed; inspect preserved logs.'}
    $result.completed=$true
} catch {$result.error=$_.Exception.Message;throw}
finally {
    $telemetry=Join-Path $repo 'benchmark\local\unity-press-context-build-memory.csv'
    if(Test-Path $telemetry){Copy-Item $telemetry (Join-Path $PSScriptRoot 'memory.csv')}
    $result.finishedUtc=[DateTime]::UtcNow.ToString('o')
    $result|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'result.json')
}
Write-Output 'UNITY_PRESS_CONTEXT_CHECK_AND_BUILD_COMPLETE'
