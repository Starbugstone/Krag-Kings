[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Video,
 [Parameter(Mandatory=$true)][string]$Ffmpeg,
 [Parameter(Mandatory=$true)][string]$OutputDirectory,
 [double]$AudioOffsetSeconds=0
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
$report=[ordered]@{passed=$false;scope='Known 72-second showcase camera/pose cues; excludes top and bottom HUD';visualAcceptance=$false;minimumMeanAbsoluteDifference=.005;minimumChangedPixelFraction=.05;frames=@();comparisons=@()}
$path=Join-Path $OutputDirectory 'motion-check.json'
function Invoke-MotionNative([string]$Executable,[string[]]$NativeArguments,[string]$Log){
 $quoted=@($NativeArguments|ForEach-Object {if($_ -match '[\s"]'){'"'+($_ -replace '"','\"')+'"'}else{$_}})
 $info=New-Object Diagnostics.ProcessStartInfo
 $info.FileName=$Executable;$info.Arguments=$quoted -join ' ';$info.UseShellExecute=$false;$info.CreateNoWindow=$true
 $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
 $process=New-Object Diagnostics.Process;$process.StartInfo=$info
 if(-not $process.Start()){throw "Could not start $Executable"}
 $null=$process.Handle;$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync();$process.WaitForExit()
 $text=$stderr.Result;if($Log){[IO.File]::WriteAllText($Log,$text)}
 if($process.ExitCode -ne 0){throw "Motion-analysis command failed: $text"}
 return $stdout.Result
}
try{
 $pixels=@{}
 foreach($cue in @(3,18,31,41,54,64)){
  $raw=Join-Path $OutputDirectory ("cue-{0:00}.gray" -f $cue)
  $time=($cue+$AudioOffsetSeconds).ToString('F4',[Globalization.CultureInfo]::InvariantCulture)
  # A small central viewport sample catches a frozen D3D surface even if its
  # overlay changes. It is diagnostic analysis, not replacement video footage.
  Invoke-MotionNative $Ffmpeg @('-hide_banner','-loglevel','error','-nostdin','-y','-threads','1','-ss',$time,'-i',$Video,'-frames:v','1','-filter_threads','1','-vf','crop=iw:ih*0.75:0:ih*0.125,scale=128:72:flags=area,format=gray','-f','rawvideo',$raw) (Join-Path $OutputDirectory ("cue-{0:00}.log" -f $cue))|Out-Null
  $pixels[$cue]=[IO.File]::ReadAllBytes($raw)
  if($pixels[$cue].Length -ne 9216){throw "Unexpected decoded frame dimensions at cue $cue"}
  $report.frames+=@{cueSeconds=$cue;videoSeconds=[double]$time;sha256=(Get-FileHash $raw -Algorithm SHA256).Hash.ToLower()}
 }
 foreach($pair in @(@(3,18),@(3,31),@(3,41),@(31,41),@(54,64))){
  $a=$pixels[$pair[0]];$b=$pixels[$pair[1]];$sum=0.0;$changed=0
  for($i=0;$i -lt $a.Length;$i++){$difference=[Math]::Abs([int]$a[$i]-[int]$b[$i]);$sum+=$difference;if($difference -gt 2){$changed++}}
  $mean=$sum/($a.Length*255.0);$fraction=$changed/[double]$a.Length
  $passed=$mean -ge $report.minimumMeanAbsoluteDifference -and $fraction -ge $report.minimumChangedPixelFraction
  $report.comparisons+=@{fromCue=$pair[0];toCue=$pair[1];meanAbsoluteDifference=$mean;changedPixelFraction=$fraction;passed=$passed}
 }
 $freezeLog=Join-Path $OutputDirectory 'freeze-detection.log'
 Invoke-MotionNative $Ffmpeg @('-hide_banner','-loglevel','info','-nostdin','-threads','1','-i',$Video,'-an','-filter_threads','1','-vf','crop=iw:ih*0.75:0:ih*0.125,scale=128:72:flags=area,freezedetect=n=-60dB:d=5','-f','null','-') $freezeLog|Out-Null
 $probe=Join-Path (Split-Path $Ffmpeg) 'ffprobe.exe'
 $videoInfo=Invoke-MotionNative $probe @('-v','error','-show_format','-of','json',$Video) ''|ConvertFrom-Json
 $duration=[double]::Parse([string]$videoInfo.format.duration,[Globalization.CultureInfo]::InvariantCulture)
 $freezeText=Get-Content $freezeLog -Raw;$intervals=@();$openStart=$null
 foreach($event in [regex]::Matches($freezeText,'freeze_(start|end):\s*([0-9.eE+\-]+)')){
  $value=[double]::Parse($event.Groups[2].Value,[Globalization.CultureInfo]::InvariantCulture)
  if($event.Groups[1].Value -eq 'start'){$openStart=$value}
  elseif($null -ne $openStart){$intervals+=@{startSeconds=$openStart;endSeconds=$value;durationSeconds=$value-$openStart};$openStart=$null}
 }
 if($null -ne $openStart){$intervals+=@{startSeconds=$openStart;endSeconds=$duration;durationSeconds=$duration-$openStart}}
 $longest=0.0;foreach($interval in $intervals){$longest=[Math]::Max($longest,$interval.durationSeconds)}
 $report.freezeDetection=@{noiseThresholdDb=-60;minimumDurationSeconds=5;longestPlateauSeconds=$longest;intervals=$intervals;passed=($longest -lt 5)}
 $report.passed=(@($report.comparisons|Where-Object {-not $_.passed}).Count -eq 0) -and $report.freezeDetection.passed
 if(-not $report.passed){throw 'Known moving/wide/portrait showcase cues are visually stale or too similar. Preserve raw evidence; reject this recording and inspect the capture backend.'}
 Write-Output 'SHOWCASE_MOTION_CHECK_PASS'
} catch {$report.error=$_.Exception.Message;throw}
finally{$report|ConvertTo-Json -Depth 8|Set-Content $path -Encoding UTF8}
