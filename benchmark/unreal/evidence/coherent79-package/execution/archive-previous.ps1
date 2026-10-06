$ErrorActionPreference='Stop'
$source='D:\Dev\Krag-Kings\benchmark\builds\unreal\Windows'
$archive='D:\Dev\Krag-Kings\benchmark\local\package-archive\unreal-fe65-before-coherent79'
$exe=Join-Path $source 'KragKingsBenchmark\Binaries\Win64\KragKingsBenchmark.exe'
$expected='fe65cc4aeb991cd2df103fcdfa76b07ce1495cf353c10799187469a041215a9d'
if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Previous package executable differs from the recorded fe65 baseline.'}
if(Test-Path -LiteralPath $archive){throw 'Preserve earlier package archive; verify it explicitly instead of overwriting.'}
$files=@(Get-ChildItem -LiteralPath $source -Recurse -File)
$bytes=($files|Measure-Object -Property Length -Sum).Sum
if((Get-PSDrive D).Free -lt ($bytes+2GB)){throw 'Insufficient free space for full reversible package archive.'}
New-Item -ItemType Directory -Path $archive|Out-Null
$records=@()
foreach($file in $files){
 $relative=$file.FullName.Substring($source.Length+1)
 $destination=Join-Path (Join-Path $archive 'Windows') $relative
 New-Item -ItemType Directory -Force -Path (Split-Path $destination)|Out-Null
 $hash=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
 Copy-Item -LiteralPath $file.FullName -Destination $destination
 if((Get-Item -LiteralPath $destination).Length -ne $file.Length -or (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash){throw ('Archive copy differs: '+$relative)}
 $records+=[ordered]@{path=$relative.Replace('\','/');bytes=$file.Length;sha256=$hash}
}
[ordered]@{source=$source;archive=$archive;complete=$true;sourceChanged=$false;executableSha256=$expected;fileCount=$files.Count;bytes=$bytes;files=$records}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $archive 'archive.json') -Encoding UTF8
Write-Output ('KK_PACKAGE_ARCHIVE_COMPLETE files='+$files.Count+' bytes='+$bytes)
