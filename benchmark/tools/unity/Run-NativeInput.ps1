[CmdletBinding()]
param([ValidateSet('Full','Balanced')][string]$Quality='Balanced')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$executable=Join-Path $repo 'benchmark\builds\Unity\KragKings-Unity.exe'
if(-not(Test-Path -LiteralPath $executable)){throw 'Build the Windows Unity demo before native input verification.'}
$run=Join-Path $repo ('benchmark\local\evidence\unity-native-input\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+$PID)
New-Item -ItemType Directory $run|Out-Null
$stdout=Join-Path $run 'launcher-stdout.log'
$stderr=Join-Path $run 'launcher-stderr.log'
$report=[ordered]@{engine='Unity';quality=$Quality;startedUtc=[DateTime]::UtcNow.ToString('o');completed=$false;artisticAcceptance=$false;performanceMeasurement=$false}
$launcher=$null;$game=$null;$evidence=$null
try {
    $script=Join-Path $PSScriptRoot 'Run-Demo.ps1'
    $launcher=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-Mode','Interactive','-Quality',$Quality) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
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
        if($launcher.HasExited){throw 'The guarded game launcher exited before native-input readiness; inspect its logs.'}
        if($game -and $evidence -and (Test-Path (Join-Path $evidence 'input-probe.json'))){break}
        if([DateTime]::UtcNow -gt $deadline){throw 'The guarded game did not report native-input readiness within 150 seconds.'}
        Start-Sleep -Milliseconds 200
    }while($true)
    if($game.Path -ne $executable){throw 'The guard PID does not identify the intended Unity executable.'}
    $report.gameProcessId=$game.Id;$report.runtimeEvidence=$evidence
    $initialProbe=Get-Content (Join-Path $evidence 'input-probe.json') -Raw|ConvertFrom-Json
    $report.buildGuid=$initialProbe.buildGuid;$report.contentFingerprint=$initialProbe.contentFingerprint
    Write-Output ('UNITY_NATIVE_INPUT_EVIDENCE '+$evidence)
    $verifier=Join-Path $run 'executed-Verify-WindowsInput.ps1'
    Copy-Item (Join-Path $PSScriptRoot 'Verify-WindowsInput.ps1') $verifier
    $report.verifierSha256=(Get-FileHash $verifier -Algorithm SHA256).Hash.ToLower()
    $windowHelper=Join-Path $run 'executed-OwnedGameWindow.ps1'
    Copy-Item (Join-Path $PSScriptRoot '..\capture\OwnedGameWindow.ps1') $windowHelper
    $report.windowHelperSha256=(Get-FileHash $windowHelper -Algorithm SHA256).Hash.ToLower()
    & $verifier -DemoProcessId $game.Id -EvidencePath $evidence -WindowHelperPath $windowHelper
    $inputResult=Get-Content (Join-Path $evidence 'windows-input-verification.json') -Raw|ConvertFrom-Json
    if(@($inputResult.failures).Count -ne 0){throw 'Native input checks failed; preserve the report.'}
    $report.buildGuid=$inputResult.buildGuid;$report.contentFingerprint=$inputResult.contentFingerprint
    $report.checks=$inputResult.checks;$report.suitePassed=$true

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
        $telemetry=Join-Path $repo ('benchmark\local\unity-runtime-interactive-'+$kind+'.csv')
        if($game -and (Test-Path $telemetry)){Copy-Item $telemetry (Join-Path $run ($kind+'.csv'))}
    }
    $report.completed=($report.suitePassed -eq $true -and $report.gameClosed -eq $true -and $report.launcherExitCode -eq 0)
    $report.finishedUtc=[DateTime]::UtcNow.ToString('o')
    $report|ConvertTo-Json -Depth 10|Set-Content (Join-Path $run 'native-input-result.json') -Encoding UTF8
    Write-Output ('UNITY_NATIVE_INPUT_REPORT '+(Join-Path $run 'native-input-result.json'))
}

if(-not $report.completed){throw 'Native input suite or owned-game closure did not complete.'}
Write-Output 'UNITY_NATIVE_INPUT_COMPLETE'
