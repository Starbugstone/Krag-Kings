"""Bounded socket surface from actual anatomical forearm cross-sections.

Pure NumPy preparation: normal-facing rays, recorded barycentric support and
explicit cut-loop coverage. No scene or rig mutation here.
"""
import math
import numpy as np

def design(points, faces, cut_ids, elbow, wrist, around=64, rows=13):
    points=np.asarray(points,float);elbow=np.asarray(elbow,float);wrist=np.asarray(wrist,float)
    axis=wrist-elbow;length=np.linalg.norm(axis);axis/=length
    across=np.cross(axis,[0,1,0]);across/=np.linalg.norm(across);other=np.cross(axis,across)
    cut_fraction=(points[np.asarray(cut_ids,int)]-elbow)@axis/length
    begin=.025;end=float(cut_fraction.max()+.035)
    if not .15<end<.24:raise RuntimeError('Actual skin boundary outside expected socket fitting interval')
    triangles=[];owners=[]
    for owner,f in enumerate(faces):
        f=list(map(int,f));q=points[f]
        if q[:,0].max()<.14 or q[:,2].max()<.715 or q[:,2].min()>.795:continue
        for i in range(1,len(f)-1):triangles.append((f[0],f[i],f[i+1]));owners.append(owner)
    triangles=np.asarray(triangles,int);q=points[triangles];a=q[:,0];e1=q[:,1]-a;e2=q[:,2]-a
    n=np.cross(e1,e2);area=np.linalg.norm(n,axis=1);valid_area=area>1e-12;n/=np.maximum(area[:,None],1e-20)
    vertices=[];supports=[];radii=[];normal_dots=[];fractions=[]
    for row in range(rows):
        fraction=begin+(end-begin)*row/(rows-1);center=elbow+axis*length*fraction
        for column in range(around):
            angle=math.tau*column/around;direction=across*math.cos(angle)+other*math.sin(angle)
            p=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.sum(e1*p,axis=1)
            good=valid_area&(abs(det)>1e-12);inverse=np.where(good,1/np.where(good,det,1),0)
            s=center-a;u=np.sum(s*p,axis=1)*inverse;cross=np.cross(s,e1);v=np.sum(cross*direction,axis=1)*inverse
            distance=np.sum(e2*cross,axis=1)*inverse
            good&=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(distance>.003)&(distance<.065)
            candidates=np.flatnonzero(good)
            if not len(candidates):raise RuntimeError('Actual forearm socket support ray misses: '+str((row,column,fraction)))
            i=int(candidates[np.argmin(distance[candidates])]);dot=float(n[i]@direction)
            if dot<.30:raise RuntimeError('Socket ray hits an inward/tangent surface: '+str((row,column,dot)))
            hit=center+direction*distance[i]
            vertices.append(hit);supports.append((triangles[i].tolist(),[float(1-u[i]-v[i]),float(u[i]),float(v[i])]))
            radii.append(float(distance[i]));normal_dots.append(dot);fractions.append(fraction)
    hits=np.asarray(vertices);fractions=np.asarray(fractions)
    directions=[]
    for i,hit in enumerate(hits):
        center=elbow+axis*length*fractions[i];d=hit-center;directions.append(d/np.linalg.norm(d))
    directions=np.asarray(directions)
    outer=hits+directions*.0033;inner=hits+directions*.0007
    result={'outer':outer,'inner':inner,'directions':directions,'supports':supports,
            'fractions':fractions,'axis':axis,'around':around,'rows':rows,
            'startCenter':elbow+axis*length*begin,'endCenter':elbow+axis*length*end}
    result['report']={'status':'Numerically fitted actual-skin socket; native pose review pending',
       'forearmAxisFraction':[begin,end],'skinCutFractionRange':[float(cut_fraction.min()),float(cut_fraction.max())],
       'minimumDistalCutCoverageMeters':float((end-cut_fraction.max())*length),
       'surfaceSamples':len(hits),'radiusRangeMeters':[min(radii),max(radii)],
       'minimumOutwardNormalDot':min(normal_dots),'innerClearanceMeters':.0007,
       'outerClearanceMeters':.0033,'nominalLeatherThicknessMeters':.0026}
    return result
