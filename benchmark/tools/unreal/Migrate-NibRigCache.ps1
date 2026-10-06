[CmdletBinding()]
param(
 [ValidateSet('Plan','Archive','Restore')][string]$Mode='Plan',
 [string]$ArchiveDirectory=''
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$benchmark=Join-Path $repo 'benchmark'
$project=Join-Path $benchmark 'unreal\KragKingsBenchmark'
$content=Join-Path $project 'Content\Benchmark\Characters\nib'
$cache=Join-Path $benchmark 'local\unreal-variant-cache'
$archiveRoot=Join-Path $benchmark 'local\unreal-rig-migrations'
$variants=@('Nib_Natural','Nib_GripReplacement','Nib_LegReplacement')
$items=@()
foreach($name in $variants){
 $folder=Join-Path $content $name;$receipt=Join-Path $cache ($name+'.json')
 if($Mode -ne 'Restore'){
  foreach($required in @($folder,$receipt)){if(-not(Test-Path -LiteralPath $required)){throw ('Missing current generated cache: '+$required)}}
 }
 $items+=@{name=$name;kind='directory';source=$folder;archiveRelative=('packages\'+$name)}
 $items+=@{name=$name;kind='receipt';source=$receipt;archiveRelative=('receipts\'+$name+'.json')}
}
function Get-SourceRecords($Items,[switch]$Hash){
 $records=@()
 foreach($item in $Items){
  $files=if($item.kind -eq 'directory'){@(Get-ChildItem -LiteralPath $item.source -Recurse -File)}else{@(Get-Item -LiteralPath $item.source)}
  foreach($file in $files){
   $suffix=if($item.kind -eq 'directory'){$file.FullName.Substring($item.source.Length+1)}else{''}
   $relative=if($suffix){Join-Path $item.archiveRelative $suffix}else{$item.archiveRelative}
   $record=[ordered]@{source=$file.FullName;archiveRelative=$relative;bytes=$file.Length;lastWriteUtc=$file.LastWriteTimeUtc.ToString('o')}
   if($Hash){$record['sha256']=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower()}
   $records+=[pscustomobject]$record
  }
 }
 $records
}
if($Mode -eq 'Plan'){
 $files=@(Get-SourceRecords $items)
 [ordered]@{
  mode='Plan';mutated=$false;variants=$variants;generatedItems=$items
  files=$files;fileCount=$files.Count;totalBytes=($files|Measure-Object bytes -Sum).Sum
  includes='Entire variant directories, including .uasset/.uexp/.ubulk sidecars, animation packages and each matching validation receipt.'
  nextSkeleton='79 authored bones; record the Unreal Nib_Rig wrapper separately. Require EarTip_L/R under Ear_L/R, ForearmTwist_L/R under LowerArm_L/R and Hand_L/R under ForearmTwist_L/R.'
  importRequirement='Fresh matching mesh/skeleton and all seven clips at the same final package paths, followed by assembly and validation. This is not a clip-only refresh.'
  sharedAssetsChanged=$false;currentWindowsPackageChanged=$false
 }|ConvertTo-Json -Depth 8
 exit 0
}
if(-not $ArchiveDirectory){throw 'Archive/Restore requires an explicit task-owned ArchiveDirectory.'}
$archive=[IO.Path]::GetFullPath($ArchiveDirectory)
$allowed=[IO.Path]::GetFullPath($archiveRoot).TrimEnd('\')+'\'
if(-not $archive.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase) -or $archive.TrimEnd('\') -eq $allowed.TrimEnd('\')){throw 'Migration archive must be a child of benchmark/local/unreal-rig-migrations.'}
# A live editor can retain these assets in memory. Preserve user-owned editors;
# refuse the migration while one has this project open instead of closing it.
$editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"|Where-Object {$_.CommandLine -and $_.CommandLine.IndexOf($project,[StringComparison]::OrdinalIgnoreCase) -ge 0})
if($editors.Count){throw 'This Unreal project is open; close its owned task editor before migrating generated assets.'}
$mutex=New-Object System.Threading.Mutex($false,'Local\KragKingsBenchmarkHeavyJob');$locked=$false
try {
 try{$locked=$mutex.WaitOne(0)}catch [System.Threading.AbandonedMutexException]{$locked=$true}
 if(-not $locked){throw 'Another guarded task is active; migration must use the reserved process boundary.'}
 if($Mode -eq 'Archive'){
  if(Test-Path -LiteralPath $archive){throw 'Use a fresh migration archive; previous evidence is preserved.'}
  $files=@(Get-SourceRecords $items -Hash)
  # Confirm current receipt package hashes before moving any generated folder.
  foreach($name in $variants){
   $receipt=Get-Content -LiteralPath (Join-Path $cache ($name+'.json')) -Raw|ConvertFrom-Json
   if($receipt.variant -ne $name -or $receipt.folder -ne 'nib'){throw ('Receipt identity mismatch: '+$name)}
   foreach($entry in $receipt.packages.PSObject.Properties){
    $path=Join-Path $project $entry.Name
    if(-not(Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne $entry.Value.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $entry.Value.sha256){throw ('Generated package no longer matches its validated receipt: '+$path)}
   }
  }
  New-Item -ItemType Directory -Force $archive|Out-Null
  $journal=[ordered]@{schemaVersion=1;mode='Archive';complete=$false;createdUtc=[DateTime]::UtcNow.ToString('o');project=$project;items=$items;files=$files;moved=@();sharedAssetsChanged=$false;currentWindowsPackageChanged=$false}
  $journalPath=Join-Path $archive 'migration.json'
  $journal|ConvertTo-Json -Depth 9|Set-Content -LiteralPath $journalPath -Encoding UTF8
  try{
   foreach($item in $items){
    $destination=Join-Path $archive $item.archiveRelative
    New-Item -ItemType Directory -Force (Split-Path $destination)|Out-Null
    Move-Item -LiteralPath $item.source -Destination $destination
    $journal.moved+=@($item.archiveRelative)
    $journal|ConvertTo-Json -Depth 9|Set-Content -LiteralPath $journalPath -Encoding UTF8
   }
   foreach($file in $files){
    $path=Join-Path $archive $file.archiveRelative
    if((Get-Item -LiteralPath $path).Length -ne $file.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $file.sha256){throw ('Archived file verification failed: '+$file.archiveRelative)}
   }
   $journal.complete=$true;$journal['completedUtc']=[DateTime]::UtcNow.ToString('o')
   $journal|ConvertTo-Json -Depth 9|Set-Content -LiteralPath $journalPath -Encoding UTF8
  }catch{
   $journal['failure']=$_.Exception.Message
   # Nothing is overwritten during recovery; these sources were just moved by us.
   foreach($item in @($items|Where-Object {$_.archiveRelative -in $journal.moved})){
    if(Test-Path -LiteralPath $item.source){throw 'Unexpected replacement appeared during archive recovery; preserve both paths for inspection.'}
    Move-Item -LiteralPath (Join-Path $archive $item.archiveRelative) -Destination $item.source
   }
   $journal['rolledBack']=$true;$journal|ConvertTo-Json -Depth 9|Set-Content -LiteralPath $journalPath -Encoding UTF8
   throw
  }
  Write-Output ('NIB_RIG_CACHE_ARCHIVED '+$journalPath)
 }else{
  $journalPath=Join-Path $archive 'migration.json';$journal=Get-Content -LiteralPath $journalPath -Raw|ConvertFrom-Json
  if(-not $journal.complete -or $journal.project -ne $project){throw 'A completed archive for this exact project is required.'}
  if($journal.schemaVersion -ne 1 -or @($journal.items).Count -ne $items.Count){throw 'Unsupported or incomplete migration journal.'}
  # Derive the allowed destinations from this script, not from journal paths.
  foreach($item in $items){
   $match=@($journal.items|Where-Object {$_.archiveRelative -eq $item.archiveRelative -and $_.source -eq $item.source -and $_.name -eq $item.name -and $_.kind -eq $item.kind})
   if($match.Count -ne 1){throw ('Migration item identity mismatch: '+$item.archiveRelative)}
  }
  $seen=@{}
  foreach($file in $journal.files){
   if([IO.Path]::IsPathRooted($file.archiveRelative) -or $seen.ContainsKey($file.archiveRelative)){throw 'Duplicate or absolute journal path.'}
   $seen[$file.archiveRelative]=$true
   $matches=@($items|Where-Object {
    ($_.kind -eq 'receipt' -and $file.archiveRelative -eq $_.archiveRelative -and $file.source -eq $_.source) -or
    ($_.kind -eq 'directory' -and $file.archiveRelative.StartsWith($_.archiveRelative+'\',[StringComparison]::OrdinalIgnoreCase) -and
     [IO.Path]::GetFullPath($file.source).StartsWith($_.source+'\',[StringComparison]::OrdinalIgnoreCase) -and
     $file.source -eq (Join-Path $_.source $file.archiveRelative.Substring($_.archiveRelative.Length+1)))
   })
   if($matches.Count -ne 1 -or -not [IO.Path]::GetFullPath((Join-Path $archive $file.archiveRelative)).StartsWith($archive.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw ('Journal file escapes expected cache: '+$file.archiveRelative)}
  }
  if(-not @($journal.files).Count){throw 'Archive journal has no files.'}
  foreach($file in $journal.files){
   $path=Join-Path $archive $file.archiveRelative
   if(-not(Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne $file.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $file.sha256){throw ('Original archived file changed: '+$file.archiveRelative)}
  }
  # Keep any failed/new replacement cache; never overwrite it with the baseline.
  $replacement=Join-Path $archive ('replaced-cache-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff'))
  foreach($item in $items){
   if(Test-Path -LiteralPath $item.source){
    $destination=Join-Path $replacement $item.archiveRelative
    New-Item -ItemType Directory -Force (Split-Path $destination)|Out-Null
    Move-Item -LiteralPath $item.source -Destination $destination
   }
   New-Item -ItemType Directory -Force (Split-Path $item.source)|Out-Null
   # Copy back so the verified original archive remains intact for comparison.
   Copy-Item -LiteralPath (Join-Path $archive $item.archiveRelative) -Destination $item.source -Recurse
  }
  foreach($file in $journal.files){
   if((Get-FileHash -LiteralPath $file.source -Algorithm SHA256).Hash.ToLower() -ne $file.sha256){throw ('Restored cache verification failed: '+$file.source)}
  }
  [ordered]@{complete=$true;restoredUtc=[DateTime]::UtcNow.ToString('o');preservedReplacement=$replacement;sharedAssetsChanged=$false;currentWindowsPackageChanged=$false;scope='Generated cache restored only; source hash gates still decide whether it can assemble/package.'}|ConvertTo-Json|Set-Content (Join-Path $archive 'restore-result.json') -Encoding UTF8
  Write-Output ('NIB_RIG_CACHE_RESTORED '+$archive)
 }
} finally {if($locked){$mutex.ReleaseMutex()};$mutex.Dispose()}
