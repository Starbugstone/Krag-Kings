[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference='Stop'
$benchmark=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$content=Join-Path $benchmark 'unreal\KragKingsBenchmark\Content\Benchmark\Characters'
$stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff')
$archive=Join-Path $benchmark ('local\unreal-invalid-import-samples\'+$stamp)
$records=@()
foreach($species in @('krag','nib')){
 $directory=Join-Path $content $species
 if(-not(Test-Path $directory)){continue}
 foreach($variant in Get-ChildItem $directory -Directory){
  if($variant.Name -notmatch '^(Krag|Nib)_[A-Za-z0-9_]+$'){continue}
  $mesh=Join-Path $variant.FullName ($variant.Name+'.uasset')
  if(-not(Test-Path $mesh)){continue}
  $missing=@('Skeleton','PhysicsAsset'|Where-Object {-not(Test-Path (Join-Path $variant.FullName ($variant.Name+'_'+$_+'.uasset')))})
  if(-not $missing.Count){continue}
  $destination=Join-Path $archive ($species+'\'+$variant.Name)
  $files=@(Get-ChildItem $variant.FullName -File -Recurse|ForEach-Object {@{file=$_.FullName.Substring($variant.FullName.Length+1);bytes=$_.Length;sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()}})
  $records+=@{source=$variant.FullName;destination=$destination;missing=$missing;files=$files;archived=[bool]$Apply}
  if($Apply){
   New-Item -ItemType Directory -Force (Split-Path $destination)|Out-Null
   Move-Item -LiteralPath $variant.FullName -Destination $destination
  }
 }
}
if($records.Count){
 if($Apply){@{reason='Generated character packages have missing persisted dependencies';records=$records}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $archive 'archive-receipt.json') -Encoding UTF8}
 $records|ConvertTo-Json -Depth 8
 if(-not $Apply){throw 'Incomplete generated character dependencies found; rerun Prepare-ImportCache.ps1 -Apply before launching the editor to archive these samples and rebuild them.'}
}else{Write-Output 'IMPORT_CACHE_DEPENDENCIES_PRESENT_OR_NOT_YET_IMPORTED'}
