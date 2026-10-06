[CmdletBinding()]
param(
 [string]$EngineRoot='D:\Games\UE_5.8',
 [string[]]$Variants=@(),
 [switch]$SkipAssembly,
 [switch]$AssembleOnly
)
$ErrorActionPreference='Stop'
if($AssembleOnly -and ($SkipAssembly -or $Variants.Count)){throw 'AssembleOnly cannot be combined with Variants or SkipAssembly.'}
$benchmark=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$project=Join-Path $benchmark 'unreal\KragKingsBenchmark'
$shared=Join-Path $benchmark 'shared'
$evidence=Join-Path $benchmark 'unreal\evidence'
$local=Join-Path $benchmark 'local\unreal-isolated-import'
$receiptDir=Join-Path $benchmark 'local\unreal-variant-cache'
$guard=Join-Path $benchmark 'tools\Run-HeavyTask.ps1'
$editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if(-not(Test-Path $editor)){throw "Installed Unreal editor missing: $editor"}
$engine=Get-Content (Join-Path $EngineRoot 'Engine\Build\Build.version') -Raw|ConvertFrom-Json
$enginePrefix="$($engine.MajorVersion).$($engine.MinorVersion).$($engine.PatchVersion)-$($engine.Changelist)"
New-Item -ItemType Directory -Force $local|Out-Null
& (Join-Path $PSScriptRoot 'Prepare-ImportCache.ps1') -Apply
$names=@()
foreach($species in @('krag','nib')){
 $manifest=Get-Content (Join-Path $shared "characters\$species\manifest.json") -Raw|ConvertFrom-Json
 $names+=@($manifest.variants|ForEach-Object {[IO.Path]::GetFileNameWithoutExtension($_.fbx)})
}
if(-not $Variants.Count){$Variants=$names}
foreach($name in $Variants){if($name -notin $names){throw "Variant absent from current manifest: $name"}}

function Test-Files([object]$Snapshot,[string]$Base,[string]$Directory,[string[]]$Extensions){
 if(-not(Test-Path -LiteralPath $Directory -PathType Container)){return $false}
 $files=@(Get-ChildItem -LiteralPath $Directory -Recurse -File|Where-Object {$_.Extension.ToLowerInvariant() -in $Extensions})
 $properties=@($Snapshot.PSObject.Properties)
 if($files.Count -ne $properties.Count){return $false}
 foreach($entry in $properties){
  $path=Join-Path $Base $entry.Name
  if(-not(Test-Path -LiteralPath $path -PathType Leaf)){return $false}
  if((Get-Item -LiteralPath $path).Length -ne $entry.Value.bytes){return $false}
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value.sha256){return $false}
 }
 return $true
}
function Test-Receipt([string]$Name){
 $path=Join-Path $receiptDir ($Name+'.json')
 if(-not(Test-Path -LiteralPath $path)){return $false}
 $receipt=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
 $species=$Name.Split('_')[0].ToLowerInvariant()
 if($receipt.recipe -ne 'skeletal-v2-explicit-dependencies-casefold-tracks' -or
    -not $receipt.engine.StartsWith($enginePrefix) -or $receipt.variant -ne $Name -or
    $receipt.folder -ne $species -or $receipt.descriptor.id -ne $Name){return $false}
 if(-not(Test-Files $receipt.characterInputs $shared (Join-Path $shared "characters\$species") @('.fbx','.png','.json','.wav'))){return $false}
 return Test-Files $receipt.packages $project (Join-Path $project "Content\Benchmark\Characters\$species\$Name") @('.uasset')
}
function Invoke-EditorStage([string]$Name,[string]$Argument,[string]$Marker){
 $log=Join-Path $evidence ($Name+'.log')
 $attempt=Join-Path $local ($Name+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff'))
 New-Item -ItemType Directory -Force $attempt|Out-Null
 $importerSnapshot=Join-Path $attempt 'import_shared_assets.py'
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'import_shared_assets.py') -Destination $importerSnapshot
 $spec=[ordered]@{
  name=$Name;executable=$editor
  arguments=@((Join-Path $project 'KragKingsBenchmark.uproject'),('-ExecutePythonScript='+$importerSnapshot),
              '-unattended','-nosplash','-stdout','-FullStdOutLogOutput',('-abslog='+$log),'-NoSound','-NullRHI','-corelimit=2','-KKReuseMaterials',$Argument)
  workingDirectory=(Split-Path $benchmark);stdout=(Join-Path $evidence ($Name+'-stdout.log'));stderr=(Join-Path $evidence ($Name+'-stderr.log'))
  minAvailableGB=10;maxPrivateGB=9;gpuTelemetry=$true;successLog=$log;successMarker=$Marker
 }
 $specPath=Join-Path $local ($Name+'-job.json')
 $spec|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $specPath -Encoding UTF8
 # Each native editor has its own guard/telemetry and must exit before the next.
 # Do not place this coordinator inside another Run-HeavyTask mutex.
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $guard -JobSpec $specPath
 if($LASTEXITCODE -ne 0){throw "Isolated Unreal stage $Name failed with guard exit $LASTEXITCODE. No later stage was started."}
}
if(-not $AssembleOnly){
 $previousPath=Join-Path $evidence 'character-import-batch-progress.json'
 $previous=if(Test-Path $previousPath){Get-Content $previousPath -Raw|ConvertFrom-Json}else{$null}
 $passed=@($previous.validated_meshes|ForEach-Object {[IO.Path]::GetFileNameWithoutExtension($_.source)})
 foreach($name in $Variants){
  if(Test-Receipt $name){Write-Output ('KK_VARIANT_CACHE_VERIFIED '+$name);continue}
  $receiptPath=Join-Path $receiptDir ($name+'.json')
  $species=$name.Split('_')[0].ToLowerInvariant()
  $generatedFolder=Join-Path $project "Content\Benchmark\Characters\$species\$name"
  if(-not(Test-Path $receiptPath) -and $name -in $passed -and (Test-Path -LiteralPath $generatedFolder -PathType Container)){
   # The Python validator checks this earlier pass against unchanged source
   # hashes, then reloads every package and rechecks actual tracks/morphs/binds.
   # An intentionally archived folder needs fresh import, not saved validation.
   Invoke-EditorStage ('unreal-validate-'+$name) ('-KKValidateSavedVariant='+$name) ('KK_VARIANT_COMPLETE '+$name)
  }else{
   Invoke-EditorStage ('unreal-import-'+$name) ('-KKImportVariant='+$name) ('KK_VARIANT_COMPLETE '+$name)
  }
  if(-not(Test-Receipt $name)){throw "Fresh receipt/hash verification failed after $name"}
 }
}
if(-not $SkipAssembly){
 foreach($name in $names){if(-not(Test-Receipt $name)){throw "Cannot assemble: validated package/source receipt missing or stale for $name"}}
 Invoke-EditorStage 'unreal-assemble' '-KKAssemble' 'KK_IMPORT_COMPLETE'
 Write-Output 'KK_ISOLATED_IMPORT_COMPLETE'
}
