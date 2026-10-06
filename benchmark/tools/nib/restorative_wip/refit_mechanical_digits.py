"""Prepared restorative finger rest-fit after the explicit left-digit migration.

Maps the existing rigid metal segments onto the new anatomical bind. Joint
radii/materials/UVs remain; only each segment's length follows ordinary finger
reach. No skeleton edits, added performance or upgrade functionality.
"""
import hashlib,json
import numpy as np
from mathutils import Matrix


def refit(rig, collection, root):
    reference = root/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/groom-source.json'
    original = json.loads(reference.read_text())['preservedRigAndActions']['bones']
    old_matrices = {n: Matrix(v['matrix']) for n,v in original.items()}
    before = {b.name: [list(r) for r in b.matrix_local] for b in rig.data.bones}
    chains = {}
    for j, finger in enumerate(['Index','Middle','Ring','Little']):
        fx = .227+(j-1.5)*.012
        z = .563-(.008 if j in [0,3] else 0)
        chains[finger] = [(fx,-.046,z+.01),(fx+.004,-.049,z-.011),
                         (fx+.003,-.060,z-.028),(fx,-.070,z-.032)]
    chains['Thumb'] = [(.206,-.042,.594),(.193,-.055,.581),(.190,-.066,.565)]
    old_lengths = {}
    for finger, points in chains.items():
        for index in range(len(points)-1):
            name = finger+str(index+1)+'_L'
            if np.linalg.norm(np.asarray(old_matrices[name].translation)-points[index]) > 2e-7:
                raise RuntimeError('Recorded mechanical chain differs from actual old rest bone '+name)
            end = np.asarray(points[index+1],float)
            axis = np.asarray(old_matrices[name].col[1][:3],float)
            length = float((end-np.asarray(points[index]))@axis)
            if length <= 0 or np.linalg.norm(end-np.asarray(points[index])-axis*length) > 2e-7:
                raise RuntimeError('Original mechanical segment does not follow recorded rest axis')
            old_lengths[name] = length
    parts = [o for o in collection.objects if o.type=='MESH' and o.get('variant')=='grip']
    segments = [o for o in parts if o.name.startswith('Articulated replacement finger')]
    hinges = [o for o in parts if o.name.startswith('Replacement finger hinge')]
    thumbs = [o for o in parts if o.name.startswith('Restorative thumb')]
    if len(segments)!=12 or len(hinges)!=12 or len(thumbs)!=2:
        raise RuntimeError('Unexpected authored mechanical hand component count')
    if {o.get('bone') for o in segments} != {f+str(i)+'_L' for f in ['Index','Middle','Ring','Little'] for i in [1,2,3]}:
        raise RuntimeError('Mechanical digit tags do not match twelve original segments')
    # Original thumbs were rigid Hand_L. Resolve their actual geometric center
    # to the two audited source segments, rather than trust object name suffixes.
    thumb_map = {}
    for obj in thumbs:
        world = np.asarray([tuple(rig.matrix_world.inverted()@obj.matrix_world@v.co) for v in obj.data.vertices])
        centers = [(np.asarray(chains['Thumb'][i])+chains['Thumb'][i+1])*.5 for i in range(2)]
        distances = [float(np.linalg.norm(world.mean(0)-p)) for p in centers]
        index = int(np.argmin(distances))
        if distances[index] > 2e-6 or index in thumb_map:
            raise RuntimeError('Original thumb segment identity is ambiguous')
        thumb_map[index] = obj
    assignments = [(o,o['bone'],False) for o in segments]+[(o,o['bone'],True) for o in hinges]
    assignments += [(thumb_map[i],'Thumb'+str(i+1)+'_L',False) for i in range(2)]
    records = []
    for obj, name, hinge in assignments:
        if obj.data.has_custom_normals:
            raise RuntimeError('Explicit normal transform required for '+obj.name)
        old = old_matrices[name]
        new = rig.data.bones[name].matrix_local.copy()
        new_length = float(rig.data.bones[name].length)
        scale = 1. if hinge else new_length/old_lengths[name]
        old_to_new = new@Matrix.Diagonal((1.,scale,1.,1.))@old.inverted()
        obj_to_rig = rig.matrix_world.inverted()@obj.matrix_world
        local = obj_to_rig.inverted()@old_to_new@obj_to_rig
        coords = np.asarray([tuple(obj_to_rig@v.co) for v in obj.data.vertices])
        axial = (coords-np.asarray(old.translation))@np.asarray(old.col[1][:3])
        if hinge:
            if np.linalg.norm(coords.mean(0)-np.asarray(old.translation)) > 2e-6:
                raise RuntimeError('Mechanical hinge is not centered on recorded old joint')
        elif abs(float(axial.min()))>2e-6 or abs(float(axial.max())-old_lengths[name])>2e-6:
            raise RuntimeError('Mechanical segment cap does not match recorded old joint pair')
        mesh_input = np.asarray([v.co[:] for v in obj.data.vertices],np.float32)
        key_inputs = {key.name:np.asarray([v.co[:] for v in key.data],np.float32)
                      for key in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {}
        old_hash = hashlib.sha256(mesh_input.tobytes()).hexdigest()
        if obj.data.users>1:
            obj.data = obj.data.copy()
        transform = np.asarray(local,dtype=np.float64)
        def mapped(points):
            return (points@transform[:3,:3].T+transform[:3,3]).astype(np.float32)
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                key.data.foreach_set('co',mapped(key_inputs[key.name]).ravel())
        obj.data.vertices.foreach_set('co',mapped(mesh_input).ravel())
        obj.data.update()
        obj.vertex_groups.clear()
        group = obj.vertex_groups.new(name=name)
        group.add(list(range(len(obj.data.vertices))),1.,'REPLACE')
        obj['bone'] = name
        obj['restorative_rest_refit'] = 'Original metal segment mapped to anatomical digit bind; rigid one-bone LBS'
        new_coords = np.asarray([tuple(obj_to_rig@v.co) for v in obj.data.vertices])
        new_axis = np.asarray(new.col[1][:3])
        new_axial = (new_coords-np.asarray(new.translation))@new_axis
        cap_error = None if hinge else max(abs(float(new_axial.min())),abs(float(new_axial.max())-new_length))
        center_error = float(np.linalg.norm(new_coords.mean(0)-np.asarray(new.translation))) if hinge else None
        if (cap_error is not None and cap_error>3e-7) or (center_error is not None and center_error>3e-7):
            raise RuntimeError('Refitted actual segment/joint endpoints differ')
        records.append({'object':obj.name,'bone':name,'hinge':hinge,
                        'oldLengthMeters':old_lengths[name],'newLengthMeters':new_length,
                        'lengthScale':scale,'capErrorMeters':cap_error,'hingeCenterErrorMeters':center_error,
                        'inputLocalVertexSha256':old_hash,
                        'outputLocalVertexSha256':hashlib.sha256(np.asarray([v.co[:] for v in obj.data.vertices],np.float32).tobytes()).hexdigest()})
    if before != {b.name:[list(r) for r in b.matrix_local] for b in rig.data.bones}:
        raise RuntimeError('Mechanical geometry refit changed rig bind')
    return [o for o,_,_ in assignments], {'oldRestContract':str(reference),
            'oldRestContractSha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'parts':records,'palmAndWristHousingUnchanged':True,
            'pending':['Actual knuckle/palm emergence and ordinary hand envelope',
                       'Actual neutral, curled and Shoot gap/contact review',
                       'Cuff/forearm twist compatibility'], 'artisticAcceptance':False}
