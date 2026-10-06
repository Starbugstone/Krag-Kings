"""Prepared topology-aware Krag jaw correction on audited library face loops.

Shared algorithm: tools/nib/v5_wip/mouth_jaw_weights.py. Krag proportions and
acting are unchanged; this only separates cranial upper lip from mandible.
Actual saved-source weights and open-mouth/blink views remain required.
"""
from pathlib import Path
import importlib.util,hashlib,json
import numpy as np


def shared_solver():
    path=Path(__file__).resolve().parents[2]/'nib/v5_wip/mouth_jaw_weights.py'
    spec=importlib.util.spec_from_file_location('krag_shared_semantic_jaw_solver',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,path


def apply(modules):
    o=modules['Head'];mesh=o.data
    source_attr=mesh.attributes.get('krag_reference_position')
    sets_attr=mesh.attributes.get('.sculpt_face_set')
    if source_attr is None or sets_attr is None:
        raise RuntimeError('Krag Jaw repair requires retained anatomical source positions and face sets')
    source=np.empty(len(mesh.vertices)*3,dtype=np.float32)
    source_attr.data.foreach_get('vector',source);source=source.reshape(-1,3)
    faces=[tuple(p.vertices) for p in mesh.polygons]
    sets=np.asarray([p.value for p in sets_attr.data],dtype=np.int32)
    edges=np.asarray([tuple(edge.vertices) for edge in mesh.edges],dtype=np.int32)
    if len(sets)!=len(faces):raise RuntimeError('Krag face-set/face correspondence is invalid')
    neck=np.zeros(len(source));old_jaw=np.zeros(len(source))
    neck_group=o.vertex_groups.get('Neck');jaw_group=o.vertex_groups.get('Jaw')
    if neck_group is None or jaw_group is None:raise RuntimeError('Expected existing Krag Jaw/Neck groups')
    for vertex in mesh.vertices:
        for group in vertex.groups:
            if group.group==neck_group.index:neck[vertex.index]=group.weight
            elif group.group==jaw_group.index:old_jaw[vertex.index]=group.weight
    solver,path=shared_solver()
    weights,statistics=solver.calculate(source,faces,sets,edges,neck)
    head=o.vertex_groups.get('Head')
    if head is None:raise RuntimeError('Missing Krag cranial group')
    for i,value in enumerate(weights):
        jaw_group.add([i],float(value),'REPLACE')
        head.add([i],float(1-neck[i]-value),'REPLACE')
    actual_sums=np.zeros(len(source));stored_jaw=np.zeros(len(source))
    for vertex in mesh.vertices:
        for group in vertex.groups:
            if group.group in {head.index,neck_group.index,jaw_group.index}:actual_sums[vertex.index]+=group.weight
            if group.group==jaw_group.index:stored_jaw[vertex.index]=group.weight
    if np.max(np.abs(actual_sums-1))>1e-6:
        raise RuntimeError('Stored Jaw repair weight partition not normalized')
    if np.max(np.abs(stored_jaw-weights))>1e-6:
        raise RuntimeError('Stored Jaw weights differ from solved field')
    statistics['maximumStoredWeightSumError']=float(np.max(np.abs(actual_sums-1)))
    statistics.update({'character':'Krag','status':'Topology-aware source weight patch; actual pose acceptance pending',
        'solverPath':'benchmark/tools/nib/v5_wip/mouth_jaw_weights.py',
        'solverSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'adapterSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'maximumJawWeightChange':float(np.max(np.abs(weights-old_jaw))),
        'changedVertices':int(np.count_nonzero(np.abs(weights-old_jaw)>1e-7)),
        'geometryChanged':False,'shapeKeysChanged':False,'actingChanged':False})
    o['krag_semantic_jaw_repair']=json.dumps(statistics)
    return statistics
