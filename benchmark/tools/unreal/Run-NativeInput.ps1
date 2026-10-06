[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$packageRoot=Join-Path $repo 'benchmark\builds\unreal\Windows'
$executable=Join-Path $packageRoot 'KragKingsBenchmark\Binaries\Win64\KragKingsBenchmark.exe'
$saved=Join-Path $packageRoot 'KragKingsBenchmark\Saved\Benchmark'
$statePath=Join-Path $saved 'input-state.json'
$inputReportPath=Join-Path $saved 'input-smoke-report.json'
if((Test-Path $OutputDirectory) -and @(Get-ChildItem $OutputDirectory -Force).Count){throw 'Use a fresh native-input evidence directory.'}
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
$OutputDirectory=(Resolve-Path $OutputDirectory).Path
$receiptPath=Join-Path $repo 'benchmark\unreal\evidence\package-result.json'
$receipt=Get-Content $receiptPath -Raw|ConvertFrom-Json
if(-not $receipt.complete){throw 'A successful Windows package receipt is required.'}
foreach($artifact in $receipt.artifacts){
 $path=Join-Path $packageRoot $artifact.path
 if(-not(Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash.ToLower() -ne $artifact.sha256){throw ('Package differs from its completed-cook receipt: '+$artifact.path)}
}
Copy-Item $receiptPath (Join-Path $OutputDirectory 'package-result.json')
foreach($stale in @($statePath,$inputReportPath)){
 if(Test-Path $stale){Copy-Item $stale (Join-Path $OutputDirectory ('previous-'+[IO.Path]::GetFileName($stale)));Remove-Item -LiteralPath $stale}
}
$runtimeLog=Join-Path $OutputDirectory 'runtime.log'
$job=[ordered]@{
 name='unreal-native-input';executable=$executable
 arguments=@('-ResX=1920','-ResY=1080','-NoVSync','-KKSkinMode=Profile','-KKInputState',('-abslog='+$runtimeLog),'-ExecCmds=sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2')
 workingDirectory=(Split-Path $executable);stdout=(Join-Path $OutputDirectory 'native-stdout.log');stderr=(Join-Path $OutputDirectory 'native-stderr.log')
 minAvailableGB=10;maxPrivateGB=10;gpuTelemetry=$true;trackProcessTree=$false;successLog=$runtimeLog;successMarker='KK_READY'
}
$jobPath=Join-Path $OutputDirectory 'job.json';$job|ConvertTo-Json -Depth 6|Set-Content $jobPath -Encoding UTF8
& (Join-Path $PSScriptRoot '..\Write-RunConditions.ps1') -OutputPath (Join-Path $OutputDirectory 'run-conditions.json')
$inputScript=Join-Path $PSScriptRoot 'input_smoke.ps1'
Copy-Item $inputScript (Join-Path $OutputDirectory 'executed-input_smoke.ps1')
$report=[ordered]@{engine='Unreal';completed=$false;visualAcceptance=$false;performanceMeasurement=$false;startedUtc=[DateTime]::UtcNow.ToString('o');exeSha256=(Get-FileHash $executable -Algorithm SHA256).Hash.ToLower();inputScriptSha256=(Get-FileHash $inputScript -Algorithm SHA256).Hash.ToLower();guardMarkerMeaning='Readiness only; inputReportCompleted and gameClosed are also required.'}
$guard=$null;$game=$null;$guardOutput=Join-Path $OutputDirectory 'guard-stdout.log'
try{
 $guardScript=Join-Path $PSScriptRoot '..\Run-HeavyTask.ps1'
 $guard=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$guardScript+'"'),'-JobSpec',('"'+$jobPath+'"')) -RedirectStandardOutput $guardOutput -RedirectStandardError (Join-Path $OutputDirectory 'guard-stderr.log') -PassThru -WindowStyle Hidden
 $null=$guard.Handle;$deadline=[DateTime]::UtcNow.AddSeconds(150)
 do{
  if(Test-Path $guardOutput){
   $guardText=[string](Get-Content $guardOutput -Raw)
   if(-not[string]::IsNullOrWhiteSpace($guardText)){
    $match=[regex]::Match($guardText,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
    if($match.Success){$game=Get-Process -Id ([int]$match.Groups[1].Value) -ErrorAction SilentlyContinue}
   }
  }
  if($guard.HasExited){throw 'The guard exited before native-input readiness; inspect its logs.'}
  if($game -and $game.MainWindowHandle -ne 0 -and (Test-Path $statePath) -and (Test-Path $runtimeLog) -and (Select-String -LiteralPath $runtimeLog -SimpleMatch 'KK_READY' -Quiet)){break}
  if([DateTime]::UtcNow -gt $deadline){throw 'Native-input readiness timed out.'}
  Start-Sleep -Milliseconds 200
 }while($true)
 if($game.Path -ne $executable){throw 'Guard PID does not identify the intended native Unreal executable.'}
 $report.gameProcessId=$game.Id
 & $inputScript -StatePath $statePath -GameProcessId $game.Id -ExecutionMode Packaged|Tee-Object -FilePath (Join-Path $OutputDirectory 'input-stdout.log')
 $inputResult=Get-Content $inputReportPath -Raw|ConvertFrom-Json
 if(-not $inputResult.completed){throw 'The actual native input suite did not complete successfully.'}
 $report.inputReportCompleted=$true;$report.checks=@($inputResult.checks).Count
}catch{$report.error=$_.Exception.Message;$report.errorStack=$_.ScriptStackTrace;throw}finally{
 if(-not $game -and (Test-Path $guardOutput)){
  $text=[string](Get-Content $guardOutput -Raw)
  if(-not[string]::IsNullOrWhiteSpace($text)){
   $match=[regex]::Match($text,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
   if($match.Success){$candidate=Get-Process -Id ([int]$match.Groups[1].Value) -ErrorAction SilentlyContinue;if($candidate -and $candidate.Path -eq $executable){$game=$candidate}}
  }
 }
 if($game){try{if(-not $game.HasExited -and $game.Path -eq $executable){$game.CloseMainWindow()|Out-Null;$report.gameClosed=$game.WaitForExit(15000)}else{$report.gameClosed=$true}}catch{$report.gameCloseError=$_.Exception.Message}}
 if($guard){if($guard.WaitForExit(20000)){$guard.Refresh();$report.guardExitCode=$guard.ExitCode}else{$report.guardStillRunning=$true}}
 foreach($path in @($statePath,$inputReportPath)){if(Test-Path $path){Copy-Item $path (Join-Path $OutputDirectory ([IO.Path]::GetFileName($path)))}}
 foreach($kind in @('memory','gpu')){
  $telemetry=Join-Path $repo ('benchmark\local\'+$job.name+'-'+$kind+'.csv')
  if($game -and (Test-Path $telemetry)){Copy-Item $telemetry (Join-Path $OutputDirectory ($kind+'.csv'))}
 }
 $report.completed=($report.inputReportCompleted -eq $true -and $report.gameClosed -eq $true -and $report.guardExitCode -eq 0)
 $report.finishedUtc=[DateTime]::UtcNow.ToString('o');$report|ConvertTo-Json -Depth 8|Set-Content (Join-Path $OutputDirectory 'native-input-result.json') -Encoding UTF8
 Write-Output ('UNREAL_NATIVE_INPUT_REPORT '+(Join-Path $OutputDirectory 'native-input-result.json'))
}
if(-not $report.completed){throw 'The guarded native input/close sequence did not fully succeed.'}
Write-Output 'UNREAL_NATIVE_INPUT_COMPLETE'
