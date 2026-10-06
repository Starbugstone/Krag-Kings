"""Actual saved-surface handle locations; no Blender or geometry modification."""
from pathlib import Path
import numpy as np,json
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'benchmark/art/krag/landmarks-v9nc'
p=np.load(OUT/'actual-neutral-surface.npz');v=p['Head_world'];pix=np.load(OUT/'TrueFront-head-pixels.npy');member=p['Head_membership'];tri=p['Head_triangles']
# Manually identified anatomical sites in the actual 1000px true-front proof.
# The numerical coordinate is a pick, not an approved design dimension.
handles={'glabella':(500,437),'brow_inner':(559,440),'brow_crest':(635,423),'brow_tail':(701,446),'forehead_above_crest':(635,366),'upper_cheek_crest':(727,550),'malar_plane':(711,604),'nasolabial_upper':(623,593),'nasolabial_lower':(655,656),'alar_base':(602,577),'nasal_bridge':(500,509),'nasal_tip':(500,562),'philtrum':(500,637),'upper_vermilion':(500,684),'mouth_corner':(645,710),'lower_vermilion':(500,720),'labiomental_fold':(500,757),'chin_front':(500,811),'mandibular_angle':(721,744)}
result={}
for name,xy in handles.items():
 # Exact orthographic ray/triangle intersection avoids selecting hidden oral
 # bag vertices merely because their projection is closer to the click.
 projected=pix[tri];a=projected[:,0];b=projected[:,1]-a;c=projected[:,2]-a;q=np.asarray(xy)-a
 det=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=abs(det)>1e-10
 u=np.divide(q[:,0]*c[:,1]-q[:,1]*c[:,0],det,out=np.zeros_like(det),where=valid)
 w=np.divide(b[:,0]*q[:,1]-b[:,1]*q[:,0],det,out=np.zeros_like(det),where=valid)
 hit=np.flatnonzero(valid&(u>=-1e-9)&(w>=-1e-9)&(u+w<=1+1e-9))
 if not len(hit):raise RuntimeError('Handle ray misses actual mesh: '+name)
 bary=np.column_stack((1-u[hit]-w[hit],u[hit],w[hit]));pts=np.einsum('ij,ijk->ik',bary,v[tri[hit]])
 nearest=int(np.argmin(pts[:,1]));face=int(hit[nearest]);center=pts[nearest];i=int(tri[face,np.argmax(bary[nearest])])
 eyes=np.asarray([[.0587531254,-.1197548732,1.9154560566],[-.0587532856,-.1195666492,1.9154570103]])
 radii=np.asarray([.0205106222,.0205403139]);t=np.clip((np.linalg.norm(center-eyes,axis=1)-(radii+.0005))/.026,0,1);smooth=t*t*t*(10+t*(-15+6*t));weight=max(0,1-(1-smooth).sum())
 result[name]={'pickedPixel':xy,'triangle':face,'triangleVertices':tri[face].tolist(),'barycentric':bary[nearest].tolist(),'world':center.tolist(),'v9ncOpticalFieldRemainingFraction':float(weight),'sourceFaceSet':int(p['Head_triangle_sets'][face])}
print(json.dumps(result,indent=2));(OUT/'measured-handles.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
