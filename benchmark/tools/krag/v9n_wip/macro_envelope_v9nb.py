"""Prepared broad facial-envelope deformation, in shared world coordinates.

The same smooth field acts on facial skin, oral geometry and control pivots.
Small moving ocular neighborhoods retain sphere/lid contact; these neighborhoods
translate with the field instead of pinning the old facial envelope in place.
Actual profile and expression renders determine whether this improves likeness.
"""
import numpy as np


def smooth(v):
    t=np.clip(v,0.,1.);return t*t*t*(10+t*(-15+6*t))


class Envelope:
    def __init__(self,eye_centers,eye_radii,lip_center,nose_center):
        self.eyes=np.asarray(eye_centers,dtype=float)
        self.radii=np.asarray(eye_radii,dtype=float)
        self.lip=np.asarray(lip_center,dtype=float)
        self.nose=np.asarray(nose_center,dtype=float)
        self.eye=self.eyes.mean(0)
        if not .005<self.radii.min()<=self.radii.max()<.040:
            raise RuntimeError('Actual globe bounds do not support a small optical neighborhood')
        if not .035<self.eye[2]-self.lip[2]<.125:
            raise RuntimeError('Measured eye/oral landmarks are outside the reviewed Krag proportions')
        self.eye_moves=self.base_delta(self.eyes)

    def base_delta(self,points):
        p=np.asarray(points,dtype=float).reshape(-1,3);x,y,z=p.T
        ax=np.sqrt(x*x+.008**2);odd=np.tanh(x/.022)
        eyz=self.eye[2];lipz=self.lip[2];nz=self.nose[2]
        g=lambda v,c,w:np.exp(-((v-c)/w)**2)
        front=smooth((self.eye[1]+.095-y)/.095)
        neck=smooth((z-(lipz-.108))/.074)
        crown=smooth(((eyz+.142)-z)/.052)
        support=front*neck*crown
        out=np.zeros_like(p)
        # Distributed nasal/upper-muzzle recession compresses the current long
        # profile. These wide fields cannot end at a material or face-set edge.
        nose=g(z,nz,.043)*np.exp(-(x/.073)**4)
        muzzle=g(z,lipz+.014,.039)*np.exp(-(x/.079)**4)
        out[:,1]+=.029*nose+.007*muzzle
        # A broad mental/mandibular front, rather than a narrow chin spike.
        chin=g(z,lipz-.044,.038)*np.exp(-(x/.081)**4)
        out[:,1]-=.017*chin;out[:,2]-=.0025*chin
        angle=g(ax,.061,.034)*g(z,lipz-.032,.047)
        out[:,0]+=.0055*odd*angle
        # Sloped, paired supraorbital mass is carried into the forehead.
        bx=abs(self.eyes[0,0]);sloped_z=eyz+.024+.10*(ax-bx)
        paired=g(x,bx,.043)+g(x,-bx,.043)
        brow=g(z,sloped_z,.040)*np.minimum(paired,1.)
        out[:,1]-=.0085*brow;out[:,2]-=.0015*brow
        bridge=g(x,0,.029)*g(z,eyz+.008,.036)
        out[:,1]-=.0030*bridge
        # Carry volume above the hood into the frontal bone. The existing
        # point itself is not pushed out into another thin visor.
        forehead=g(z,eyz+.060,.045)*np.exp(-(x/.112)**4)
        out[:,1]-=.0100*forehead
        malar=g(ax,.078,.028)*g(z,eyz-.047,.050)
        out[:,1]+=.0040*malar
        # Preserve a broad fleshy alar mass while shortening its profile.
        out[:,0]+=.0030*odd*g(ax,.027,.022)*g(z,nz,.035)
        return out*support[:,None]

    def delta(self,points):
        p=np.asarray(points,dtype=float).reshape(-1,3);d=self.base_delta(p)
        weights=[]
        for center,radius in zip(self.eyes,self.radii):
            # Exact sphere/lid-contact region plus a continuous surrounding
            # blend, not an immovable mask across the nose/brow envelope.
            inner=radius+.0015;outer=inner+.050
            distance=np.linalg.norm(p-center,axis=1)
            weights.append(1-smooth((distance-inner)/(outer-inner)))
        w=np.stack(weights,axis=1);total=w.sum(1);denom=np.maximum(total,1.)
        return d*(1-np.minimum(total,1))[:,None]+w@self.eye_moves/denom[:,None]

    def transform(self,points):
        p=np.asarray(points,dtype=float).reshape(-1,3)
        return p+self.delta(p)

    def jacobian_report(self,points):
        p=np.asarray(points,dtype=float);step=.00001;columns=[]
        for axis in range(3):
            offset=np.zeros(3);offset[axis]=step
            columns.append((self.transform(p+offset)-self.transform(p-offset))/(2*step))
        j=np.stack(columns,axis=2);det=np.linalg.det(j);sv=np.linalg.svd(j,compute_uv=False)
        if det.min()<=.20 or sv.min()<=.20 or sv.max()>2.2:
            raise RuntimeError('Broad envelope folds/collapses space or exceeds bounded scale: '+str({'minDet':float(det.min()),'minScale':float(sv.min()),'maxScale':float(sv.max()),'maxScalePointMeters':p[np.argmax(sv[:,0])].tolist(),'minScalePointMeters':p[np.argmin(sv[:,-1])].tolist()}))
        return {'minimumJacobianDeterminant':float(det.min()),'minimumLocalScale':float(sv.min()),'maximumLocalScale':float(sv.max()),'sampleCount':len(p)}


def surface_report(before,after,triangles):
    tri=np.asarray(triangles,dtype=int);old=before[tri];new=after[tri]
    a=np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0]);b=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0])
    aa=np.linalg.norm(a,axis=1);bb=np.linalg.norm(b,axis=1);valid=aa>1e-12
    cosine=np.einsum('ij,ij->i',a[valid],b[valid])/np.maximum(aa[valid]*bb[valid],1e-30)
    ratio=bb[valid]/aa[valid];angles=np.degrees(np.arccos(np.clip(cosine,-1,1)))
    if cosine.min()<=0 or ratio.min()<.20:raise RuntimeError('Macro envelope flips/collapses an actual Head triangle')
    return {'flippedTriangles':int(np.count_nonzero(cosine<=0)),'minimumTriangleAreaRatio':float(ratio.min()),
            'normalChangeDegreesP99':float(np.quantile(angles,.99)),'normalChangeDegreesMaximum':float(angles.max()),
            'preexistingDegenerateTriangles':int(np.count_nonzero(~valid)),'maxDisplacementMeters':float(np.linalg.norm(after-before,axis=1).max())}
