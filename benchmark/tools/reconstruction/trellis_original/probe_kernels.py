"""Small actual GPU compatibility probes; no weights or concept images loaded."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['ATTN_BACKEND'] = 'xformers'
os.environ['SPARSE_ATTN_BACKEND'] = 'xformers'
os.environ['SPARSE_BACKEND'] = 'spconv'
os.environ['SPCONV_ALGO'] = 'native'
os.environ['OMP_NUM_THREADS'] = '4'
ROOT = Path(__file__).resolve().parents[4]
pilot = ROOT/'benchmark/local/trellis-original-pilot-v1'
source = pilot/'source'
record = json.loads((pilot/'source-preparation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
final_hashes = {change['path']: change['preparedSha256'] for change in record['changes']}
for relative, expected in final_hashes.items():
    assert sha(source/relative) == expected
sys.path.insert(0, str(source))
import torch
import xformers
import xformers.ops as xops
import spconv.pytorch as spconv

out = pilot/'kernel-probe'
assert not out.exists(), 'Preserve previous actual probe'
out.mkdir()
report = {'status':'running', 'torch':torch.__version__, 'xformers':xformers.__version__,
          'cuda':torch.version.cuda, 'recipeSha256':sha(Path(__file__)),
          'sourcePreparationSha256':sha(pilot/'source-preparation.json'),
          'modelWeightsLoaded':False, 'inferenceRan':False, 'checks':[]}
def check(name, operation):
    start=time.perf_counter()
    result=operation()
    torch.cuda.synchronize()
    report['checks'].append({'name':name, 'elapsedSeconds':time.perf_counter()-start, **result})
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('KERNEL_PROBE', name, result, flush=True)
try:
    assert torch.cuda.is_available(), 'CUDA unavailable'
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(.60)
    props=torch.cuda.get_device_properties(0)
    report['device']={'name':props.name,'capability':[props.major,props.minor],'vramBytes':props.total_memory}
    free,total=torch.cuda.mem_get_info()
    assert free >= 3*1024**3, 'Insufficient free GPU memory for bounded kernel pilot'
    torch.cuda.reset_peak_memory_stats()
    def attention():
        torch.manual_seed(31)
        q,k,v=[torch.randn((1,512,8,64),device='cuda',dtype=torch.float16) for _ in range(3)]
        actual=xops.memory_efficient_attention(q,k,v)
        reference=torch.nn.functional.scaled_dot_product_attention(q.float().transpose(1,2),k.float().transpose(1,2),v.float().transpose(1,2)).transpose(1,2)
        error=(actual.float()-reference).abs().max().item()
        assert torch.isfinite(actual).all() and error<.01, error
        return {'shape':list(actual.shape),'maximumAbsoluteErrorVsFloat32':error,'tolerance':.01}
    check('fp16_memory_efficient_attention',attention)
    def convolution():
        coords=torch.cartesian_prod(*(torch.arange(4,device='cuda') for _ in range(3))).int()
        coords=torch.cat([torch.zeros((len(coords),1),device='cuda',dtype=torch.int32),coords],1)
        feats=torch.randn((len(coords),32),device='cuda',dtype=torch.float32)
        layer=spconv.SubMConv3d(32,32,3,padding=1,bias=False,algo=spconv.ConvAlgo.Native).cuda().eval()
        with torch.inference_mode(): actual=layer(spconv.SparseConvTensor(feats,coords,[4,4,4],1))
        assert actual.features.shape==feats.shape and torch.isfinite(actual.features).all()
        layer.half()
        with torch.inference_mode(): half=layer(spconv.SparseConvTensor(feats.half(),coords,[4,4,4],1))
        error=(actual.features-half.features.float()).abs().max().item()
        assert torch.isfinite(half.features).all() and error<.01, error
        return {'shape':list(actual.features.shape),'allFinite':True,
                'dtypes':[str(actual.features.dtype),str(half.features.dtype)],
                'maximumHalfAbsoluteErrorVsFloat32':error,'tolerance':.01}
    check('spconv_native_small_grid',convolution)
    def mesh():
        from trellis.representations.mesh.flexicubes.flexicubes import FlexiCubes, check_tensor
        from trellis.representations.mesh.utils_cube import construct_dense_grid
        assert check_tensor(torch.zeros((2,3)),(None,3),throw=False)
        assert not check_tensor(torch.zeros((2,4)),(None,3),throw=False)
        vertices,cubes=construct_dense_grid(8,'cuda')
        vertices=vertices.float()/8-.5
        sdf=torch.linalg.vector_norm(vertices,dim=1)-.3
        result=FlexiCubes('cuda')(vertices,sdf,cubes,8)
        verts,faces=result[:2]
        assert len(verts)>0 and len(faces)>0 and torch.isfinite(verts).all()
        assert int(faces.min())>=0 and int(faces.max())<len(verts)
        return {'vertices':len(verts),'triangles':len(faces),'allFinite':True}
    check('flexicubes_small_sphere',mesh)
    report['status']='Small native kernels passed; full inference remains untested'
    report['peakAllocatedBytes']=torch.cuda.max_memory_allocated()
    report['peakReservedBytes']=torch.cuda.max_memory_reserved()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('TRELLIS_ORIGINAL_KERNEL_PROBE_COMPLETE',flush=True)
except Exception as error:
    report['status']='Actual kernel probe failed'
    report['error']=repr(error)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    raise
