"""Prepared continuous aperture/closure proposal from the actual v5i cache.

This is a bounded construction study, not approved Nib dimensions. It keeps
both canthi, eye assemblies and nasal-domain anchors fixed. The existing
anatomical graph and actual opaque globe determine support and clearance.
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'v5_wip'))
from orbital_closure_v5i import OrbitalDomain,split_arcs,front_surface_y,eye_surface,propose

parser=argparse.ArgumentParser()
parser.add_argument('--output-cache',type=Path,required=True)
parser.add_argument('--output-report',type=Path,required=True)
args=parser.parse_args()
if args.output_cache.exists() or args.output_report.exists():
    raise RuntimeError('Preserve the previous numerical identity proposal')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_report_path=ROOT/'benchmark/art/nib/v5-study/native-v5i-orbital-proposal-rotation.json'
old_report=json.loads(old_report_path.read_text())
geometry_path=ROOT/'benchmark/local/nib-v5i-orbital-geometry.npz'
old_proposal_path=ROOT/'benchmark/local/nib-v5i-orbital-proposal-rotation.npz'
if sha(geometry_path)!=old_report['cacheSha256'] or sha(old_proposal_path)!=old_report['proposalCacheSha256']:
    raise RuntimeError('Actual orbital construction provenance differs')
with np.load(geometry_path) as data:cache={k:data[k] for k in data.files}
with np.load(old_proposal_path) as data:
    basis=data['neutral'].astype(np.float32).astype(np.float64)
cache['basis']=basis
neutral=basis.copy();topology={'eyes':{}}
eyes={}
def projected_vertical_bounds(xs,vertices,triangles):
    """Exact piecewise-linear X/Z silhouette of the actual ocular triangles."""
    q=np.asarray(vertices,float)[triangles]
    a=q[:,[0,1,2]].reshape(-1,3);b=q[:,[1,2,0]].reshape(-1,3)
    dx=b[:,0]-a[:,0];nonvertical=abs(dx)>1e-14;denom=np.where(nonvertical,dx,1.)
    result=[]
    for x in xs:
        t=(x-a[:,0])/denom
        hit=nonvertical&(t>=-1e-9)&(t<=1+1e-9)
        z=a[:,2]+t*(b[:,2]-a[:,2])
        result.append([float(z[hit].min()),float(z[hit].max())] if hit.any() else [np.nan,np.nan])
    return np.asarray(result)
for side,region in [('R',9),('L',10)]:
    ring=np.asarray(old_report['eyes'][side]['ring'],np.int32)
    topology['eyes'][side]={'candidateRingVertexIds':ring.tolist()}
    upper,lower=split_arcs(ring,basis)
    domain=OrbitalDomain(cache['source'],cache['faces'],cache['faceSets'],cache['edges'],region,ring)
    x=basis[ring,0];t=(x-x.min())/(x.max()-x.min())
    arch=np.maximum(0,np.sin(np.pi*t))**1.2
    # Provisional +2.3/-1.0 mm arc lift increases height without moving eye
    # centers or turning the canthi into circular baby-eye openings.
    upper_mask=np.isin(ring,upper)
    delta=np.zeros((len(ring),3))
    delta[:,2]=np.where(upper_mask,.0023,-.0010)*arch
    vertices,triangles=eye_surface(cache,side)
    bounds=projected_vertical_bounds(basis[ring,0],vertices,triangles)
    requested=delta[:,2].copy()
    available=np.where(upper_mask,bounds[:,1]-basis[ring,2],basis[ring,2]-bounds[:,0])-.00025
    supported=np.isfinite(available)&(available>0)
    # A smooth bounded response fades the lift where the actual globe becomes
    # shallow near a canthus. It does not expand the eye or silently permit the
    # previously failed off-shell targets. Fixed corner deltas remain zero.
    delta[:,2]=0
    delta[supported,2]=np.sign(requested[supported])*available[supported]*np.tanh(abs(requested[supported])/available[supported])
    proposed=basis[ring]+delta
    shell=front_surface_y(proposed[:,[0,2]],vertices,triangles)
    original_shell=front_surface_y(basis[ring][:,[0,2]],vertices,triangles)
    if np.any(np.isfinite(original_shell)&~np.isfinite(shell)):
        raise RuntimeError('Proposed aperture leaves the actual eye-shell projection')
    valid=np.isfinite(shell)
    delta[valid,1]=np.minimum(0,shell[valid]-.00020-basis[ring[valid],1])
    correction,solve=domain.solve(delta)
    neutral+=correction
    eyes[side]={'maximumUpperLiftMeters':.0023,'maximumLowerDropMeters':.0010,
                'actualMaximumUpperLiftMeters':float(delta[upper_mask,2].max()),
                'actualMaximumLowerDropMeters':float(-delta[~upper_mask,2].min()),
                'ocularSilhouetteBoundedRimIds':ring[abs(delta[:,2]-requested)>.00005].tolist(),
                'minimumOcularSilhouetteClearanceMeters':.00025,
                'solve':solve,'maximumDeltaMeters':float(np.linalg.norm(correction,axis=1).max()),
                'canthusMaximumDeltaMeters':float(np.linalg.norm(correction[[upper[0],upper[-1]]],axis=1).max())}
cache['basis']=neutral
neutral,shapes,closure=propose(cache,topology,rotation_preservation=True)
faces=cache['faces'];tri=np.vstack((faces[:,[0,1,2]],faces[:,[0,2,3]]));edges=cache['edges']
def normals(p):
    q=p[tri];return np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
old_normals=normals(basis);old_area=np.linalg.norm(old_normals,axis=1)
old_edges=np.linalg.norm(basis[edges[:,1]]-basis[edges[:,0]],axis=1)
def metrics(p):
    n=normals(p);area=np.linalg.norm(n,axis=1)
    dot=np.sum(n*old_normals,axis=1)/np.maximum(area*old_area,1e-20)
    return {'maximumDisplacementMeters':float(np.linalg.norm(p-basis,axis=1).max()),
            'introducedDegenerates':int(((area<1e-14)&(old_area>=1e-14)).sum()),
            'trianglesRotatedOver90':int((dot<0).sum()),
            'minimumAreaRatio':float((area/np.maximum(old_area,1e-20)).min()),
            'maximumEdgeStretch':float((np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)/np.maximum(old_edges,1e-12)).max())}
poses={}
for name in ['Blink','Squint']:
    for value in [.25,.5,.75,1.]:
        poses[name+'_'+str(value)]=metrics(neutral+value*(shapes[name+'_L']+shapes[name+'_R']))
nasal=np.unique(faces[cache['faceSets']==11])
nasal_delta=float(np.linalg.norm(neutral[nasal]-basis[nasal],axis=1).max())
if nasal_delta>1e-12:raise RuntimeError('Identity aperture moved nasal anchors')
for side in ['L','R']:
    upper=np.asarray(closure['eyes'][side]['upperArc']);lower=np.asarray(closure['eyes'][side]['lowerArc'])
    x=np.linspace(neutral[upper,0].min(),neutral[upper,0].max(),201)
    opening=np.interp(x,neutral[upper,0],neutral[upper,2])-np.interp(x,neutral[lower,0],neutral[lower,2])
    eyes[side]['widthMeters']=float(x[-1]-x[0]);eyes[side]['maximumApertureMeters']=float(opening.max())
    eyes[side]['widthToHeight']=float((x[-1]-x[0])/opening.max())
neutral_metric=metrics(neutral)
hard_fail=neutral_metric['introducedDegenerates']>0 or neutral_metric['trianglesRotatedOver90']>0 or any(p['introducedDegenerates'] for p in poses.values())
report={'status':'Numerical proposal only; no Blender source or actual render yet',
        'eyes':eyes,'neutral':neutral_metric,'poses':poses,'closure':closure,
        'nasalMaximumDeltaMeters':nasal_delta,'hardStructuralFailure':hard_fail,
        'fullBlinkNormalWarningsRetained':poses['Blink_1.0']['trianglesRotatedOver90'],
        'inputGeometrySha256':sha(geometry_path),'inputNeutralSha256':sha(old_proposal_path),
        'inputReportSha256':sha(old_report_path),'artisticAcceptance':False,'sharedChanged':False,
        'sourceDimensionsAreProvisional':True,
        'codeSha256':{p.name:sha(p) for p in [Path(__file__),HERE.parent/'v5_wip/orbital_closure_v5i.py']}}
args.output_cache.parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(args.output_cache,expectedBasis=basis.astype(np.float32),neutral=neutral,**shapes)
report['proposalCacheSha256']=sha(args.output_cache)
args.output_report.parent.mkdir(parents=True,exist_ok=True)
args.output_report.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'eyes':eyes,'neutral':neutral_metric,'fullBlink':poses['Blink_1.0'],'hardStructuralFailure':hard_fail}))
if hard_fail:raise RuntimeError('Identity proposal fails structural numerical gate; evidence preserved')
print('NIB_ORBITAL_IDENTITY_NUMERICAL_PROPOSAL_COMPLETE',flush=True)
