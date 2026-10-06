"""Small raw-cage field check; not a Blender render or accepted silhouette."""
from pathlib import Path
import ast,sys,json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[4];BASE=ROOT/'benchmark/tools/krag'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(Path(__file__).parent))
import profile_fit,krag_proportions_v9f
namespace={'np':np};tree=ast.parse((BASE/'krag_head_v9.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fit');exec(compile(ast.Module(body=[function],type_ignores=[]),'frozen-fit','exec'),namespace)
namespace_old={};exec((BASE/'v9g_wip/face_planes.py').read_text(),namespace_old)
raw=np.load(ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz',allow_pickle=True)['vertices'];x,y,z=raw.T;base=namespace['fit'](raw);old=namespace_old['refine'](raw,base);new=profile_fit.refine(raw,base)
def final(p):
 q=p.copy();q[:,0]*=.93;q[:,1]*=.94;q[:,2]=2.107+(q[:,2]-2.107)*.85
 return krag_proportions_v9f.transform(q)
old_final,new_final=final(old),final(new)
regions={'brow':(abs(x)>.012)&(abs(x)<.061)&(z>.322)&(z<.356)&(y<-.06),'glabella':(abs(x)<.018)&(z>.325)&(z<.375)&(y<-.065),'cheek':(abs(x)>.042)&(abs(x)<.079)&(z>.226)&(z<.290)&(y<-.045),'chin':(abs(x)<.052)&(z>.173)&(z<.209)&(y<-.06),'muzzle':(abs(x)<.040)&(z>.224)&(z<.269)&(y<-.10)}
front=np.clip((-y-.035)/.06,0,1)
r={'status':'Raw control-cage fitting measurements only; actual smooth source/profile required','preparedFitSha256':hashlib.sha256(Path(profile_fit.__file__).read_bytes()).hexdigest(),'regions':{}}
for name,mask in regions.items():
 r['regions'][name]={'vertices':int(mask.sum()),'oldAddedFieldFrontMaskRange':[float(front[mask].min()),float(front[mask].max())],'oldAddedFieldFrontMaskMean':float(front[mask].mean()),'oldAddedFieldMaxDeltaMeters':float(np.linalg.norm((old-base)[mask],axis=1).max()),'v9gRawCageMostForwardFinalY':float(old_final[mask,1].min()),'proposedRawCageMostForwardFinalY':float(new_final[mask,1].min()),'maxFinalChangeMeters':float(np.linalg.norm(new_final[mask]-old_final[mask],axis=1).max())}
print(json.dumps(r,indent=2));(ROOT/'benchmark/art/krag/anatomy-study/profile-field-proposal-v9h.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
