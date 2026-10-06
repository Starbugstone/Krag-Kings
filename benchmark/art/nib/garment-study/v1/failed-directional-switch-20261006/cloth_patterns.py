"""Prepared fabric patterns against the actual anatomical Nib cage.

These are ungenerated construction proposals. Keep the concept sleeveless
underlayer, bib/straps, compressed draped scarf and visible lean arms. Physical
settling and actual posed review are required before any appearance claim.
"""
from collections import Counter,defaultdict
import numpy as np


def smooth(a,b,x):
    t=np.clip((np.asarray(x)-a)/(b-a),0,1);return t*t*(3-2*t)


def boundary_loops(faces):
    uses=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
    graph=defaultdict(list)
    for (a,b),count in uses.items():
        if count>2:raise RuntimeError('Nonmanifold authored garment surface')
        if count==1:graph[a].append(b);graph[b].append(a)
    if any(len(v)!=2 for v in graph.values()):raise RuntimeError('Open/branched garment boundary')
    unseen=set(graph);loops=[]
    while unseen:
        start=min(unseen);previous=None;current=start;loop=[]
        while current in unseen:
            loop.append(current);unseen.remove(current)
            choices=[v for v in graph[current] if v!=previous]
            following=choices[0];previous,current=current,following
        if current!=start:raise RuntimeError('Garment boundary does not close')
        loops.append(loop)
    return loops


def undershirt(cage_points,cage_faces,arm_domain):
    """Open four-boundary torso pattern: neck, waist and two arm openings."""
    p=np.asarray(cage_points,dtype=np.float64);arm=np.asarray(arm_domain)
    keep=(p[:,2]>=.665)&(p[:,2]<=.991)&(arm<.24)
    chosen=[list(map(int,f)) for f in cage_faces if all(keep[i] for i in f)]
    used=np.asarray(sorted({i for f in chosen for i in f}),dtype=np.int32);lookup={old:i for i,old in enumerate(used)}
    faces=[[lookup[i] for i in f] for f in chosen];points=p[used].copy()
    loops=boundary_loops(faces)
    if len(loops)!=4:raise RuntimeError('Undershirt must have exactly neck/waist/two arm openings')
    # Relax only the ragged selection boundary; physical fitting then projects
    # it onto actual skin + clearance instead of keeping a staircase cut edge.
    for _ in range(10):
        old=points.copy()
        for loop in loops:
            ids=np.asarray(loop);points[ids]=old[ids]*.60+(old[np.roll(ids,1)]+old[np.roll(ids,-1)])*.20
    shoulder=smooth(.921,.962,points[:,2])*(1-smooth(.102,.142,abs(points[:,0])))
    neck=sorted(loops,key=lambda loop:-float(points[loop,2].mean()))[0]
    shoulder[neck]=np.maximum(shoulder[neck],.90)
    return {'points':points,'faces':faces,'sourceVertexIds':used,'armDomain':arm[used],
        'pins':shoulder,'loops':loops,'status':'Unrelaxed topology-derived cloth pattern; actual solver/contact review required'}


def scarf():
    """One continuous overlapping wrap, with free front and tucked rear edge.

    Unlike the superseded three independent annular collars, this is one open
    sheet with diagonal bias and variable sag. Dimensions are fitting proposals.
    """
    along=240;across=19;points=[];faces=[];uv=[];pins=[]
    for i in range(along):
        u=i/(along-1);turn=2.45*u;angle=.18*np.pi+turn*np.pi*2
        front=max(0,-np.sin(angle));back=max(0,np.sin(angle))
        for j in range(across):
            v=j/(across-1)
            rx=.050+.0032*turn+.018*v
            ry=.058+.005*turn+.023*v+.008*front
            fold=.0018*np.sin(angle*2.5+v*4.8)+.0011*np.sin(angle*5.3-v*7)
            x=rx*np.cos(angle)+.002*np.sin(angle*2+.4)
            y=.008+(ry+fold)*np.sin(angle)
            z=1.039-.011*turn-.052*v-front*(.016+.017*v)+.004*np.cos(angle*2+.6)
            z+=fold*np.sin(v*np.pi)
            points.append((x,y,z));uv.append((turn*.35,v*.10))
            nape=back**5*(1-float(smooth(.05,.30,v)))
            tucked=float(smooth(.92,1,u))*(1-float(smooth(.0,.38,v)))
            pins.append(max(nape*.94,tucked))
    for i in range(along-1):
        for j in range(across-1):
            a=i*across+j;faces.append([a,a+1,a+across+1,a+across])
    return {'points':np.asarray(points),'faces':faces,'uv':np.asarray(uv),'pins':np.asarray(pins),
        'status':'Continuous initial wrapped textile; not settled or visually accepted'}
