[CmdletBinding()]
param(
 [ValidateSet('Idle','Moving')][string]$Mode='Idle',
 [ValidateSet('Full','Balanced')][string]$Profile='Full',
 [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $PSScriptRoot '..\capture\OwnedGameWindow.ps1')
$package=Join-Path $repo 'benchmark\builds\unreal\Windows\KragKingsBenchmark'
$executable=Join-Path $package 'Binaries\Win64\KragKingsBenchmark.exe'
if(-not(Test-Path $executable)){throw 'The actual Windows package is required.'}
if((Test-Path $OutputDirectory) -and @(Get-ChildItem $OutputDirectory -Force).Count){throw 'Use a fresh performance evidence directory.'}
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
$OutputDirectory=(Resolve-Path $OutputDirectory).Path
$prefix='performance-'+$Mode.ToLower();$nativeEvidence=Join-Path $package 'Saved\Benchmark'
foreach($name in @(($prefix+'.json'),($prefix+'-frames.csv'))) {
 $source=Join-Path $nativeEvidence $name
 if(Test-Path $source){Move-Item $source (Join-Path $OutputDirectory ('prior-'+$name))}
}
$quality=if($Profile -eq 'Balanced'){2}else{3}
# Compare software-Lumen High vs Epic; retain native pixels, textures, shadows,
# anti-aliasing, post processing and geometry. These are tuning candidates.
$commands=@('sg.ViewDistanceQuality 3','sg.AntiAliasingQuality 3','sg.ShadowQuality 3',"sg.GlobalIlluminationQuality $quality","sg.ReflectionQuality $quality",'sg.PostProcessQuality 3','sg.TextureQuality 3','sg.EffectsQuality 3','sg.FoliageQuality 3','sg.ShadingQuality 3','r.VolumetricFog 1')
$runtimeLog=Join-Path $OutputDirectory 'runtime.log'
$job=[ordered]@{
 name=('unreal-'+$Mode.ToLower()+'-'+$Profile.ToLower());executable=$executable
 arguments=@('-ResX=1920','-ResY=1080','-NoVSync',('-abslog='+$runtimeLog),('-ExecCmds='+($commands -join ',')),$(if($Mode -eq 'Moving'){'-KKPerfMoving'}else{'-KKPerf'}))
 workingDirectory=(Split-Path $executable);stdout=(Join-Path $OutputDirectory 'native-stdout.log');stderr=(Join-Path $OutputDirectory 'native-stderr.log')
 minAvailableGB=10;maxPrivateGB=10;gpuTelemetry=$true;trackProcessTree=$false;successLog=$runtimeLog;successMarker=('KK_METRICS mode='+$prefix)
}
$jobPath=Join-Path $OutputDirectory 'job.json';$job|ConvertTo-Json -Depth 6|Set-Content $jobPath -Encoding UTF8
& (Join-Path $PSScriptRoot '..\Write-RunConditions.ps1') -OutputPath (Join-Path $OutputDirectory 'run-conditions.json')
$packageReceipt=Join-Path $repo 'benchmark\unreal\evidence\package-result.json'
$packageMetadata=Get-Content $packageReceipt -Raw|ConvertFrom-Json
foreach($artifact in $packageMetadata.artifacts){
 $path=Join-Path (Split-Path $package) $artifact.path
 if(-not(Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash.ToLower() -ne $artifact.sha256){throw ('Packaged artifact no longer matches completed cook: '+$artifact.path)}
}
Copy-Item $packageReceipt (Join-Path $OutputDirectory 'package-result.json')
$report=[ordered]@{engine='Unreal';mode=$Mode;profile=$Profile;profileDescription=$(if($Profile -eq 'Balanced'){'High software Lumen GI/reflections; all other recorded groups Epic, native pixels'}else{'Epic software Lumen GI/reflections and remaining recorded groups, native pixels'});commands=$commands;source='actual packaged native Windows process';exeSha256=(Get-FileHash $executable -Algorithm SHA256).Hash.ToLower();comparisonComplete=$false;artisticAcceptance=$false;startedUtc=[DateTime]::UtcNow.ToString('o')}
$guard=$null;$game=$null;$lease=$null
try {
 $guardScript=Join-Path $PSScriptRoot '..\Run-HeavyTask.ps1'
 $guardOutput=Join-Path $OutputDirectory 'guard-stdout.log'
 $guard=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$guardScript+'"'),'-JobSpec',('"'+$jobPath+'"')) -RedirectStandardOutput $guardOutput -RedirectStandardError (Join-Path $OutputDirectory 'guard-stderr.log') -PassThru -WindowStyle Hidden
 $null=$guard.Handle
 $readyDeadline=[DateTime]::UtcNow.AddSeconds(90)
 while($true){
  if($guard.HasExited){throw 'Guard exited before the intended game window became ready.'}
  if(Test-Path $guardOutput){
   $guardText=[string](Get-Content $guardOutput -Raw)
   $match=[regex]::Match($guardText,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
   if($match.Success){
    $game=Get-Process -Id ([int]$match.Groups[1].Value) -ErrorAction SilentlyContinue
    if($game -and $game.MainWindowHandle -ne [IntPtr]::Zero -and (Test-Path $runtimeLog) -and (Select-String -LiteralPath $runtimeLog -Pattern 'KK_READY' -SimpleMatch -Quiet)){break}
   }
  }
  if([DateTime]::UtcNow -gt $readyDeadline){throw 'Actual game readiness timed out.'}
  Start-Sleep -Milliseconds 100
 }
 if($game.Path -ne $executable){throw 'Guard PID is not the intended native executable.'}
 # Bounded activation during warmup only. No pointer/keyboard injection, frame
 # capture, state probes, or focus polling occurs during the measured interval.
 $lease=[KKOwnedWindowLease]::Acquire($game.MainWindowHandle,[uint32]$game.Id)
 $report.gameProcessId=$game.Id;$report.foregroundAcquiredUtc=[DateTime]::UtcNow.ToString('o');$report.originalTopmost=$lease.OriginalTopmost
 if(-not $guard.WaitForExit(75000)){throw 'Performance run did not close after its bounded sample.'}
 $guard.Refresh();$report.guardExit=$guard.ExitCode
 if($guard.ExitCode -ne 0){throw "Guarded performance process failed: $($guard.ExitCode)"}
 foreach($name in @(($prefix+'.json'),($prefix+'-frames.csv'))){Copy-Item (Join-Path $nativeEvidence $name) (Join-Path $OutputDirectory $name)}
 $metrics=Get-Content (Join-Path $OutputDirectory ($prefix+'.json')) -Raw|ConvertFrom-Json
 if(-not $metrics.comparison_pass -or -not $metrics.completed_sample_window -or $metrics.width -ne 1920 -or $metrics.height -ne 1080 -or $metrics.warmup_seconds -ne 15){throw 'Runtime did not confirm the full native-1080p comparison window.'}
 foreach($entry in @(@('r.ScreenPercentage',100),@('r.DynamicRes.OperationMode',0),@('r.VSync',0),@('sg.GlobalIlluminationQuality',$quality),@('sg.ReflectionQuality',$quality),@('sg.ShadowQuality',3),@('sg.TextureQuality',3))){if($metrics.actual_cvars.($entry[0]) -ne $entry[1]){throw ('Runtime setting mismatch: '+$entry[0])}}
 $report.comparisonComplete=$true;$report.metrics=$metrics
 $report.nativeProfileFieldNote='The executable requested_profile text describes its default. Actual CVars and this wrapper profile describe this measured launch.'
 Write-Output ('UNREAL_PERFORMANCE_COMPLETE '+$Mode+' '+$Profile+' fps='+$metrics.average_fps)
} catch {$report.error=$_.Exception.Message;$report.errorStack=$_.ScriptStackTrace;throw} finally {
 if($lease){try{$lease.Dispose();$report.windowLeaseRestored=$lease.Restored}catch{$report.windowRestoreError=$_.Exception.Message}}
 if(-not $game -and $guardOutput -and (Test-Path $guardOutput)){
  $guardText=[string](Get-Content $guardOutput -Raw)
  $started=[regex]::Match($guardText,'HEAVY_JOB_STARTED[^\r\n]*PID=(\d+)')
  if($started.Success){$candidate=Get-Process -Id ([int]$started.Groups[1].Value) -ErrorAction SilentlyContinue;if($candidate -and $candidate.Path -eq $executable){$game=$candidate}}
 }
 if($game){try{if(-not $game.HasExited){$game.CloseMainWindow()|Out-Null}}catch{}}
 if($guard -and -not $guard.HasExited){$null=$guard.WaitForExit(10000)}
 foreach($kind in @('memory','gpu')){
  $telemetry=Join-Path $repo ('benchmark\local\'+$job.name+'-'+$kind+'.csv')
  if(Test-Path $telemetry){Copy-Item $telemetry (Join-Path $OutputDirectory ($kind+'.csv'))}
 }
 $report.finishedUtc=[DateTime]::UtcNow.ToString('o')
 $report|ConvertTo-Json -Depth 12|Set-Content (Join-Path $OutputDirectory 'run-result.json') -Encoding UTF8
}
