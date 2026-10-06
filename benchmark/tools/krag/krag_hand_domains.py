"""Provisional finger/palm domains from original CC0 hand connectivity.

Fields are solved before the creature warp. Distal fingers are identified as
separate connected components, so nearby neighboring digits cannot exchange
influence through empty space. Preserve these point fields through subdivision.
This is prepared source work and requires a real posed contact review.
"""
import numpy as np
ATTRIBUTES=['Krag_DigitDomain_'+str(i)+'_v3' for i in range(5)]

# Source-space joint proposals from actual mesh cross-sections and the retained
# hand wireframe. MCP centers are inside the palm; the old thumb endpoint was
# outside its distal skin. This is not a claim of final skeletal placement.
SOURCE_JOINTS={
    'Finger_0':[(.4028,-.0620,.805),(.4184,-.0637,.765),(.4245,-.0627,.729)],
    'Finger_1':[(.4100,-.0877,.812),(.4300,-.0992,.756),(.4260,-.1119,.719)],
    'Finger_2':[(.4095,-.1071,.809),(.4311,-.1277,.757),(.4318,-.1423,.720)],
    'Finger_3':[(.4050,-.1322,.813),(.4203,-.1520,.778),(.4189,-.1656,.744)],
    'Thumb':[(.3715,-.1130,.851),(.3691,-.1500,.8272),(.3695,-.1730,.8099)]}

def solve(vertices,polygons):
    p=np.asarray(vertices,dtype=float);edges=set()
    for face in polygons:
        face=list(face)
        for a,b in zip(face,face[1:]+face[:1]):
            if a!=b:edges.add(tuple(sorted((int(a),int(b)))))
    adjacent=[set() for _ in p]
    for a,b in edges:adjacent[a].add(b);adjacent[b].add(a)
    def components(ids):
        unseen=set(map(int,ids));parts=[]
        while unseen:
            seed=unseen.pop();part={seed};queue=[seed]
            while queue:
                a=queue.pop();near=adjacent[a]&unseen;unseen-=near;part|=near;queue.extend(near)
            parts.append(sorted(part))
        return parts
    result=np.zeros((len(p),5));records=[]
    for sign in [1,-1]:
        mask=(sign*p[:,0]>.32)&(p[:,2]<.92)&(p[:,2]>.69)
        ids=np.flatnonzero(mask);index={old:i for i,old in enumerate(ids)};q=p[ids]
        localedges=np.asarray([(index[a],index[b]) for a,b in edges if a in index and b in index],dtype=int)
        a=np.concatenate((localedges[:,0],localedges[:,1]));b=np.concatenate((localedges[:,1],localedges[:,0]))
        conductance=1/np.maximum(np.linalg.norm(q[a]-q[b],axis=1),.001)
        denominator=np.bincount(a,weights=conductance,minlength=len(q))
        fingers=components(np.flatnonzero(mask&(p[:,2]<.765)))
        if len(fingers)!=4:raise AssertionError('Expected four separate distal finger components')
        fingers.sort(key=lambda part:-float(p[part,1].mean()))
        thumb=components(np.flatnonzero(mask&(p[:,2]<.82)&(sign*p[:,0]<.386)&(p[:,1]<-.145)))
        if len(thumb)!=1:raise AssertionError('Expected one connected distal thumb component')
        fields=np.zeros((len(q),6));fields[:,5]=1
        pinned=q[:,2]>.835
        counts=[]
        for digit,part in enumerate(fingers+[thumb[0]]):
            local=np.asarray([index[i] for i in part]);fields[local]=0;fields[local,digit]=1;pinned[local]=True;counts.append(len(local))
        for iteration in range(2500):
            update=np.column_stack([np.bincount(a,weights=conductance*fields[b,k],minlength=len(q))/np.maximum(denominator,1e-12) for k in range(6)])
            update[pinned]=fields[pinned];error=float(np.max(abs(update-fields)));fields=update
            if error<1e-9:break
        if error>=1e-9:raise AssertionError('Finger-domain field did not converge')
        if not np.isfinite(fields).all() or fields.min()<-1e-8 or np.max(abs(fields.sum(1)-1))>1e-7:raise AssertionError('Invalid finger partition')
        result[ids]=fields[:,:5]
        records.append({'side':'L' if sign>0 else 'R','sourceVertices':len(ids),'seedCounts':counts,'palmSeedCount':int(np.sum(q[:,2]>.835)),'iterations':iteration+1,'residual':error,'maxPartitionError':float(np.max(abs(fields.sum(1)-1)))})
    return result,{'status':'Prepared topology domain; actual fingertip contact and palm deformation unverified','hands':records}

def attach(mesh,fields):
    for i,name in enumerate(ATTRIBUTES):
        attribute=mesh.attributes.get(name) or mesh.attributes.new(name,'FLOAT','POINT')
        attribute.data.foreach_set('value',np.asarray(fields[:,i],dtype=np.float32))

def read(mesh):
    result=np.empty((len(mesh.vertices),5),dtype=np.float32)
    for i,name in enumerate(ATTRIBUTES):
        values=np.empty(len(mesh.vertices),dtype=np.float32)
        mesh.attributes[name].data.foreach_get('value',values);result[:,i]=values
    return result
