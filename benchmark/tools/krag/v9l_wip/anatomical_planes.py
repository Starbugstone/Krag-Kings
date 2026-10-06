"""Provisional continuous orbital/cheek/mandibular sculpt after profile repair.

Works in final source metres. Pins actual optical apertures and oral boundaries,
not entire orbital face sets (which also contain most of the brow surface).
"""
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'v9i_wip'))
from face_relief import boundary_fade


def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)


def refine(raw,points,tags,edges):
    raw=np.asarray(raw,dtype=float);points=np.asarray(points,dtype=float)
    x,y,z=raw.T;member=lambda i:(tags&(np.uint64(1)<<np.uint64(i)))!=0
    external=np.logical_or.reduce([member(i)for i in [33,24,11,5,6,9,10]])&~member(7)
    margin=boundary_fade(raw,edges,external,.004)
    front=smooth((-y-.084)/.031)*margin
    g=lambda v,c,w:np.exp(-((v-c)/w)**2)
    # The exposed ocular opening stays fitted to its globe. Surrounding orbital
    # skin remains available for a low overhanging ridge, rather than being
    # accidentally excluded wholesale by its anatomical face-set label.
    optical_radius=np.sqrt(((abs(x)-.0358764)/.021)**2+((z-.3100375)/.011)**2)
    optical_guard=smooth((optical_radius-.88)/.65)
    d=np.zeros_like(points)
    line=.310+.60*abs(x)
    hood=g(abs(x),.036,.027)*g(z,line,.022)*front*optical_guard
    hood_plane=-.168+.20*(abs(points[:,0])-.04)+.40*(points[:,2]-1.935)
    d[:,1]+=np.clip(hood_plane-points[:,1],-.035,.008)*hood
    d[:,2]-=.0030*hood*g(abs(x),.022,.025)
    bridge=g(x,0,.015)*g(z,.333,.029)*front*optical_guard
    d[:,1]+=np.clip(-.155-points[:,1],-.025,.010)*bridge
    # Two independent glabellar furrows interrupt the joined orbital bridge.
    for sign in [-1,1]:
        center=sign*(.009+.045*(z-.342));support=g(z,.351,.026)*front
        d[:,1]+=.0060*g(x,center,.0022)*support
        d[:,1]-=.0028*g(x,center+sign*.004,.0042)*support
    # Broad zygomatic plane and lower cheek recess, connected through the
    # original loops. This gives a bony cheek transition instead of a sphere.
    cheek=g(abs(x),.055,.023)*g(z,.282,.027)*front*optical_guard
    cheek_plane=-.145+.33*(abs(points[:,0])-.09)-.30*(points[:,2]-1.887)
    d[:,1]+=.80*np.clip(cheek_plane-points[:,1],-.021,.012)*cheek
    hollow=g(abs(x),.060,.023)*g(z,.244,.021)*front
    d[:,1]+=.010*hollow
    # Alar folds start outside the actual wide nasal ala and pass lateral to
    # the real commissures. Old .019-source-X grooves fell inside the nose.
    t=np.clip((.273-z)/.043,0,1);fold=.028+.003*t
    support=g(z,.252,.026)*front
    d[:,1]+=.0065*g(abs(x),fold,.0028)*support
    d[:,1]-=.0035*g(abs(x),fold+.0048,.0045)*support
    # A broad rounded mandible remains within the projecting muzzle envelope;
    # no narrow chin spike is reintroduced.
    chin=np.exp(-(x/.048)**4)*g(z,.203,.029)*front
    chin_plane=-.180+.20*abs(points[:,0])
    d[:,1]+=.80*np.clip(chin_plane-points[:,1],-.020,.010)*chin
    # Shaped lower-lip/chin crease, clear of the exact mouth boundary.
    d[:,1]+=.0028*g(z,.210+.018*abs(x),.0024)*g(x,0,.036)*front
    # Physical protection is also applied to all subsequent fold fields.
    d*=optical_guard[:,None]
    magnitude=np.linalg.norm(d,axis=1)
    if magnitude.max()>.045 or not np.isfinite(d).all():raise RuntimeError('Unbounded facial-plane study')
    return d,{'status':'Prepared source geometry; actual neutral/profile/blink likeness review mandatory',
              'maxDisplacementMeters':float(magnitude.max()),'orbitalSetsRetainedForSculpt':[5,6,9,10],
              'oralRimPinned':True,'opticalOpeningProtected':True,
              'changedVertices':int(np.count_nonzero(magnitude>1e-6))}
