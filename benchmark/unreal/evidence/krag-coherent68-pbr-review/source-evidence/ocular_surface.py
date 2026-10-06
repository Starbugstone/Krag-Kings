"""Actual ocular-coordinate pigment/limbus and coated curved corneal surface.

No flattened eye card or unrelated tiled image. Source point attributes must
be baked on the actual Face UV atlas for a later runtime export.
"""
import bpy,numpy as np,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'v9j_wip'))
import krag_iris_material,dental_arch


def apply(face):
    mesh=face.data;attribute=mesh.attributes.get('krag_reference_position')
    if attribute is None:raise RuntimeError('Original fitted ocular coordinates missing')
    raw=np.empty(len(mesh.vertices)*3,dtype=np.float32);attribute.data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
    amber={v for p in mesh.polygons if mesh.materials[p.material_index].name=='Krag_Amber'for v in p.vertices}
    coords=np.zeros_like(raw);mask=np.zeros(len(raw),dtype=np.float32);count=0;details=[]
    for part in dental_arch.components(mesh):
        if not any(int(i)in amber for i in part):continue
        source=raw[part];sign=1 if source[:,0].mean()>0 else-1
        center=np.asarray((sign*.0358765,-.1153812,.3100375));planar=source[:,[0,2]]-center[[0,2]]
        radius=float(np.quantile(np.linalg.norm(planar,axis=1),.99))
        if not .004<radius<.009:raise RuntimeError('Invalid retained iris extent')
        coords[part,:2]=planar/radius;mask[part]=1;count+=1
        details.append({'side':'L'if sign>0 else'R','points':len(part),'sourceRadiusMeters':radius})
    if count!=2:raise RuntimeError('Expected exactly two continuous iris surfaces')
    for name,kind,values,field in [('Krag_IrisCoord','FLOAT_VECTOR',coords,'vector'),('Krag_IrisMask','FLOAT',mask,'value')]:
        a=mesh.attributes.get(name)or mesh.attributes.new(name,kind,'POINT');a.data.foreach_set(field,values.ravel())
    iris=bpy.data.materials['Krag_Amber'];krag_iris_material.configure(iris)
    for material_name in ['Krag_Amber','Krag_EyeWhite']:
        material=bpy.data.materials[material_name];bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.20
        bs.inputs['Coat Weight'].default_value=1;bs.inputs['Coat Roughness'].default_value=.065;bs.inputs['Coat IOR'].default_value=1.376
        material['ocularRepresentation']='Existing fitted curved shell and iris, radial pigment/limbus, wet corneal coat; no new transparency dependency'
    return {'status':'Actual source material fields; runtime atlas/coat integration pending','irisSurfaces':details,
            'radialReliefMeters':.000018,'coatRoughness':.065,'coatIOR':1.376,'geometryUnchanged':True,
            'runtimeRequirement':'Bake actual Face UV atlas; preserve ocular wet-coat response explicitly in engine materials'}
