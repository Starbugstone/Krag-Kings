"""Prepared separated neural surface features and CPU FlexiCubes extraction.

The network feature path is unchanged. A one-cell extractor supplies only the
output-channel layout during GPU inference; the actual 256-grid extraction is
performed in a separate guarded CPU process after the neural model is gone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

p=argparse.ArgumentParser();p.add_argument('--stage',choices=['mesh-features','mesh-extract'],required=True);a=p.parse_args()
os.environ.update(ATTN_BACKEND='xformers',SPARSE_ATTN_BACKEND='xformers',SPARSE_BACKEND='spconv',SPCONV_ALGO='native',HF_HUB_OFFLINE='1',OMP_NUM_THREADS='4')
ROOT=Path(__file__).resolve().parents[4];pilot=ROOT/'benchmark/local/trellis-original-pilot-v1';source=pilot/'source';weights=pilot/'weights';out=pilot/'krag-bust-study-v1'
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
prepared=json.loads((pilot/'source-preparation.json').read_text())
for name,expected in {r['path']:r['preparedSha256'] for r in prepared['changes']}.items():assert sha(source/name)==expected
sys.path.insert(0,str(source))
import torch
import numpy as np
from trellis import models
from trellis.modules import sparse as sp
from trellis.representations.mesh import SparseFeatures2Mesh

torch.set_num_threads(4)
record_path=out/(a.stage+'.json');assert not record_path.exists(),'Preserve earlier actual stage'
record={'status':'running','stage':a.stage,'recipeSha256':sha(Path(__file__)),'artisticAcceptance':False,'engineIntegrated':False,'sourceConceptUploaded':False};started=time.perf_counter()
record_path.write_text(json.dumps(record,indent=2)+'\n')
def read(name):
    meta=json.loads((out/(name+'.json')).read_text());path=out/(name+'.pt')
    assert meta['status']=='Actual stage completed' and sha(path)==meta['outputSha256']
    return torch.load(path,map_location='cpu',weights_only=True)
try:
    with torch.inference_mode():
        if a.stage=='mesh-features':
            assert torch.cuda.is_available()
            torch.cuda.set_per_process_memory_fraction(.70)
            assert torch.cuda.mem_get_info()[0]>4*1024**3
            torch.cuda.reset_peak_memory_stats()
            from trellis.models.structured_latent_vae import decoder_mesh
            from trellis.models.structured_latent_vae.base import SparseTransformerBase
            original=decoder_mesh.SparseFeatures2Mesh
            def metadata_extractor(**kwargs):return original(device='cpu',res=1,use_color=kwargs['use_color'])
            decoder_mesh.SparseFeatures2Mesh=metadata_extractor
            config_path=weights/'ckpts/slat_dec_mesh_swin8_B_64l8m256c_fp16'
            manifest=json.loads((ROOT/'benchmark/local/trellis-original-feasibility/mesh-stage-manifest.json').read_text())
            pin=next(m for m in manifest if m['role']=='slat_decoder_mesh')
            assert sha(config_path.with_suffix('.safetensors'))==pin['weight']['lfs']['sha256']
            assert sha(config_path.with_suffix('.json'))==pin['configSha256']
            try:net=models.from_pretrained(str(config_path)).eval().cuda()
            finally:decoder_mesh.SparseFeatures2Mesh=original
            latent=read('latent');tensor=sp.SparseTensor(feats=latent['features'].cuda(),coords=latent['coordinates'].cuda())
            h=SparseTransformerBase.forward(net,tensor)
            for block in net.upsample:h=block(h)
            h=h.type(tensor.dtype);h=net.out_layer(h)
            assert h.feats.shape[1]==101 and torch.isfinite(h.feats).all()
            assert len(h.feats)<=2000000,'Surface occupancy exceeds bounded pilot size'
            result={'features':h.feats.cpu(),'coordinates':h.coords.cpu()}
            destination=out/'mesh-features.pt';assert not destination.exists()
            torch.save(result,destination)
            record.update(outputSha256=sha(destination),occupiedCoordinates=len(h.feats),featureChannels=h.feats.shape[1],peakAllocatedBytes=torch.cuda.max_memory_allocated(),peakReservedBytes=torch.cuda.max_memory_reserved())
        else:
            import psutil
            assert psutil.virtual_memory().available>=8*1024**3,'CPU extraction requires8GiB available'
            values=read('mesh-features')
            tensor=sp.SparseTensor(feats=values['features'],coords=values['coordinates'])
            extractor=SparseFeatures2Mesh(device='cpu',res=256,use_color=True)
            mesh=extractor(tensor,training=False)
            assert mesh.success and torch.isfinite(mesh.vertices).all()
            assert int(mesh.faces.min())>=0 and int(mesh.faces.max())<len(mesh.vertices)
            data={'vertices':mesh.vertices.numpy(),'faces':mesh.faces.numpy(),'attributes':mesh.vertex_attrs.numpy()}
            destination=out/'Krag_Bust_Trellis_Provisional.npz';assert not destination.exists()
            np.savez_compressed(destination,**data)
            record.update(outputSha256=sha(destination),vertices=len(mesh.vertices),triangles=len(mesh.faces),attributeChannels=mesh.vertex_attrs.shape[1],hasSkeleton=False,hasSeparateMouthInterior=False,unseenSurfacesProvisional=True)
    record.update(status='Actual stage completed',elapsedSeconds=time.perf_counter()-started)
    record_path.write_text(json.dumps(record,indent=2)+'\n')
    print('TRELLIS_ORIGINAL_MESH_STAGE_COMPLETE',a.stage,flush=True)
except Exception as error:
    record.update(status='Actual stage failed',error=repr(error),elapsedSeconds=time.perf_counter()-started)
    record_path.write_text(json.dumps(record,indent=2)+'\n')
    raise
