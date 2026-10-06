[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Video,
 [Parameter(Mandatory=$true)][double]$AudioOffsetSeconds,
 [Parameter(Mandatory=$true)][string]$OutputDirectory,
 [string]$Ffmpeg=''
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if(-not $Ffmpeg){$Ffmpeg=Join-Path $repo 'benchmark\local\capture\ffmpeg-compatible\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe'}
if(-not(Test-Path -LiteralPath $Video -PathType Leaf)){throw 'Actual recorded video is required.'}
if($AudioOffsetSeconds -lt 0 -or $AudioOffsetSeconds -gt 30){throw 'Expected the capture report measured audio/engine-start offset.'}
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
$OutputDirectory=(Resolve-Path $OutputDirectory).Path
$cues=@(
 @{seconds=3;label='wide pair';file='frame-03.png'},
 @{seconds=7.7;label='walk and run';file='action-07.7-walk.png'},
 @{seconds=14.4;label='concurrent melee and shooting';file='action-14.4-overlap.png'},
 @{seconds=16.4;label='bionic action poses';file='action-16.4-bionics.png'},
 @{seconds=18;label='coarse hit boundary';file='frame-18.png'},
 @{seconds=18.3;label='hit reactions';file='action-18.3-hit.png'},
 @{seconds=22;label='variant movement';file='frame-22.png'},
 @{seconds=24.4;label='shooting and melee';file='action-24.4-actions.png'},
 @{seconds=26;label='variant body view';file='frame-26.png'},
 @{seconds=31;label='Nib facial performance';file='frame-31.png'},
 @{seconds=36.9;label='Nib shooting portrait';file='action-36.9-nib-shoot.png'},
 @{seconds=41;label='Krag facial performance';file='frame-41.png'},
 @{seconds=46.0;label='Krag melee portrait';file='action-46.0-krag-melee.png'},
 @{seconds=47.4;label='Krag shooting portrait';file='action-47.4-krag-shoot.png'},
 @{seconds=54;label='bionic carousel';file='frame-54.png'},
 @{seconds=64;label='closing movement';file='frame-64.png'}
)
$samples=@()
foreach($cue in $cues){
 $videoSeconds=[double]$cue.seconds+$AudioOffsetSeconds
 $time=$videoSeconds.ToString('F4',[Globalization.CultureInfo]::InvariantCulture)
 $image=Join-Path $OutputDirectory $cue.file
 & $Ffmpeg -hide_banner -loglevel error -nostdin -y -threads 1 -filter_threads 1 -ss $time -i $Video -frames:v 1 $image
 if($LASTEXITCODE -ne 0 -or -not(Test-Path -LiteralPath $image)){throw ('Could not extract actual review frame at '+$time)}
 $samples+= [ordered]@{showcaseSeconds=[double]$cue.seconds;videoSeconds=$videoSeconds;purpose=$cue.label;file=$cue.file;sha256=(Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$report=[ordered]@{source='Frames decoded from actual recorded game video at measured engine-start offset';video=(Resolve-Path $Video).Path;videoSha256=(Get-FileHash -LiteralPath $Video -Algorithm SHA256).Hash.ToLowerInvariant();audioOffsetSeconds=$AudioOffsetSeconds;visualAcceptance=$false;samples=$samples}
$report|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $OutputDirectory 'review-frame-samples.json') -Encoding UTF8
Write-Output ('SHOWCASE_REVIEW_FRAMES_COMPLETE '+$OutputDirectory)
