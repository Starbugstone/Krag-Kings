[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Unity','Unreal')][string]$Engine,
    [Parameter(Mandatory=$true)][string]$RuntimeLog,
    [Parameter(Mandatory=$true)][string]$StartFlag,
    [Parameter(Mandatory=$true)][string]$EngineAudio,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [int]$GameProcessId=0,
    [string]$WindowTitle='',
    [string]$Ffmpeg='',
    [ValidateRange(15,60)][int]$FrameRate=30,
    [ValidateRange(30,180)][int]$ShowcaseSeconds=72,
    [int]$ReadyTimeoutSeconds=120
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if(-not $Ffmpeg){$Ffmpeg=Join-Path $repo 'benchmark\local\capture\ffmpeg-compatible\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe'}
$ffprobe=Join-Path (Split-Path $Ffmpeg) 'ffprobe.exe'
foreach($tool in @($Ffmpeg,$ffprobe)){if(-not(Test-Path $tool)){throw "Capture tool missing: $tool"}}
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$OutputDirectory=(Resolve-Path $OutputDirectory).Path
$prefix=$Engine.ToLower()+'-showcase'
$raw=Join-Path $OutputDirectory ($prefix+'-video-only.mp4')
$final=Join-Path $OutputDirectory ($prefix+'.mp4')
$progress=Join-Path $OutputDirectory ($prefix+'-capture-progress.txt')
$reportPath=Join-Path $OutputDirectory ($prefix+'-capture.json')
if(Test-Path $final){throw "Existing reviewed output preserved; choose another directory: $final"}
if(Test-Path $StartFlag){throw 'Stale showcase start flag exists; relaunch the game in wait mode before recording.'}
if(Test-Path $EngineAudio){throw 'Existing engine audio preserved; remove/archive that task output before a fresh recording.'}

Add-Type @'
using System;using System.Runtime.InteropServices;
public static class KKCaptureWindow {
 [StructLayout(LayoutKind.Sequential)]public struct RECT {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")]public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]public static extern IntPtr FindWindow(string className,string title);
 [DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr hwnd);
 [DllImport("user32.dll")]public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")]public static extern bool IsWindow(IntPtr hwnd);
 [DllImport("user32.dll")]public static extern bool IsIconic(IntPtr hwnd);
 [DllImport("user32.dll")]public static extern bool GetClientRect(IntPtr hwnd,out RECT rect);
 [DllImport("user32.dll")]public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint processId);
}
'@
[KKCaptureWindow]::SetProcessDPIAware()|Out-Null
function Native-Argument([string]$Value){
    if($Value -notmatch '[\s"]'){return $Value}
    $escaped=[regex]::Replace($Value,'(\\*)"', '$1$1\"')
    $escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
    return '"'+$escaped+'"'
}
function Start-Native([string]$Executable,[string[]]$Arguments,[bool]$Interactive=$false){
    $info=New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName=$Executable;$info.Arguments=($Arguments|ForEach-Object {Native-Argument $_}) -join ' '
    $info.UseShellExecute=$false;$info.CreateNoWindow=$true
    $info.RedirectStandardError=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardInput=$Interactive
    $process=New-Object System.Diagnostics.Process;$process.StartInfo=$info
    if(-not $process.Start()){throw "Could not start $Executable"}
    $null=$process.Handle
    return [pscustomobject]@{process=$process;stderr=$process.StandardError.ReadToEndAsync();stdout=$process.StandardOutput.ReadToEndAsync()}
}
function Invoke-Native([string]$Executable,[string[]]$Arguments,[string]$Log){
    $job=Start-Native $Executable $Arguments
    $job.process.WaitForExit();$errorText=$job.stderr.Result;$output=$job.stdout.Result
    if($Log){[IO.File]::WriteAllText($Log,$errorText)}
    if($job.process.ExitCode -ne 0){throw "Native command failed ($($job.process.ExitCode)): $Executable. $errorText"}
    return $output
}
function Has-Marker([string]$Marker){
    if(-not(Test-Path $RuntimeLog)){return $false}
    return [bool](Get-Content $RuntimeLog -Tail 120 -ErrorAction SilentlyContinue | Select-String -SimpleMatch $Marker | Select-Object -First 1)
}
function Assert-Window {
    if(-not[KKCaptureWindow]::IsWindow($script:window) -or [KKCaptureWindow]::IsIconic($script:window)){throw 'The selected game window closed or minimized; recording stopped.'}
    if([KKCaptureWindow]::GetForegroundWindow() -ne $script:window){throw 'Game lost foreground; recording stopped without following or capturing another application.'}
    $rect=New-Object KKCaptureWindow+RECT
    [KKCaptureWindow]::GetClientRect($script:window,[ref]$rect)|Out-Null
    if($rect.Right -ne $script:clientWidth -or $rect.Bottom -ne $script:clientHeight){throw 'Game client size changed during recording; repeat with a stable viewport.'}
}
$report=[ordered]@{engine=$Engine;source='real-time capture of explicit game HWND client area';desktopCapture=$false;systemAudioCapture=$false;microphoneCapture=$false;encoder='h264_nvenc';recordingFrameRate=$FrameRate;gameFrameRateClaim=$false;ffmpeg=$Ffmpeg;showcaseSeconds=$ShowcaseSeconds;completed=$false;visualAcceptance=$false;startedUtc=[DateTime]::UtcNow.ToString('o')}
$capture=$null;$gateWritten=$false
try {
    $deadline=[DateTime]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
    while(-not(Has-Marker 'SHOWCASE_READY')){
        if([DateTime]::UtcNow -gt $deadline){throw 'Game did not report SHOWCASE_READY before timeout.'}
        Start-Sleep -Milliseconds 250
    }
    if(Has-Marker 'SHOWCASE_STARTED'){throw 'Showcase already started; launch with its wait flag and a fresh runtime log.'}
    if($GameProcessId){$game=Get-Process -Id $GameProcessId;$window=$game.MainWindowHandle}
    elseif($WindowTitle){$window=[KKCaptureWindow]::FindWindow($null,$WindowTitle)}
    else{throw 'Pass the intended game process ID or exact window title; desktop fallback is disabled.'}
    if($window -eq [IntPtr]::Zero){throw 'The intended game window is not visible yet.'}
    $windowOwner=[uint32]0;[KKCaptureWindow]::GetWindowThreadProcessId($window,[ref]$windowOwner)|Out-Null
    $game=Get-Process -Id $windowOwner
    if($game.ProcessName -notmatch 'KragKings|Krag-Kings'){throw "Unexpected target process '$($game.ProcessName)'; refusing window capture."}
    $client=New-Object KKCaptureWindow+RECT;[KKCaptureWindow]::GetClientRect($window,[ref]$client)|Out-Null
    $clientWidth=$client.Right;$clientHeight=$client.Bottom
    if($clientWidth -lt 640 -or $clientHeight -lt 360){throw 'Game client is too small for a review recording.'}
    [KKCaptureWindow]::SetForegroundWindow($window)|Out-Null;Start-Sleep -Milliseconds 250;Assert-Window
    $report.windowHandle=$window.ToInt64();$report.gameProcessId=$windowOwner;$report.windowTitle=$game.MainWindowTitle
    $report.clientWidth=$clientWidth;$report.clientHeight=$clientHeight
    if(Test-Path $progress){Remove-Item $progress}
    $arguments=@('-hide_banner','-loglevel','warning','-y','-stats_period','0.1','-thread_queue_size','8','-f','gdigrab','-draw_mouse','0','-framerate',"$FrameRate",'-i',('hwnd='+$window.ToInt64()),'-an','-vf','crop=trunc(iw/2)*2:trunc(ih/2)*2,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-c:v','h264_nvenc','-preset','p4','-tune','hq','-rc','vbr','-cq','19','-b:v','0','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart','-progress',$progress,$raw)
    $capture=Start-Native $Ffmpeg $arguments $true
    $readyDeadline=[DateTime]::UtcNow.AddSeconds(15);$firstMediaSeconds=$null
    do {
        Assert-Window
        if($capture.process.HasExited){throw ('Capture encoder exited before first frame: '+$capture.stderr.Result)}
        if(Test-Path $progress){
            $line=Get-Content $progress -Tail 35 -ErrorAction SilentlyContinue|Where-Object {$_ -match '^out_time_us=\d+$'}|Select-Object -Last 1
            if($line){$firstMediaSeconds=[double]($line.Split('=')[1])/1000000.0;$firstProgressUtc=[DateTime]::UtcNow;break}
        }
        Start-Sleep -Milliseconds 25
    }while([DateTime]::UtcNow -lt $readyDeadline)
    if($null -eq $firstMediaSeconds){throw 'No encoded frame progress; no showcase start signal was sent.'}
    $gateUtc=[DateTime]::UtcNow
    $audioOffset=[Math]::Max(0,$firstMediaSeconds+($gateUtc-$firstProgressUtc).TotalSeconds)
    New-Item -ItemType Directory -Force (Split-Path $StartFlag)|Out-Null
    [IO.File]::WriteAllText($StartFlag,$gateUtc.ToString('o'));$gateWritten=$true
    $report.gateUtc=$gateUtc.ToString('o');$report.audioOffsetSeconds=$audioOffset
    $report.audioSync='Offset from first encoded frame progress and gate wall clock; estimated within capture polling/audio start latency, requires listening review.'
    $showcaseDeadline=$gateUtc.AddSeconds($ShowcaseSeconds+25);$completedAt=$null
    while($true){
        Assert-Window
        if($capture.process.HasExited){throw ('Capture ended before showcase completion: '+$capture.stderr.Result)}
        if(-not $completedAt -and (Has-Marker 'SHOWCASE_COMPLETE')){$completedAt=[DateTime]::UtcNow}
        if($completedAt -and ([DateTime]::UtcNow-$completedAt).TotalSeconds -ge 2){break}
        if([DateTime]::UtcNow -gt $showcaseDeadline){throw 'No showcase completion marker within the recording deadline.'}
        Start-Sleep -Milliseconds 100
    }
    $capture.process.StandardInput.WriteLine('q');$capture.process.StandardInput.Flush()
    if(-not $capture.process.WaitForExit(15000)){$capture.process.Kill();throw 'Capture encoder did not finalize after its own stop request.'}
    [IO.File]::WriteAllText((Join-Path $OutputDirectory ($prefix+'-capture.log')),$capture.stderr.Result)
    if($capture.process.ExitCode -ne 0){throw 'Capture encoder returned a failure exit code.'}
    $audioDeadline=[DateTime]::UtcNow.AddSeconds(30);$previousSize=0;$stable=0
    while([DateTime]::UtcNow -lt $audioDeadline){
        if(Test-Path $EngineAudio){$size=(Get-Item $EngineAudio).Length;if($size -gt 44 -and $size -eq $previousSize){$stable++}else{$stable=0};$previousSize=$size;if($stable -ge 3){break}}
        Start-Sleep -Milliseconds 250
    }
    if($stable -lt 3){throw 'The game-only WAV did not finish exporting; raw video remains available without invented audio.'}
    $offset=$audioOffset.ToString('F4',[Globalization.CultureInfo]::InvariantCulture)
    $mux=@('-hide_banner','-loglevel','warning','-nostdin','-y','-i',$raw,'-itsoffset',$offset,'-i',$EngineAudio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',$final)
    Invoke-Native $Ffmpeg $mux (Join-Path $OutputDirectory ($prefix+'-mux.log'))|Out-Null
    $metadata=Invoke-Native $ffprobe @('-v','error','-show_streams','-show_format','-of','json',$final) ''|ConvertFrom-Json
    $video=$metadata.streams|Where-Object codec_type -eq 'video';$audio=$metadata.streams|Where-Object codec_type -eq 'audio'
    if(-not $video -or -not $audio -or [double]$metadata.format.duration -lt $ShowcaseSeconds){throw 'Muxed file lacks required video/audio/duration.'}
    $frames=Join-Path $OutputDirectory ($prefix+'-frames');New-Item -ItemType Directory -Force $frames|Out-Null
    foreach($seconds in @(3,18,22,26,31,41,54,64)){
        $time=($seconds+$audioOffset).ToString('F4',[Globalization.CultureInfo]::InvariantCulture)
        Invoke-Native $Ffmpeg @('-hide_banner','-loglevel','error','-nostdin','-y','-ss',$time,'-i',$final,'-frames:v','1',(Join-Path $frames ("frame-{0:00}.png" -f $seconds))) ''|Out-Null
    }
    $report.completed=$true;$report.output=$final;$report.engineAudio=$EngineAudio;$report.rawVideo=$raw
    $report.media=$metadata;$report.reviewFrames=$frames;$report.outputSha256=(Get-FileHash $final -Algorithm SHA256).Hash.ToLower()
    Write-Output ('CAPTURE_COMPLETE '+$final)
} catch {
    $report.error=$_.Exception.Message
    throw
} finally {
    if($capture -and -not $capture.process.HasExited){
        try{$capture.process.StandardInput.WriteLine('q');$capture.process.StandardInput.Flush();if(-not $capture.process.WaitForExit(5000)){$capture.process.Kill()}}catch{}
    }
    $report.finishedUtc=[DateTime]::UtcNow.ToString('o')
    $report|ConvertTo-Json -Depth 12|Set-Content $reportPath -Encoding UTF8
}
