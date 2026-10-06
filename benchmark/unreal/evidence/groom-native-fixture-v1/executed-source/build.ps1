param([Parameter(Mandatory=$true)][string]$Plan)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$spec=Get-Content -LiteralPath $Plan -Raw|ConvertFrom-Json
foreach($pin in $spec.pins){
    $file=Join-Path $repo $pin.path
    if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.sha256){throw ('Frozen groom probe input changed: '+$pin.path)}
}
$project=Join-Path $repo ($spec.projectDirectory+'\GroomProbe.uproject')
if(-not $project.StartsWith((Join-Path $repo 'benchmark\local\groom-probe\'),[StringComparison]::OrdinalIgnoreCase)){throw 'Refuse build outside isolated probe directory'}
$build=Join-Path $spec.engine 'Engine\Build\BatchFiles\Build.bat'
& $build GroomProbeEditor Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE
if($LASTEXITCODE -ne 0){throw ('Isolated groom probe editor build failed: '+$LASTEXITCODE)}
Write-Output 'KK_GROOM_PROBE_BUILD_COMPLETE'
