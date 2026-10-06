[CmdletBinding()]
param(
 [ValidateSet('Full','Balanced')][string]$Quality='Balanced',
 [ValidateSet('Generic','DefaultLit','Profile')][string]$SkinMode='Generic',
 [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$windowsPackage=Join-Path $repo 'benchmark\builds\unreal\Windows'
$executable=Join-Path $windowsPackage 'KragKingsBenchmark\Binaries\Win64\KragKingsBenchmark.exe'
if(-not(Test-Path -LiteralPath $executable)){throw 'Build the actual Windows Unreal package before recording.'}
if((Test-Path $OutputDirectory) -and @(Get-ChildItem $OutputDirectory -Force).Count){throw 'Use a fresh recording evidence directory.'}
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
$OutputDirectory=(Resolve-Path $OutputDirectory).Path
$packageReceipt=Join-Path $repo 'benchmark\unreal\evidence\package-result.json'
$packageMetadata=Get-Content $packageReceipt -Raw|ConvertFrom-Json
foreach($artifact in $packageMetadata.artifacts){
 $path=Join-Path $windowsPackage $artifact.path
 if(-not(Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash.ToLower() -ne $artifact.sha256){throw ('Package differs from its completed-cook receipt: '+$artifact.path)}
}
Copy-Item $packageReceipt (Join-Path $OutputDirectory 'package-result.json')
$level=if($Quality -eq 'Balanced'){2}else{3}
$commands=@('sg.ViewDistanceQuality 3','sg.AntiAliasingQuality 3','sg.ShadowQuality 3',"sg.GlobalIlluminationQuality $level","sg.ReflectionQuality $level",'sg.PostProcessQuality 3','sg.TextureQuality 3','sg.EffectsQuality 3','sg.FoliageQuality 3','sg.ShadingQuality 3','r.VolumetricFog 1')
$runtimeLog=Join-Path $OutputDirectory 'runtime.log'
$gate=Join-Path $OutputDirectory 'showcase-start.flag'
$job=[ordered]@{
 name='unreal-recording';executable=$executable
 arguments=@('-ResX=1920','-ResY=1080','-NoVSync','-KKShowcase','-KKShowcaseWait',('-KKSkinMode='+$SkinMode),('-KKShowcaseGate='+$gate),('-abslog='+$runtimeLog),('-ExecCmds='+($commands -join ',')))
 workingDirectory=(Split-Path $executable);stdout=(Join-Path $OutputDirectory 'native-stdout.log');stderr=(Join-Path $OutputDirectory 'native-stderr.log')
 minAvailableGB=10;maxPrivateGB=10;gpuTelemetry=$true;trackProcessTree=$false;successLog=$runtimeLog;successMarker='KK_SHOWCASE_COMPLETE'
}
$jobPath=Join-Path $OutputDirectory 'job.json';$job|ConvertTo-Json -Depth 6|Set-Content $jobPath -Encoding UTF8
& (Join-Path $PSScriptRoot '..\Write-RunConditions.ps1') -OutputPath (Join-Path $OutputDirectory 'run-conditions.json')
$report=[ordered]@{engine='Unreal';quality=$Quality;skinMode=$SkinMode;startedUtc=[DateTime]::UtcNow.ToString('o');completed=$false;artisticAcceptance=$false;performanceMeasurement=$false;exeSha256=(Get-FileHash $executable -Algorithm SHA256).Hash.ToLower()}
$guard=$null;$game=$null
$guardOutput=Join-Path $OutputDirectory 'guard-stdout.log'
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
  if($guard.HasExited){throw 'The guard exited before showcase readiness; inspect its logs.'}
  if($game -and (Test-Path $runtimeLog) -and (Select-String -LiteralPath $runtimeLog -SimpleMatch 'KK_SHOWCASE_READY' -Quiet)){break}
  if([DateTime]::UtcNow -gt $deadline){throw 'Showcase readiness timed out.'}
  Start-Sleep -Milliseconds 200
 }while($true)
 if($game.Path -ne $executable){throw 'Guard PID does not identify the intended native Unreal executable.'}
 if($SkinMode -ne 'Generic'){
  foreach($species in @('Krag','Nib')){
   if(-not(Select-String -LiteralPath $runtimeLog -SimpleMatch ("KK_SKIN_MODE species=$species mode=$SkinMode") -Quiet)){throw 'Runtime did not confirm the requested material mode for both species.'}
  }
 }
 $report.gameProcessId=$game.Id
 $capture=Join-Path $OutputDirectory 'capture-wgc'
 & (Join-Path $PSScriptRoot '..\capture\Capture-Demo.ps1') -Engine Unreal -GameProcessId $game.Id -RuntimeLog $runtimeLog -StartFlag $gate -EngineAudio (Join-Path $OutputDirectory 'showcase-engine-audio.wav') -OutputDirectory $capture
 $captureReport=Get-Content (Join-Path $capture 'unreal-showcase-capture.json') -Raw|ConvertFrom-Json
 if(-not $captureReport.completed){throw 'Capture did not pass its actual media checks.'}
 if(-not(Select-String -LiteralPath $runtimeLog -SimpleMatch 'KK_SHOWCASE_COMPLETE' -Quiet)){throw 'The game did not finish its actual sequence.'}
 $report.mediaChecksPassed=$true;$report.video=$captureReport.output;$report.videoSha256=$captureReport.outputSha256
}catch{$report.error=$_.Exception.Message;$report.errorStack=$_.ScriptStackTrace;throw}finally{
 if(-not $game -and (Test-Path $guardOutput)){
  $guardText=[string](Get-Content $guardOutput -Raw)
  if(-not[string]::IsNullOrWhiteSpace($guardText)){
   $match=[regex]::Match($guardText,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
   if($match.Success){$candidate=Get-Process -Id ([int]$match.Groups[1].Value) -ErrorAction SilentlyContinue;if($candidate -and $candidate.Path -eq $executable){$game=$candidate}}
  }
 }
 if($game){try{if(-not $game.HasExited -and $game.Path -eq $executable){$game.CloseMainWindow()|Out-Null;$report.gameClosed=$game.WaitForExit(15000)}else{$report.gameClosed=$true}}catch{$report.gameCloseError=$_.Exception.Message}}
 if($guard){if($guard.WaitForExit(20000)){$guard.Refresh();$report.guardExitCode=$guard.ExitCode}else{$report.guardStillRunning=$true}}
 foreach($kind in @('memory','gpu')){
  $telemetry=Join-Path $repo ('benchmark\local\'+$job.name+'-'+$kind+'.csv')
  if($game -and (Test-Path $telemetry)){Copy-Item $telemetry (Join-Path $OutputDirectory ($kind+'.csv'))}
 }
 $report.completed=($report.mediaChecksPassed -eq $true -and $report.gameClosed -eq $true -and $report.guardExitCode -eq 0)
 $report.finishedUtc=[DateTime]::UtcNow.ToString('o');$report|ConvertTo-Json -Depth 10|Set-Content (Join-Path $OutputDirectory 'recording-result.json') -Encoding UTF8
 Write-Output ('UNREAL_RECORDING_REPORT '+(Join-Path $OutputDirectory 'recording-result.json'))
}
if(-not $report.completed){throw 'Media was retained, but the guarded recording/close sequence did not fully succeed.'}
Write-Output ('UNREAL_RECORDING_COMPLETE '+$report.video)
