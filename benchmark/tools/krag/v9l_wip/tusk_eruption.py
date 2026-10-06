"""Provisional curved tusks fitted to actual gingiva and the true lower lip.

Replace the old three-ring wedges while retaining every unrelated ocular vertex,
shape coordinate and bone weight. Actual neutral/open profile review is required.
"""
from pathlib import Path
import sys,math
import numpy as np
import bpy,bmesh
from mathutils import Vector
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'v9j_wip'));import dental_arch


def ring_curve(root,emergence,tip,count=17):
    # One quadratic passes exactly through the true emergence at t=.5.
    control=2*emergence-.5*(root+tip);rows=[];t_values=np.linspace(0,1,count)
    radii=np.interp(t_values,[0,.25,.50,.75,.92,1],[.0046,.0045,.0039,.0026,.0012,.00035])
    for t,radius in zip(t_values,radii):
        center=(1-t)**2*root+2*t*(1-t)*control+t*t*tip
        tangent=2*(1-t)*(control-root)+2*t*(tip-control);tangent/=np.linalg.norm(tangent)
        axis=np.asarray((1.,0.,0.));axis-=tangent*np.dot(axis,tangent);axis/=np.linalg.norm(axis);other=np.cross(tangent,axis)
        row=[center+radius*(axis*math.cos(a)+other*math.sin(a))for a in np.linspace(0,2*math.pi,24,endpoint=False)]
        rows.append(row)
    return np.asarray(rows)


def apply(head,face,oral,root_targets):
    mesh=face.data;basis=np.asarray([tuple(v.co)for v in mesh.shape_keys.key_blocks['Basis'].data]);old_keys={k.name:np.asarray([tuple(v.co)for v in k.data])for k in mesh.shape_keys.key_blocks}
    ivory={v for p in mesh.polygons if mesh.materials[p.material_index].name=='Krag_Ivory'for v in p.vertices}
    parts=[part for part in dental_arch.components(mesh)if int(part[0])in ivory]
    if len(parts)!=2 or any(len(p)!=48 for p in parts):raise RuntimeError('Expected two reviewed three-ring tusks')
    tags=np.zeros(len(head.data.vertices),dtype=np.uint64);sets=head.data.attributes['.sculpt_face_set']
    for polygon in head.data.polygons:tags[list(polygon.vertices)]|=np.uint64(1)<<np.uint64(sets.data[polygon.index].value)
    lower=((tags&(np.uint64(1)<<np.uint64(24)))!=0)&((tags&(np.uint64(1)<<np.uint64(7)))!=0)
    lip=np.asarray([tuple(face.matrix_world.inverted()@head.matrix_world@v.co)for v in head.data.shape_keys.key_blocks['Basis'].data])[lower]
    if len(lip)<20:raise RuntimeError('True lower lip rim missing')
    lip=lip[np.argsort(lip[:,0])];specs=[]
    for part in parts:
        rings=part.reshape(3,16);centers=basis[rings].mean(1);tip=centers[np.argmax(centers[:,2])].copy();side='L'if tip[0]>0 else'R'
        root=np.asarray(face.matrix_world.inverted()@oral.matrix_world@Vector(root_targets[side]),dtype=float)
        # Preserve the actual lower dental arch root; fit the passage through
        # the source rim at that canine X instead of attaching to cheek skin.
        lip_site=np.asarray([root[0],np.interp(root[0],lip[:,0],lip[:,1]),np.interp(root[0],lip[:,0],lip[:,2])])
        emergence=lip_site+np.asarray((0,.0015,-.001))
        if not root[2]<lip_site[2]+.004:raise RuntimeError('Lower gingival root lies above the true lip; oral arch needs refitting before tusk construction')
        if not .012<tip[2]-lip_site[2]<.050:raise RuntimeError('Reviewed tusk tip has implausible exposure relative to actual lip')
        points=ring_curve(root,emergence,tip)
        specs.append({'side':side,'oldVertices':part,'root':root,'lip':lip_site,'emergence':emergence,'tip':tip,'rows':points})
    material=bpy.data.materials.get('Krag_TuskEnamel_Source')
    if material is None:
        material=bpy.data.materials['Krag_Ivory'].copy();material.name='Krag_TuskEnamel_Source'
        for node in material.node_tree.nodes:
            if node.type=='BUMP':node.inputs['Distance'].default_value=.000035;node.inputs['Strength'].default_value=.22
            elif node.type=='BSDF_PRINCIPLED':node.inputs['Roughness'].default_value=.27
    slot=len(mesh.materials);mesh.materials.append(material)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();marker=bm.verts.layers.int.new('krag_tusk_retained_vertex')
    for vertex in bm.verts:vertex[marker]=vertex.index+1
    shape_names=set(bm.verts.layers.shape.keys());shape_layers=[bm.verts.layers.shape[name]for name in shape_names]
    if not (set(old_keys)-{'Basis'}).issubset(shape_names):raise RuntimeError('BMesh did not retain every non-Basis facial shape layer')
    removed=set(int(i)for part in parts for i in part);bmesh.ops.delete(bm,geom=[bm.verts[i]for i in sorted(removed)],context='VERTS')
    uv=bm.loops.layers.uv.active;new_faces=[]
    if uv is None:raise RuntimeError('Face actual UV layer is absent')
    for spec in specs:
        rows=[]
        for row in spec['rows']:
            made=[]
            for point in row:
                v=bm.verts.new(point);v[marker]=0
                for layer in shape_layers:v[layer]=point
                made.append(v)
            rows.append(made)
        for i in range(len(rows)-1):
            for j in range(24):
                jj=(j+1)%24;face_new=bm.faces.new((rows[i][j],rows[i][jj],rows[i+1][jj],rows[i+1][j]));face_new.material_index=slot;face_new.smooth=True
                for loop,coord in zip(face_new.loops,[(j/24,i/16),((j+1)/24,i/16),((j+1)/24,(i+1)/16),(j/24,(i+1)/16)]):loop[uv].uv=coord
                new_faces.append(face_new)
        for row,reverse in [(rows[0],True),(rows[-1],False)]:
            cap=bm.faces.new(tuple(reversed(row))if reverse else tuple(row));cap.material_index=slot;new_faces.append(cap)
    bmesh.ops.recalc_face_normals(bm,faces=new_faces);bm.to_mesh(mesh);bm.free();mesh.update()
    attr=mesh.attributes['krag_tusk_retained_vertex'];mapping=np.asarray([v.value for v in attr.data],dtype=int)-1;keep=mapping>=0;new=np.flatnonzero(~keep)
    for key in mesh.shape_keys.key_blocks:
        coords=np.asarray([tuple(v.co)for v in key.data]);expected=old_keys[key.name][mapping[keep]]
        if not np.array_equal(coords[keep],expected):raise RuntimeError('Tusk construction moved unrelated ocular '+key.name+' coordinates')
    jaw=face.vertex_groups['Jaw']
    for group in face.vertex_groups:group.remove(new.tolist())
    jaw.add(new.tolist(),1.,'REPLACE')
    # Rigid tusks use only Jaw articulation, never live captured facial mixes.
    current=np.asarray([tuple(v.co)for v in mesh.shape_keys.key_blocks['Basis'].data])
    for key in mesh.shape_keys.key_blocks:
        coords=np.asarray([tuple(v.co)for v in key.data]);coords[new]=current[new];key.data.foreach_set('co',coords.astype(np.float32).ravel())
    report={'status':'Actual replacement tusks; neutral/open root/skin clearance still requires renders','removedThreeRingVertices':len(removed),'newCurvedTuskVertices':len(new),'unrelatedFacialShapeCoordinatesExact':True,'radialSegments':24,'axialRings':17,
      'sides':[{'side':s['side'],'gingivalRoot':s['root'].tolist(),'trueLowerLip':s['lip'].tolist(),'emergenceCenter':s['emergence'].tolist(),'retainedTip':s['tip'].tolist()}for s in specs]}
    return report
