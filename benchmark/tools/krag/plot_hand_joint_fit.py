"""Diagnostic projection of retained source mesh and current source-space joints.
This is a topology plot, not a Blender render or revised character asset.
"""
import sys
import numpy as np,OpenImageIO as oiio
from pathlib import Path
root=Path(__file__).resolve().parents[3];d=root/'benchmark/art/krag/anatomy-study'
a=np.load(d/'GEO-body_male_realistic.npz',allow_pickle=True);v=a['vertices'];polys=a['polygons']
mask=(v[:,0]>.32)&(v[:,2]<.905)&(v[:,2]>.69)
joints={
'0':[(.401,-.050,.805),(.423,-.063,.765),(.424,-.063,.729)],
'1':[(.401,-.091,.812),(.426,-.105,.756),(.427,-.111,.719)],
'2':[(.400,-.121,.809),(.430,-.134,.757),(.432,-.142,.720)],
'3':[(.396,-.148,.813),(.421,-.160,.778),(.419,-.165,.744)],
'T':[(.373,-.110,.867),(.380,-.157,.839),(.389,-.174,.819)]}
if '--proposed' in sys.argv:
 from krag_hand_domains import SOURCE_JOINTS
 joints=SOURCE_JOINTS
W,H=850,1000;rgb=np.full((H,W,3),.96,np.float32)
def project(p):return np.array(((p[1]+.205)*4600+50,(.925-p[2])*4000+45))
def line(a,b,color,width=1):
 a=project(a);b=project(b);steps=int(np.linalg.norm(b-a)*2)+1
 for t in np.linspace(0,1,steps):
  x,y=np.rint(a*(1-t)+b*t).astype(int)
  rgb[max(0,y-width):min(H,y+width+1),max(0,x-width):min(W,x+width+1)]=color
for p in polys:
 for i,j in zip(p,np.roll(p,-1)):
  if mask[i] and mask[j]:line(v[i],v[j],(.65,.69,.73))
for k,chain in joints.items():
 for a,b in zip(chain,chain[1:]):line(a,b,(.1,.3,.9),2)
 for i,p in enumerate(chain):
  x,y=np.rint(project(p)).astype(int);yy,xx=np.ogrid[-6:7,-6:7];circle=xx*xx+yy*yy<=36
  rgb[y-6:y+7,x-6:x+7][circle]=[(.85,.1,.12),(.1,.65,.1),(.9,.5,.1)][i]
out=d/('Source_Hand_Proposed_Joints.png' if '--proposed' in sys.argv else 'Source_Hand_Current_Joints.png');img=oiio.ImageOutput.create(str(out));img.open(str(out),oiio.ImageSpec(W,H,3,oiio.UINT8));img.write_image((np.clip(rgb,0,1)*255).astype(np.uint8));img.close()
print(out)
