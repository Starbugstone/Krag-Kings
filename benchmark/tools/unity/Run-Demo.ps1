param([ValidateSet('Verify','Performance','PerformanceMoving','Showcase','Interactive')][string]$Mode='Interactive')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$executable=Join-Path $repo 'benchmark\builds\Unity\KragKings-Unity.exe'
if(-not(Test-Path $executable)){throw 'The Unity Windows demo has not been built yet.'}
$evidence=Join-Path $repo ('benchmark\local\evidence\unity-'+$Mode.ToLowerInvariant()+'\'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force $evidence | Out-Null
Write-Output ('UNITY_EVIDENCE_DIR '+$evidence)
$arguments=@('-screen-width','1920','-screen-height','1080','-screen-fullscreen','1','-window-mode','borderless','-force-d3d12','-evidencePath',$evidence,'-logFile',(Join-Path $evidence 'player.log'))
if($Mode -eq 'Verify'){$arguments+='-benchmarkVerify'}
if($Mode -eq 'Performance'){$arguments+='-benchmarkPerformance'}
if($Mode -eq 'PerformanceMoving'){$arguments+='-benchmarkPerformanceMoving'}
if($Mode -eq 'Showcase'){
    $arguments+=@('-benchmarkShowcase','-showcaseWait')
    Remove-Item (Join-Path $evidence 'showcase-start.flag'),(Join-Path $evidence 'showcase-ready.json'),(Join-Path $evidence 'showcase-started.json'),(Join-Path $evidence 'showcase-complete.json') -Force -ErrorAction SilentlyContinue
}
if($Mode -eq 'Interactive'){$arguments+='-inputProbe'}
$spec=Join-Path $repo 'benchmark\local\unity-runtime-job.json'
@{name=('unity-runtime-'+$Mode.ToLowerInvariant());executable=$executable;arguments=$arguments;workingDirectory=(Split-Path $executable);minAvailableGB=10;maxPrivateGB=8;gpuTelemetry=$true} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $spec
& (Join-Path $PSScriptRoot '..\Run-HeavyTask.ps1') -JobSpec $spec
exit $LASTEXITCODE
