[CmdletBinding()]
param([ValidateSet('Full','Balanced')][string]$Quality='Balanced')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$executable=Join-Path $repo 'benchmark\builds\Unity\KragKings-Unity.exe'
if(-not(Test-Path -LiteralPath $executable)){throw 'Build the Windows Unity demo before recording.'}
$run=Join-Path $repo ('benchmark\local\evidence\unity-recording\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+$PID)
New-Item -ItemType Directory $run|Out-Null
$stdout=Join-Path $run 'launcher-stdout.log'
$stderr=Join-Path $run 'launcher-stderr.log'
$report=[ordered]@{engine='Unity';quality=$Quality;startedUtc=[DateTime]::UtcNow.ToString('o');completed=$false;artisticAcceptance=$false;performanceMeasurement=$false}
$launcher=$null;$game=$null;$evidence=$null
try {
    $script=Join-Path $PSScriptRoot 'Run-Demo.ps1'
    $launcher=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-Mode','Showcase','-Quality',$Quality) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
    $null=$launcher.Handle
    $deadline=[DateTime]::UtcNow.AddSeconds(150)
    do {
        if(Test-Path $stdout){
            $logText=[string](Get-Content $stdout -Raw)
            $pathMatch=[regex]::Match($logText,'(?m)^UNITY_EVIDENCE_DIR (.+)\r?$')
            if($pathMatch.Success){$evidence=$pathMatch.Groups[1].Value.Trim()}
            $processMatch=[regex]::Match($logText,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
            if($processMatch.Success){$game=Get-Process -Id ([int]$processMatch.Groups[1].Value) -ErrorAction SilentlyContinue}
        }
        if($launcher.HasExited){throw 'The guarded game launcher exited before showcase readiness; inspect its logs.'}
        if($game -and $evidence -and (Test-Path (Join-Path $evidence 'showcase-ready.json'))){break}
        if([DateTime]::UtcNow -gt $deadline){throw 'The guarded game did not report showcase readiness within 150 seconds.'}
        Start-Sleep -Milliseconds 200
    }while($true)
    if($game.Path -ne $executable){throw 'The guard PID does not identify the intended Unity executable.'}
    $report.gameProcessId=$game.Id;$report.runtimeEvidence=$evidence
    Write-Output ('UNITY_RECORDING_EVIDENCE '+$evidence)
    $capture=Join-Path $evidence 'capture-wgc'
    & (Join-Path $PSScriptRoot '..\capture\Capture-Demo.ps1') -Engine Unity -GameProcessId $game.Id -RuntimeLog (Join-Path $evidence 'player.log') -StartFlag (Join-Path $evidence 'showcase-start.flag') -EngineAudio (Join-Path $evidence 'showcase-engine-audio.wav') -OutputDirectory $capture
    $captureReport=Get-Content (Join-Path $capture 'unity-showcase-capture.json') -Raw|ConvertFrom-Json
    if(-not $captureReport.completed){throw 'The recorder did not complete its media checks.'}
    $framing=Get-Content (Join-Path $evidence 'showcase-framing.json') -Raw|ConvertFrom-Json
    $report.video=$captureReport.output;$report.videoSha256=$captureReport.outputSha256
    $report.buildGuid=$framing.buildGuid;$report.contentFingerprint=$framing.contentFingerprint
    $report.framing=$framing;$report.completed=$true
    Write-Output ('UNITY_RECORDING_COMPLETE '+$captureReport.output)
    if(-not $framing.passed){Write-Warning 'The actual wide-view framing check failed. Media is retained for correction and visual review.'}
} catch {$report.error=$_.Exception.Message;throw} finally {
    # Close only the game launched by this invocation. Never close an editor or
    # an unrelated process to obtain foreground or release the heavy-task slot.
    if($game){
        try{
            if(-not $game.HasExited -and $game.Path -eq $executable){
                $game.CloseMainWindow()|Out-Null
                $report.gameClosed=$game.WaitForExit(15000)
            }else{$report.gameClosed=$true}
        }catch{$report.gameCloseError=$_.Exception.Message}
    }
    if($launcher){
        $finished=$launcher.WaitForExit(20000)
        if($finished){$launcher.Refresh();$report.launcherExitCode=$launcher.ExitCode}
        else{$report.launcherStillRunning=$true}
    }
    foreach($kind in @('memory','gpu')){
        $telemetry=Join-Path $repo ('benchmark\local\unity-runtime-showcase-'+$kind+'.csv')
        if($game -and (Test-Path $telemetry)){Copy-Item $telemetry (Join-Path $run ($kind+'.csv'))}
    }
    $report.finishedUtc=[DateTime]::UtcNow.ToString('o')
    $report|ConvertTo-Json -Depth 10|Set-Content (Join-Path $run 'recording-result.json') -Encoding UTF8
    Write-Output ('UNITY_RECORDING_REPORT '+(Join-Path $run 'recording-result.json'))
}
