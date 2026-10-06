"""Provisional topology-aware torso/arm domain on the unwarped CC0 cage.

This field belongs to source anatomy, not the widened character's X coordinate.
It must travel as a POINT attribute through subdivision and modular partitioning.
No production source uses it until the explicit integration option is enabled.
"""
import numpy as np

ATTRIBUTE='Krag_ArmDomain_v2'

def solve(vertices,polygons):
    p=np.asarray(vertices,dtype=np.float64);x=np.abs(p[:,0]);z=p[:,2]
    pairs=set()
    for face in polygons:
        face=list(face)
        for a,b in zip(face,face[1:]+face[:1]):
            if a!=b:pairs.add(tuple(sorted((int(a),int(b)))))
    edges=np.asarray(sorted(pairs),dtype=np.int32)
    a=np.concatenate([edges[:,0],edges[:,1]]);b=np.concatenate([edges[:,1],edges[:,0]])
    conductance=1/np.maximum(np.linalg.norm(p[a]-p[b],axis=1),.001)
    denominator=np.bincount(a,weights=conductance,minlength=len(p))
    # Fixed body-side seeds include broad lower ribs/waist. Arm seeds are
    # farther along actual source upper arms, forearms and hands, not Krag X.
    torso=(x<.115)|((z<1.245)&(x<.207))|((z>1.445)&(x<.145))
    arm=(x>.255)&(z>.690)&(z<1.420)
    if np.any(torso&arm):raise AssertionError('Conflicting anatomical seeds')
    pinned=torso|arm;field=np.full(len(p),.5);field[torso]=0;field[arm]=1
    error=1.
    for iteration in range(1600):
        values=np.bincount(a,weights=conductance*field[b],minlength=len(p))/np.maximum(denominator,1e-12)
        values[pinned]=field[pinned];error=float(np.max(np.abs(values-field)));field=values
        if error<1e-8:break
    if not np.isfinite(field).all() or field.min()<-1e-8 or field.max()>1+1e-8:raise AssertionError('Invalid domain field')
    return field,{'iterations':iteration+1,'maxIterationDelta':error,'converged':error<1e-8,
        'torsoSeedVertices':int(torso.sum()),'armSeedVertices':int(arm.sum()),
        'vertices':len(p),'undirectedEdges':len(edges),'status':'Anatomical weighting proposal; actual raised-arm deformation review required'}

def attach(mesh,values):
    attribute=mesh.attributes.get(ATTRIBUTE) or mesh.attributes.new(ATTRIBUTE,'FLOAT','POINT')
    attribute.data.foreach_set('value',np.asarray(values,dtype=np.float32))

def read(mesh):
    values=np.empty(len(mesh.vertices),dtype=np.float32)
    mesh.attributes[ATTRIBUTE].data.foreach_get('value',values)
    return values
