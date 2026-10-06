"""Experimental landmark warp of CC0 animation topology toward the Nib sheet.

This remains a clay study. It does not update the approved reference, current
master, rig or shared files. Proportions are review proposals, not new canon.
"""
import json, math
from pathlib import Path
import numpy as np

def gaussian(x,c,w):return np.exp(-((x-c)/w)**2)

def fit_head(source):
    x,y,z=source.T
    front=np.clip((-y-.005)/.065,0,1)
    target_z=np.interp(z,[.02,.13,.18,.222,.234,.268,.310,.337,.436],
                         [.930,1.024,1.064,1.102,1.110,1.138,1.165,1.190,1.260])
    width=np.interp(z,[.02,.13,.18,.222,.268,.31,.337,.38,.436],[.50,.66,.72,.98,1.13,1.09,1.03,.86,.80])
    target_x=x*width
    target_y=y*.60+.026
    # The human nostril/upper-lip loops become a compact feline nose and broad
    # muzzle. Preserve their topology and depth, instead of overlaying primitives.
    muzzle=gaussian(x,0,.052)*gaussian(z,.230,.031)*front
    target_y-=.022*muzzle
    lips=gaussian(x,0,.041)*gaussian(z,.232,.014)*front
    target_x*=1+.30*lips
    target_z-=(z-.232)*.18*lips
    nose=gaussian(x,0,.030)*gaussian(z,.267,.025)*front
    target_x*=1-.34*nose
    target_y-=.020*nose
    target_y+=.008*gaussian(x,0,.020)*gaussian(z,.294,.016)*front
    # Taper the mental pad rather than retaining the source's square human chin.
    target_y+=.009*gaussian(x,0,.043)*gaussian(z,.190,.023)*front
    # A wider cheek shelf and restrained hollow carry the reference's adult read.
    cheek=gaussian(abs(x),.055,.024)*gaussian(z,.277,.033)*front
    target_x+=np.sign(x)*.008*cheek
    target_y-=.004*cheek
    # Keep the eyes in their continuous orbital skin; alter the entire orbital
    # region together so lids and the reference eyeballs retain contact.
    eyes=gaussian(abs(x),.035876,.026)*gaussian(z,.310037,.022)*front
    target_x+=np.sign(x)*(abs(x)-.035876)*.04*eyes
    target_z+=(abs(x)-.035876)*.14*eyes
    target_z-=(z-.310037)*.22*eyes
    brow=gaussian(abs(x),.032,.028)*gaussian(z,.333,.012)*front
    target_y-=.003*brow
    target_z-=.004*gaussian(abs(x),.018,.018)*brow
    # Collapse human ear relief into the lateral skull. The existing two large
    # fennec auricles remain the only visible ears when this study is integrated.
    # Tiny unilateral mouth-corner lift is the reference's closed-mouth smirk.
    target_z+=.002*gaussian(x,.032,.016)*gaussian(z,.232,.015)*front
    return np.column_stack((target_x,target_y,target_z))

def remove_human_ears(original,fitted,faces):
    """Discard human auricles and rebuild lateral skull patches for the study.

    Native integration will use the precise asset face sets if available. These
    spatial study selections must not become an unreviewed production boolean.
    """
    from study_head import boundaries
    x,y,z=original.T
    mask=(abs(x)>.060)&(y>-.055)&(y<.057)&(z>.235)&(z<.350)
    faces=[p for p in faces if not np.any(mask[p])]
    groups=boundaries(fitted,faces);vertices=fitted.tolist()
    edges={}
    for p in faces:
        for a,b in zip(p,p[1:]+p[:1]):
            edge=tuple(sorted((a,b)));edges.setdefault(edge,[]).append((a,b))
    for group in groups:
        if abs(group['mean'][0])<.045 or group['mean'][2]<1.10:continue
        members=set(group['indices'])
        oriented=[uses[0] for pair,uses in edges.items() if len(uses)==1 and pair[0] in members and pair[1] in members]
        successor={a:b for a,b in oriented}
        if len(successor)!=len(oriented):raise RuntimeError('Study ear boundary is not a single manifold loop')
        loop=[oriented[0][0]]
        while successor[loop[-1]]!=loop[0]:
            loop.append(successor[loop[-1]])
            if len(loop)>len(oriented):raise RuntimeError('Study ear boundary traversal failed')
        center=np.mean(fitted[loop],axis=0);center[0]=math.copysign(.064,center[0])
        inner=[]
        for index in loop:
            point=fitted[index]*.55+center*.45
            inner.append(len(vertices));vertices.append(point.tolist())
        middle=len(vertices);vertices.append(center.tolist())
        for i,a in enumerate(loop):
            j=(i+1)%len(loop);b=loop[j]
            # Existing boundary order is reversed on the new patch.
            faces.append([b,a,inner[i],inner[j]])
            faces.append([inner[j],inner[i],middle])
    return np.asarray(vertices),faces

if __name__=='__main__':
    from study_head import load_reference, render, OUT
    verts,faces=load_reference();fitted=fit_head(verts)
    fitted,faces=remove_human_ears(verts,fitted,faces)
    # Cut below the final neck seam for a readable head-only study. Production
    # integration must bridge/weld the seam into the existing united anatomy.
    keep=[p for p in faces if min(fitted[p,2])>1.045]
    used=sorted({i for p in keep for i in p});index={old:new for new,old in enumerate(used)}
    keptverts=fitted[used];keptfaces=[[index[i] for i in p] for p in keep]
    for label,angle in [('Front',0),('Side',math.pi/2),('Perspective',.55)]:
        render(keptverts,keptfaces,OUT/('Nib_HeadWarp_'+label+'.png'),angle)
    data={'status':'Experimental CC0-derived clay study; unrigged and unaccepted. No production outputs updated.',
          'sourceObject':'GEO-head_animation_realistic','license':'CC0 per bundle README',
          'vertices':keptverts.tolist(),'faces':keptfaces,'sourceIndices':used}
    (OUT/'head-warp-study.json').write_text(json.dumps(data,indent=2))
    print('Unaccepted facial landmark study written; production assets unchanged.')
