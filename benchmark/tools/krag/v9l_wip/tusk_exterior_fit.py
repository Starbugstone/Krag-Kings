"""Fit exposed crown geometry against actual exterior lip/muzzle surfaces.

The buried gingival roots remain fixed. This is a bounded source correction,
not proof of posed contact, final oral anatomy or concept acceptance.
"""
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'v9j_wip'));import dental_arch


def apply(head,face):
    mesh=face.data;keys=mesh.shape_keys.key_blocks;basis=np.asarray([tuple(v.co)for v in keys['Basis'].data]);delta=np.zeros_like(basis)
    ivory={i for p in mesh.polygons if mesh.materials[p.material_index].name=='Krag_TuskEnamel_Source'for i in p.vertices}
    parts=[part for part in dental_arch.components(mesh)if int(part[0])in ivory]
    if len(parts)!=2 or any(len(p)!=408 for p in parts):raise RuntimeError('Expected the actual v9le17-ring tusks')
    xform=face.matrix_world.inverted()@head.matrix_world;points=[xform@v.co for v in head.data.shape_keys.key_blocks['Basis'].data]
    sets=head.data.attributes['.sculpt_face_set'];polygons=[p for p in head.data.polygons if sets.data[p.index].value not in [7,5,6]]
    tree=BVHTree.FromPolygons(points,[tuple(p.vertices)for p in polygons]);report=[]
    for part in parts:
        rings=part.reshape(17,24);centers=basis[rings].mean(1);required=np.zeros(17);hits=[]
        expected=np.asarray((np.sign(centers[0,0])*.04102049023,-.15700653195,1.80372047424))
        if np.linalg.norm(centers[0]-expected)>.00001:raise RuntimeError('Actual tusk ring indexing does not start at the preserved gingival root')
        for row in range(8,17):
            for index in rings[row]:
                p=basis[index];surface,normal,face_id,distance=tree.ray_cast(Vector((p[0],-.65,p[2])),Vector((0,1,0)),1.2)
                if surface is None:continue
                tag=int(sets.data[polygons[face_id].index].value)
                need=float(p[1]-surface.y+.0008)
                if need>required[row]:required[row]=need
                hits.append({'ring':row,'headRegion':tag,'requiredForwardMeters':max(0,need)})
        # Smooth only the exposed displacement, retaining its exact clearance
        # inequalities. A quintic transition leaves root rows0..3 unchanged.
        shift=required.copy()
        for _ in range(12):
            smoothed=shift.copy();smoothed[8:16]=.25*shift[7:15]+.5*shift[8:16]+.25*shift[9:17]
            shift[8:]=np.maximum(required[8:],smoothed[8:])
        for row in range(4,8):
            t=(row-3)/5;fade=t*t*t*(10+t*(-15+6*t));shift[row]=shift[8]*fade
        if shift.max()>.045:raise RuntimeError('Exposed tusk requires more than45mm exterior fit; dental/soft-tissue correction required: '+str({'maximumMeters':float(shift.max()),'requiredByRingMeters':required.tolist()}))
        for row,indices in enumerate(rings):delta[indices,1]-=shift[row]
        after=basis+delta;minimum=1.
        for row in range(8,17):
            for index in rings[row]:
                p=after[index];surface,normal,face_id,distance=tree.ray_cast(Vector((p[0],-.65,p[2])),Vector((0,1,0)),1.2)
                if surface is not None:minimum=min(minimum,float(surface.y-p[1]))
        if minimum<.000799:raise RuntimeError('Exposed tusk clearance invariant failed')
        if np.any(delta[rings[:4]]):raise RuntimeError('Gingival root moved during crown fit')
        report.append({'side':'L'if centers[0,0]>0 else'R','rootCenterUnchanged':centers[0].tolist(),'requiredForwardByRingMeters':required.tolist(),'appliedForwardByRingMeters':shift.tolist(),'maximumForwardCorrectionMeters':float(shift.max()),'minimumFrontSurfaceGapMeters':minimum,'surfaceRegionIds':sorted(set(h['headRegion']for h in hits)),
                       'archReviewFlag':bool(shift.max()>.025)})
    untouched=np.ones(len(basis),dtype=bool);untouched[list(ivory)]=False
    for key in keys:
        original=np.asarray([tuple(v.co)for v in key.data]);key.data.foreach_set('co',(original+delta).astype(np.float32).ravel())
        actual=np.asarray([tuple(v.co)for v in key.data])
        if not np.array_equal(actual[untouched],original[untouched]):raise RuntimeError('Crown fit moved unrelated ocular coordinates')
    mesh.vertices.foreach_set('co',(basis+delta).astype(np.float32).ravel());mesh.update()
    return {'status':'Actual crown-to-exterior source fit; neutral/open profile review required','gingivalRootsFixed':True,'unrelatedOcularShapesExact':True,'sides':report,'pending':['True eruption appearance and posed lip clearance','Dental-arch setback and visible gum/tongue depth','Normal mouth and concept likeness']}
