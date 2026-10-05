param([string]$Blender='D:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$local=Join-Path $repo 'benchmark\local'
$logs=Join-Path $local 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$spec=Join-Path $local 'environment-job.json'
@{
    name='environment-dunes'; executable=$Blender; workingDirectory=$repo;
    arguments=@('--background','--threads','4','--python-exit-code','2','--python',(Join-Path $PSScriptRoot 'build_dunes.py'));
    stdout=(Join-Path $logs 'environment-dunes-stdout.log');
    stderr=(Join-Path $logs 'environment-dunes-stderr.log');
    minAvailableGB=10; maxPrivateGB=8
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $spec
& (Join-Path $PSScriptRoot '..\Run-HeavyTask.ps1') -JobSpec $spec
exit $LASTEXITCODE
