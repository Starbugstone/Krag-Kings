"""One local, offline, unrigged Krag-bust reference inference; no shared writes."""
import argparse
import datetime
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'benchmark/local/triposr-reference-v1'
PLAN = Path(__file__).with_name('krag-bust-pilot.plan.json')


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=PLAN)
    args = parser.parse_args()
    selected_plan = args.plan.resolve()
    if os.name != 'nt' or Path(sys.executable).resolve() != (BASE/'venv/Scripts/python.exe').resolve():
        raise RuntimeError('Use only the isolated Windows interpreter')
    installation = json.loads((BASE/'installation.json').read_text(encoding='utf-8'))
    plan = json.loads(selected_plan.read_text(encoding='utf-8'))
    if not installation['pipCheckPassed'] or not installation['cpuExtensionSmokePassed']:
        raise RuntimeError('Actual isolated installation checks have not passed')
    model = BASE/'models/TripoSR'
    if sha(model/'model.ckpt') != plan['inferenceProposal']['modelSha256']:
        raise RuntimeError('Pinned model content changed')
    data = ROOT/plan['input']['outputDirectory']
    conditioning = data/'conditioning.png'
    input_receipt = json.loads((data/'input-receipt.json').read_text(encoding='utf-8'))
    if input_receipt['planSha256'] != sha(selected_plan) or sha(conditioning) != input_receipt['outputs']['conditioning.png']:
        raise RuntimeError('Conditioning image differs from the approved preprocessing receipt')
    output = ROOT/plan.get('outputDirectory', 'benchmark/local/triposr-reference-v1/pilot-krag-bust-v1')
    if output.exists():
        raise RuntimeError('Preserve the first pilot result; no automatic second inference')
    output.mkdir()
    os.environ.update({'HF_HOME':str(BASE/'cache/huggingface'),
        'HF_HUB_CACHE':str(BASE/'cache/huggingface/hub'),
        'HUGGINGFACE_HUB_CACHE':str(BASE/'cache/huggingface/hub'),
        'TRANSFORMERS_CACHE':str(BASE/'cache/huggingface/hub'),
        'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
        'DO_NOT_TRACK':'1','TORCH_HOME':str(BASE/'cache/torch'),
        'TORCH_EXTENSIONS_DIR':str(BASE/'cache/torch-extensions'),'U2NET_HOME':str(BASE/'cache/u2net'),
        'OMP_NUM_THREADS':'2','TMP':str(BASE/'temp'),'TEMP':str(BASE/'temp')})
    sys.path.insert(0,str(BASE/'sources/TripoSR'))
    result={'status':'RUNNING','utcStarted':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'planSha256':sha(selected_plan),'recipeSha256':sha(__file__),
        'installationSha256':sha(BASE/'installation.json'),'inputReceiptSha256':sha(data/'input-receipt.json'),
        'inferenceProposal':plan['inferenceProposal'],'artisticAcceptance':False,
        'rigged':False,'sharedAssetsChanged':False,'imageUploaded':False}
    started=time.monotonic()
    try:
        import numpy as np
        import torch
        from PIL import Image
        from tsr.system import TSR
        torch.set_num_threads(2)
        torch.manual_seed(0)
        np.random.seed(0)
        from torchmcubes import marching_cubes
        import trimesh
        policy=plan['inferenceProposal']
        gpu_available=torch.cuda.is_available()
        free=total=0
        if gpu_available:
            torch.cuda.set_device('cuda:0')
            free,total=torch.cuda.mem_get_info()
            result['gpuPreflight']={'name':torch.cuda.get_device_name(),
                'initialFreeBytes':free,'totalBytes':total}
        if gpu_available and free>=policy['minimumFreeGiBForFp32']*1024**3:
            device='cuda:0';half=False
        elif gpu_available and free>=policy['minimumFreeGiBForAutocast']*1024**3:
            device='cuda:0';half=True
        else:
            device='cpu';half=False
        if policy.get('requireFp16CudaForMatchedAB') and (device != 'cuda:0' or not half):
            raise RuntimeError('Matched A/B requires sufficient free VRAM for the same FP16 CUDA forward; no model was loaded')
        result['device']={'selected':device,'torchVersion':torch.__version__,
            'cudaRuntime':torch.version.cuda,'selectedBeforeModelLoad':True}
        result['precision']='FP16 CUDA autocast forward; FP32 streamed field queries/CPU extraction' if half else 'FP32 '+device+' forward and streamed extraction'
        result['extraction']={'gridResolution':policy['marchingCubesResolution'],
            'maxPositionsPerQuery':policy['chunkSize'],'densityStorage':'CPU float32',
            'marchingCubes':'Pinned CPU extension','fullGpuGridAllocated':False}
        def sync():
            if device.startswith('cuda'):torch.cuda.synchronize()
        if device.startswith('cuda'):torch.cuda.reset_peak_memory_stats()
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        stage=time.monotonic()
        network=TSR.from_pretrained(str(model),config_name='config.yaml',weight_name='model.ckpt')
        network.eval()
        network.renderer.set_chunk_size(policy['chunkSize'])
        network.to(device)
        sync()
        result['modelLoadSeconds']=time.monotonic()-stage
        stage=time.monotonic()
        autocast=torch.autocast(device_type='cuda',dtype=torch.float16) if half else contextlib.nullcontext()
        with Image.open(conditioning) as image, torch.inference_mode(), autocast:
            scene_codes=network([image.convert('RGB')],device=device)
        sync()
        result['inferenceSeconds']=time.monotonic()-stage
        result['sceneCodeDtype']=str(scene_codes.dtype)
        scene_code=scene_codes[0].float()
        del scene_codes
        stage=time.monotonic()
        resolution=policy['marchingCubesResolution']
        chunk=policy['chunkSize']
        radius=network.renderer.cfg.radius
        # Exact same ij grid ordering and linspace values as the official helper,
        # constructed in small batches rather than a full GPU coordinate tensor.
        def positions(n,limit):
            axis=torch.linspace(0,1,n)
            for start in range(0,n**3,limit):
                indices=torch.arange(start,min(start+limit,n**3))
                xyz=torch.stack((axis[indices//(n*n)],axis[(indices//n)%n],axis[indices%n]),dim=-1)
                yield start,xyz
        xs=torch.linspace(0,1,8)
        gx,gy,gz=torch.meshgrid(xs,xs,xs,indexing='ij')
        official=torch.stack((gx.reshape(-1),gy.reshape(-1),gz.reshape(-1)),dim=-1)
        streamed=torch.cat([values for _,values in positions(8,23)])
        if not torch.equal(official,streamed):raise RuntimeError('Streamed grid differs from official axis order')
        result['streamedGridOrderingCheckPassed']=True
        density=torch.empty(resolution**3,dtype=torch.float32)
        with torch.inference_mode():
            for offset,xyz in positions(resolution,chunk):
                points=(xyz*(2*radius)-radius).to(device)
                field=network.renderer.query_triplane(network.decoder,points,scene_code)
                density[offset:offset+len(xyz)]=field['density_act'].reshape(-1).float().cpu()
                del field,points
                if offset%(chunk*256)==0:print('DENSITY_PROGRESS',offset,resolution**3,flush=True)
        vertices,faces=marching_cubes((density.reshape(resolution,resolution,resolution)-25.0).contiguous(),0.0)
        vertices=(vertices[:,[2,1,0]]/(resolution-1.0))*(2*radius)-radius
        colors=torch.empty((len(vertices),3),dtype=torch.float32)
        with torch.inference_mode():
            for offset in range(0,len(vertices),chunk):
                points=vertices[offset:offset+chunk].to(device)
                field=network.renderer.query_triplane(network.decoder,points,scene_code)
                colors[offset:offset+len(points)]=field['color'].float().cpu()
                del field,points
        meshes=[trimesh.Trimesh(vertices=vertices.numpy(),faces=faces.numpy(),vertex_colors=colors.numpy())]
        sync()
        result['extractionSeconds']=time.monotonic()-stage
        if len(meshes)!=1 or len(meshes[0].vertices)==0 or len(meshes[0].faces)==0:
            raise RuntimeError('No usable mesh was produced')
        mesh=meshes[0]
        if not np.isfinite(mesh.vertices).all():
            raise RuntimeError('Generated geometry contains non-finite coordinates')
        target=output/'Krag_Bust_Reference.glb'
        mesh.export(target)
        result.update({'status':'REFERENCE_GEOMETRY_GENERATED_REQUIRES_VISUAL_REVIEW',
            'vertices':len(mesh.vertices),'triangles':len(mesh.faces),
            'bounds':mesh.bounds.tolist(),'watertight':bool(mesh.is_watertight),
            'outputSha256':sha(target),'outputBytes':target.stat().st_size,
            'torchPeakAllocatedBytes':torch.cuda.max_memory_allocated() if device.startswith('cuda') else None,
            'torchPeakReservedBytes':torch.cuda.max_memory_reserved() if device.startswith('cuda') else None,
            'tf32':False,
            'neutralGeometryReviewExecuted':False})
    except Exception as error:
        result.update({'status':'FAILED','errorType':type(error).__name__,'error':str(error)})
        if 'torch' in locals() and torch.cuda.is_initialized():
            result['torchPeakAllocatedBytes']=torch.cuda.max_memory_allocated()
            result['torchPeakReservedBytes']=torch.cuda.max_memory_reserved()
        raise
    finally:
        result['elapsedSeconds']=time.monotonic()-started
        result['utcFinished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output/'pilot-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('TRIPOSR_REFERENCE_PILOT_GENERATED',flush=True)


if __name__=='__main__':
    main()
