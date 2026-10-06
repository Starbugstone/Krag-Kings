"""Equip an isolated exterior study on a COPY of the reviewed Krag master.

Retains original anatomy, weights, animation and the archived original weapon.
No engine export or shared promotion. Muzzle sockets derive from visible mesh.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--weapon',type=Path,required=True)
p.add_argument('--grip-report',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.output.exists():raise RuntimeError('Preserve existing study; use a fresh output')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source_hash=sha(a.source);weapon_hash=sha(a.weapon)
spec=json.loads(a.grip_report.read_text())['spec']
bpy.ops.wm.open_mainfile(filepath=str(a.source))
rig=bpy.data.objects['Krag_Rig'];original=bpy.data.objects['Weapon_R']
old_action=rig.animation_data.action;old_frame=bpy.context.scene.frame_current
rest_before={b.name:list(v for row in b.matrix_local for v in row) for b in rig.data.bones}
center=Vector(spec['center']);row=Vector(spec['rowAxis']).normalized()
forward=(Vector(spec['aim'])-Vector(spec['muzzle'])).normalized()
y_axis=-forward;x_axis=y_axis.cross(row).normalized()
if abs(x_axis.dot(row))>1e-5 or x_axis.dot(Vector(spec['palmNormal']))<.999:
    raise AssertionError('Grip basis does not match actual fitted hand')
basis=Matrix((x_axis,y_axis,row)).transposed()
if abs(basis.determinant()-1)>1e-5:raise AssertionError('Weapon basis must be proper rigid transform')
transform=Matrix.Translation(center)@basis.to_4x4()

with bpy.data.libraries.load(str(a.weapon),link=False) as (source,destination):
    destination.objects=list(source.objects)
parts=[]
for obj in destination.objects:
    if obj is None:continue
    if obj.type=='MESH' and obj.get('module')=='Weapon_R_Study':
        bpy.context.scene.collection.objects.link(obj);parts.append(obj)
    else:bpy.data.objects.remove(obj,do_unlink=True)
if len(parts)!=134:raise AssertionError('Unexpected frozen weapon-v2 inventory')
lip=next(obj for obj in parts if obj.name=='Muzzle worn lip')
front_y=min((lip.matrix_world@v.co).y for v in lip.data.vertices)
front_indices=[v.index for v in lip.data.vertices if abs((lip.matrix_world@v.co).y-front_y)<1e-6]
if len(front_indices)!=192:raise AssertionError('Inspect actual muzzle ring topology')
front=sum((lip.matrix_world@lip.data.vertices[i].co for i in front_indices),Vector())/len(front_indices)
attribute=lip.data.attributes.new('WeaponStudy_VisibleMuzzle','FLOAT','POINT')
for i in front_indices:attribute.data[i].value=1
for obj in parts:
    obj.matrix_world=transform@obj.matrix_world
    obj.vertex_groups.clear();obj.vertex_groups.new(name='Hand_R').add(list(range(len(obj.data.vertices))),1,'REPLACE')
    if not obj.data.uv_layers:raise AssertionError('Missing study UVs')
    obj.data.uv_layers.active.name='UVMap'
original.name='ARCHIVE pre-study Weapon_R';original['archived_module']='Weapon_R'
del original['module'];original.hide_render=True;original.hide_set(True)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
weapon=bpy.context.object;weapon.name='Weapon_R';weapon['module']='Weapon_R'
weapon['provisional_exterior_study']=True
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
weapon.parent=rig;modifier=weapon.modifiers.new('Rigid hand attachment','ARMATURE');modifier.object=rig
weapon.hide_render=False;weapon.hide_set(False)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
muzzle=rig.matrix_world.inverted()@(transform@front)
for name,head in [('WeaponMuzzle',muzzle),('WeaponAim',muzzle+forward*.10)]:
    bone=rig.data.edit_bones[name];bone.head=head;bone.tail=head+forward*.025
bpy.ops.object.mode_set(mode='OBJECT')
for bone in rig.data.bones:
    if bone.name in ('WeaponMuzzle','WeaponAim'):continue
    if rest_before[bone.name]!=list(v for matrix_row in bone.matrix_local for v in matrix_row):
        raise AssertionError('Unrelated bind bone changed: '+bone.name)
indices=[i for i,v in enumerate(weapon.data.attributes['WeaponStudy_VisibleMuzzle'].data) if v.value>.5]
samples=[]
for name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
    action=bpy.data.actions.get(name)
    if action is None:raise AssertionError('Missing original clip '+name)
    rig.animation_data.action=action
    for frame in [int(action.frame_range[0]),round(sum(action.frame_range)/2),int(action.frame_range[1])]:
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        evaluated=weapon.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        try:visible=sum((evaluated.matrix_world@mesh.vertices[i].co for i in indices),Vector())/len(indices)
        finally:evaluated.to_mesh_clear()
        socket=rig.matrix_world@rig.pose.bones['WeaponMuzzle'].head
        error=(visible-socket).length
        if error>1e-5:raise AssertionError('Visible muzzle/socket disagree')
        samples.append({'clip':name,'frame':frame,'visibleMuzzleErrorMeters':error})
rig.animation_data.action=old_action;bpy.context.scene.frame_set(old_frame)
bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
report={'status':'Actual equipped study; posed contact/render acceptance remains pending',
    'source':str(a.source),'sourceSha256':source_hash,'weapon':str(a.weapon),'weaponSha256':weapon_hash,
    'output':str(a.output),'outputSha256':sha(a.output),'gripReportSha256':sha(a.grip_report),
    'socketDerivation':'Actual visible front-lip mesh centroid, not the earlier study empty',
    'studyEmptyOffsetCorrectionMeters':abs(front_y+.567),'muzzleSourceLocalMeters':list(front),
    'rigidBasisDeterminant':basis.determinant(),'poseSamples':samples,'unchangedOtherBoneRestMatrices':True,
    'sharedAssetsChanged':False,'exported':False,'artisticAcceptance':False}
a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
if sha(a.source)!=source_hash or sha(a.weapon)!=weapon_hash:raise AssertionError('Input source changed')
print('KRAG_WEAPON_EQUIPPED_STUDY_COMPLETE',flush=True)
