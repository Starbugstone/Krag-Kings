"""Evaluate the actual route code through all rows using saved mesh caches.

No Blender process, mesh authoring, cloth rerun or shared writes. The exact
build() prefix through its curvature gate is extracted from the recipe AST.
"""
import ast,copy,hashlib,json,math,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
class Vector(np.ndarray):
    def __new__(cls,value):return np.asarray(value,dtype=np.float64).view(cls)
    x=property(lambda self:float(self[0]));y=property(lambda self:float(self[1]));z=property(lambda self:float(self[2]))
class Surface:
    def __init__(self,p,f):
        self.points=np.asarray(p,dtype=np.float64);self.tri=np.asarray(f,dtype=np.int32);q=self.points[self.tri]
        self.q=q;self.e1=q[:,1]-q[:,0];self.e2=q[:,2]-q[:,0];normal=np.cross(self.e1,self.e2);length=np.linalg.norm(normal,axis=1)
        self.valid=length>1e-12;self.normal=normal/np.maximum(length[:,None],1e-30)
    def ray_cast(self,origin,axis,limit):
        h=np.cross(np.broadcast_to(axis,self.e2.shape),self.e2);det=np.sum(self.e1*h,1);ok=self.valid&(abs(det)>1e-12);inv=np.zeros_like(det);inv[ok]=1/det[ok]
        s=origin-self.q[:,0];u=inv*np.sum(s*h,1);q=np.cross(s,self.e1);v=inv*np.sum(axis*q,1);t=inv*np.sum(self.e2*q,1)
        ok&=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(t>=0)&(t<=limit);t[~ok]=np.inf;i=int(t.argmin())
        if not np.isfinite(t[i]):return None,None,None,None
        return Vector(origin+axis*t[i]),Vector(self.normal[i]),i,float(t[i])
    def find_nearest(self,point):
        a,b,c=self.q[:,0],self.q[:,1],self.q[:,2];h=np.sum((point-a)*self.normal,1);best=point-h[:,None]*self.normal
        v0=self.e1;v1=self.e2;v2=best-a;d00=np.sum(v0*v0,1);d01=np.sum(v0*v1,1);d11=np.sum(v1*v1,1);d20=np.sum(v2*v0,1);d21=np.sum(v2*v1,1);den=d00*d11-d01*d01
        v=(d11*d20-d01*d21)/np.maximum(den,1e-30);w=(d00*d21-d01*d20)/np.maximum(den,1e-30);inside=self.valid&(v>=0)&(w>=0)&(v+w<=1);dist=np.sum((best-point)**2,1);dist[~inside]=np.inf
        for x,y in [(a,b),(b,c),(c,a)]:
            edge=y-x;t=np.clip(np.sum((point-x)*edge,1)/np.maximum(np.sum(edge*edge,1),1e-30),0,1);hit=x+t[:,None]*edge;d2=np.sum((hit-point)**2,1);m=(d2<dist)&self.valid;best[m]=hit[m];dist[m]=d2[m]
        i=int(dist.argmin());return Vector(best[i]),Vector(self.normal[i]),i,float(np.sqrt(dist[i]))
def json_mesh(name):
    path=ROOT/'benchmark/local'/name;d=json.loads(path.read_text());assert d['sourceSha256']=='b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da'
    f=[(p[0],p[i],p[i+1]) for p in d['polygons'] for i in range(1,len(p)-1)]
    return Surface(d['vertices'],f),path
body,bp=json_mesh('nib-actual-v5-body.json');belt,be=json_mesh('nib-actual-v5-belt.json')
sp=ROOT/'benchmark/local/nib-fitted-shirt-support-v2.npz';d=np.load(sp)
assert str(d['source_sha256'])=='b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da'
assert str(d['cloth_patterns_sha256'])==hashlib.sha256((HERE/'sewn_undershirt_v2.py').read_bytes()).hexdigest()
shirt=Surface(d['points'],d['triangles']);surfaces={'body':body,'belt':belt,'shirt':shirt}
source=HERE/'shoulder_straps_v2.py';module=ast.parse(source.read_text());smooth=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='smooth_curve');build=copy.deepcopy(next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='build'))
stop=next(i for i,n in enumerate(build.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='widths' for t in n.targets))
result=ast.parse("return {'rows':routing,'maximumAngleDegrees':float(bend.max()),'maximumShirtLiftMeters':float(envelope.max()),'beltAnchor':anchor.tolist(),'endpointDeltaMeters':float(np.linalg.norm(end_delta)),'allSupportAndCurvatureGatesPass':True}").body[0]
build.body=build.body[:stop]+[result];compiled=ast.fix_missing_locations(ast.Module(body=[smooth,build],type_ignores=[]))
def tree(name):
    s=surfaces[name];return s,s.points,s.tri
env={'np':np,'math':math,'Path':Path,'json':json,'Vector':Vector,'tree':tree,'__file__':str(source)};exec(compile(compiled,str(source),'exec'),env)
report={'status':'Exact route prefix tested on actual saved Body/Belt and actual settled shirt cache; no native source saved','sourceSha256':'b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da','recipeSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'auditCodeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'caches':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [bp,be,sp]},'sides':{},'nativeValidation':False,'artisticAcceptance':False,'sharedChanged':False}
try:
    for side in [-1,1]:report['sides'][str(side)]=env['build']('audit',side,None,None,None,'body','shirt','belt')
    report['allPreparedGatesPass']=True
except Exception as exc:
    report['allPreparedGatesPass']=False;report['failure']=str(exc)
out=ROOT/'benchmark/art/nib/garment-study/strap-v2-all-support-preparation.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'pass':report['allPreparedGatesPass'],'failure':report.get('failure'),'sides':{k:{n:v for n,v in d.items() if n!='rows'} for k,d in report['sides'].items()}}))
if not report['allPreparedGatesPass']:raise SystemExit(2)
