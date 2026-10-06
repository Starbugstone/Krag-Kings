"""Prepared staged original-TRELLIS shape study, not a production asset exporter.

One neural model is resident per process. Intermediate tensors are retained so
an actual memory/kernel failure does not discard completed inference stages.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p=argparse.ArgumentParser()
p.add_argument('--stage',choices=['condition','structure','coordinates','latent'],required=True)
a=p.parse_args()
os.environ.update(ATTN_BACKEND='xformers',SPARSE_ATTN_BACKEND='xformers',SPARSE_BACKEND='spconv',SPCONV_ALGO='native',HF_HUB_OFFLINE='1',OMP_NUM_THREADS='4')
ROOT=Path(__file__).resolve().parents[4]
pilot=ROOT/'benchmark/local/trellis-original-pilot-v1'
source=pilot/'source';weights=pilot/'weights';out=pilot/'krag-bust-study-v1'
out.mkdir(exist_ok=True)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
# Read large weights in bounded chunks rather than materializing them in RAM.
def file_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
prepared=json.loads((pilot/'source-preparation.json').read_text())
for name,expected in {row['path']:row['preparedSha256'] for row in prepared['changes']}.items():
    assert file_sha(source/name)==expected
receipt=json.loads((weights/'download-receipt.json').read_text())
assert receipt['status']=='Actual public pilot weights downloaded; inference has not run'
sys.path.insert(0,str(source))
import torch
import numpy as np
from trellis import models
from trellis.pipelines import samplers
from trellis.pipelines.trellis_image_to_3d import TrellisImageTo3DPipeline
from trellis.modules import sparse as sp

torch.set_num_threads(4)
assert torch.cuda.is_available()
torch.cuda.set_per_process_memory_fraction(.70)
free,total=torch.cuda.mem_get_info()
assert free>4*1024**3, 'At least4GiB free VRAM required before a stage'
torch.cuda.reset_peak_memory_stats()
config=json.loads((ROOT/'benchmark/local/trellis-original-feasibility/pipeline.json').read_text())['args']
manifest=json.loads((ROOT/'benchmark/local/trellis-original-feasibility/mesh-stage-manifest.json').read_text())
final=out/(a.stage+'.pt');report_path=out/(a.stage+'.json')
assert not final.exists() and not report_path.exists(), 'Preserve existing stage/failure'
started=time.perf_counter();report={'stage':a.stage,'status':'running','recipeSha256':sha(Path(__file__)),'seed':31,'sourceConceptUploaded':False,'artisticAcceptance':False}
report_path.write_text(json.dumps(report,indent=2)+'\n')
def read(name):
    record=json.loads((out/(name+'.json')).read_text())
    path=out/(name+'.pt')
    assert record['status']=='Actual stage completed' and file_sha(path)==record['outputSha256']
    return torch.load(path,map_location='cpu',weights_only=True)
def model(role):
    item=next(s for s in manifest if s['role']==role)
    path=weights/item['weight']['rfilename']
    assert file_sha(path)==item['weight']['lfs']['sha256']
    assert file_sha(path.with_suffix('.json'))==item['configSha256']
    return models.from_pretrained(str(path.with_suffix(''))).eval().cuda()
def condition():return {k:v.cuda() for k,v in read('condition').items()}
def sample(name):
    cfg=config[name]
    return getattr(samplers,cfg['name'])(**cfg['args']),cfg['params']
try:
    with torch.inference_mode():
        torch.manual_seed(31)
        if a.stage=='condition':
            dino=ROOT/'benchmark/local/trellis-original-feasibility/dinov2'
            revision=subprocess.check_output(['git','-C',str(dino),'rev-parse','HEAD'],text=True).strip()
            assert revision=='7764ea0f912e53c92e82eb78a2a1631e92725fc8'
            sys.path.insert(0,str(dino))
            from dinov2.hub.backbones import dinov2_vitl14_reg
            path=weights/'dinov2_vitl14_reg4_pretrain.pth'
            expected=next(x for x in receipt['files'] if Path(x['path']).name==path.name)
            assert file_sha(path)==expected['sha256']
            net=dinov2_vitl14_reg(pretrained=False).eval()
            net.load_state_dict(torch.load(path,map_location='cpu',weights_only=True),strict=True)
            net.cuda()
            from PIL import Image
            input_path=ROOT/'benchmark/unreal/evidence/triposr-krag-bust-matted-v2/input/foreground-original-rgb.png'
            assert file_sha(input_path)=='3733b77247fcabfab1dd715f0b13e06e27e15df8beb77deaa18ab528435ba8a2'
            image=Image.open(input_path)
            assert image.mode=='RGBA'
            pipe=TrellisImageTo3DPipeline()
            image=pipe.preprocess_image(image)
            values=torch.from_numpy(np.array(image).astype(np.float32)/255).permute(2,0,1).unsqueeze(0).cuda()
            values=(values-torch.tensor([.485,.456,.406],device='cuda')[None,:,None,None])/torch.tensor([.229,.224,.225],device='cuda')[None,:,None,None]
            features=net(values,is_training=True)['x_prenorm']
            cond=torch.nn.functional.layer_norm(features,features.shape[-1:])
            result={'cond':cond.cpu(),'neg_cond':torch.zeros_like(cond).cpu()}
            report['inputSha256']=file_sha(input_path);report['conditionShape']=list(cond.shape)
        elif a.stage=='structure':
            net=model('sparse_structure_flow_model');sampler,params=sample('sparse_structure_sampler')
            noise=torch.randn(1,net.in_channels,net.resolution,net.resolution,net.resolution).cuda()
            result=sampler.sample(net,noise,**condition(),**params,verbose=True).samples.cpu()
            assert torch.isfinite(result).all()
        elif a.stage=='coordinates':
            net=model('sparse_structure_decoder');decoded=net(read('structure').cuda())
            result=torch.argwhere(decoded>0)[:,[0,2,3,4]].int().cpu()
            assert 0<len(result)<=40000, 'Occupancy exceeds bounded pilot size; preserve latent for review'
            report['occupiedCoordinates']=len(result)
        else:
            net=model('slat_flow_model');sampler,params=sample('slat_sampler')
            coords=read('coordinates').cuda()
            noise=sp.SparseTensor(feats=torch.randn(len(coords),net.in_channels).cuda(),coords=coords)
            latent=sampler.sample(net,noise,**condition(),**params,verbose=True).samples
            std=torch.tensor(config['slat_normalization']['std'],device='cuda')[None]
            mean=torch.tensor(config['slat_normalization']['mean'],device='cuda')[None]
            latent=latent*std+mean
            result={'features':latent.feats.cpu(),'coordinates':latent.coords.cpu()}
            assert torch.isfinite(result['features']).all()
        torch.cuda.synchronize()
        temp=final.with_suffix('.partial');assert not temp.exists()
        torch.save(result,temp);temp.rename(final)
    report.update(status='Actual stage completed',elapsedSeconds=time.perf_counter()-started,outputSha256=file_sha(final),peakAllocatedBytes=torch.cuda.max_memory_allocated(),peakReservedBytes=torch.cuda.max_memory_reserved())
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('TRELLIS_ORIGINAL_STAGE_COMPLETE',a.stage,flush=True)
except Exception as error:
    report.update(status='Actual stage failed',error=repr(error),elapsedSeconds=time.perf_counter()-started)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    raise
