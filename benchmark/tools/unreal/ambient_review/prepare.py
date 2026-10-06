"""Read the existing sand map and freeze a bounded lower-hemisphere study.

Requires Pillow/numpy only. Does not load Torch, an engine or an image model.
No runtime is launched and no source texture is edited.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise RuntimeError('Unsafe study name')
    out=Path(__file__).parent/'plans'/args.name
    if out.exists():raise RuntimeError('Preserve earlier prepared recipe')
    image=ROOT/'benchmark/shared/environment/Sand_BaseColor.png'
    rgb=np.asarray(Image.open(image).convert('RGB'),dtype=np.float32)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    mean=linear.mean(axis=(0,1),dtype=np.float64)
    sun_lux=55000;sun_elevation=42
    estimated_radiance=mean*(sun_lux*math.sin(math.radians(sun_elevation))/math.pi)
    if not np.isfinite(estimated_radiance).all() or max(estimated_radiance)>10000:raise RuntimeError('Invalid radiance range')
    pins=[image,Path(__file__).resolve(),
          ROOT/'benchmark/unreal/KragKingsBenchmark/Source/KragKingsBenchmark/KKBenchmarkGameMode.cpp',
          ROOT/'benchmark/unreal/KragKingsBenchmark/Source/KragKingsBenchmark/KKBenchmarkGameMode.h',
          ROOT/'benchmark/unreal/evidence/coherent79-import/import-source-snapshot.json']
    plan={'name':args.name,'status':'Prepared; new native code is not compiled and no ambient comparison has run',
        'image':{'path':image.relative_to(ROOT).as_posix(),'dimensions':[rgb.shape[1],rgb.shape[0]],'sha256':sha(image),'meanDecodedLinearRgb':mean.tolist()},
        'estimate':{'method':'Flat Lambertian sand approximation: mean decoded texture RGB * sunLux * sin(elevation) / pi',
                    'limitation':'Authored BaseColor is an appearance input, not measured spectral reflectance. This is a bounded far-field fill approximation, not a physically validated GI replacement.',
                    'sunLux':sun_lux,'sunElevationDegrees':sun_elevation,'unscaledLinearRgbRadiance':estimated_radiance.tolist(),
                    'fractions':[0,.125,.25],'existingSkylightIntensity':.85},
        'fixed':['source meshes and pose','Profile skin','camera','55klux neutral sun','manual physical exposure','upper sky','Lumen quality','native1080'],
        'pinSha256':{p.relative_to(ROOT).as_posix():sha(p) for p in pins},
        'requires':['Compile the exact pinned editor native module','Verify pins immediately before launch','Actual nine images and lighting report','Inspect lit/shaded contour and ground contact','Measure shipped candidate separately before accepting performance'],
        'artisticAcceptance':False,'performanceSample':False}
    base='D:\\Dev\\Krag-Kings\\benchmark\\local\\evidence\\unreal-ambient\\'+args.name
    job={'name':'unreal-ambient-'+args.name,'executable':'D:\\Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe',
         'arguments':['D:\\Dev\\Krag-Kings\\benchmark\\unreal\\KragKingsBenchmark\\KragKingsBenchmark.uproject','-game','-ResX=1920','-ResY=1080','-NoVSync','-KKSkinMode=Profile','-KKGroundBounceReview',
                      *['-KKGroundRadiance'+channel+'='+format(value,'.9f') for channel,value in zip('RGB',estimated_radiance)],
                      '-KKSkinReviewOutput='+base,'-abslog='+base+'\\runtime.log','-ExecCmds=sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,r.VolumetricFog 1'],
         'workingDirectory':'D:\\Dev\\Krag-Kings','stdout':base+'\\guard-stdout.log','stderr':base+'\\guard-stderr.log',
         'minAvailableGB':10,'maxPrivateGB':9,'gpuTelemetry':True,'successLog':base+'\\runtime.log','successMarker':'KK_GROUND_BOUNCE_REVIEW_COMPLETE'}
    out.mkdir(parents=True)
    for name,value in [('plan.json',plan),('review.job.json',job)]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n',newline='\n')
    print(json.dumps({'plan':str(out/'plan.json'),'linearAlbedo':mean.tolist(),'radiance':estimated_radiance.tolist(),'launched':False}))

if __name__=='__main__':main()
