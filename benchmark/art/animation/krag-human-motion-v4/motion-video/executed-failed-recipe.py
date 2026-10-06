"""Encode verified Blender frames as a silent source-review video, never FPS proof."""
import argparse,hashlib,json,subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise RuntimeError('Preserve previous motion video')
r=json.loads((a.review/'review.json').read_text());sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def local_path(text):
    # Review receipts are written by Windows Blender; encoding runs in WSL.
    if len(text)>2 and text[1]==':':return Path('/mnt/'+text[0].lower()+text[2:].replace('\\','/'))
    return Path(text)
for clip,entry in r['clips'].items():
    for view,frames in entry['views'].items():
        for frame in frames:
            path=local_path(frame['file'])
            if sha(path)!=frame['sha256']:raise RuntimeError('Review frame changed '+str(path))
a.output.mkdir(parents=True);commands=[];segments=[];timeline=[];cursor=0
for clip,repeats in [('Walk',4),('Run',4),('Idle',1)]:
    info=r['clips'][clip];count=len(info['views']['front']);rate=info['sampleRate']
    if count!=len(info['views']['side']):raise RuntimeError('Mismatched paired review count')
    seconds=count/rate*repeats;segment=a.output/(clip+'.mp4')
    cmd=[str(a.ffmpeg),'-hide_banner','-loglevel','error','-nostdin','-stream_loop',str(repeats-1),'-framerate',str(rate),'-i',str(a.review/clip/'front/%04d.png'),'-stream_loop',str(repeats-1),'-framerate',str(rate),'-i',str(a.review/clip/'side/%04d.png'),'-filter_complex_threads','1','-filter_complex','[0:v][1:v]hstack=inputs=2,fps=30,format=yuv420p[v]','-map','[v]','-an','-c:v','libx264','-threads','2','-preset','medium','-crf','18','-t',str(seconds),'-movflags','+faststart',str(segment)]
    subprocess.run(cmd,check=True,capture_output=True);commands.append(cmd);segments.append(segment)
    timeline.append({'clip':clip,'startSeconds':cursor,'durationSeconds':seconds,'cycles':repeats,'renderedSamplesPerSecond':rate,'encodedFramesPerSecond':30,'idleSamplesHeldNotInterpolated':clip=='Idle'});cursor+=seconds
concat=a.output/'segments.txt';concat.write_text(''.join("file '"+f.name+"'\n" for f in segments));target=a.output/'Actual_Blender_WholeBody_Motion.mp4';cmd=[str(a.ffmpeg),'-hide_banner','-loglevel','error','-nostdin','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(target)];subprocess.run(cmd,check=True,capture_output=True);commands.append(cmd)
# Full decode establishes container/frame integrity, without claiming that a
# model has visually watched uninterrupted playback or measured runtime FPS.
cmd=[str(a.ffmpeg),'-hide_banner','-nostdin','-threads','1','-i',str(target),'-map','0:v:0','-progress','pipe:1','-nostats','-f','null','-'];decode=subprocess.run(cmd,capture_output=True,text=True,check=True);(a.output/'decode.log.txt').write_text(decode.stderr);commands.append(cmd)
decoded_frames=[int(line.split('=',1)[1]) for line in decode.stdout.splitlines() if line.startswith('frame=')]
if not decoded_frames or decoded_frames[-1]!=round(cursor*30):raise RuntimeError('Decoded motion video frame count differs from source timeline')
report={'actualDecodedFrames':decoded_frames[-1],'sourceReview':str(a.review/'review.json'),'sourceReviewSha256':sha(a.review/'review.json'),'sourceBlendSha256':r['sourceSha256'],'video':target.name,'videoSha256':sha(target),'expectedDurationSeconds':cursor,'expectedEncodedFrames':round(cursor*30),'timeline':timeline,'silent':True,'sourceFramesVerified':True,'fullDecodeExit':0,'actualGameEngineCapture':False,'runtimePerformanceMeasurement':False,'continuousPlaybackVisuallyReviewed':False,'artisticAcceptance':False,'commands':commands}
(a.output/'video.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['video','videoSha256','expectedDurationSeconds','expectedEncodedFrames','fullDecodeExit']}))
