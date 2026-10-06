"""Read-only attribution of a failed source/FBX pose comparison."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector

directory=Path(sys.argv[sys.argv.index('--')+1])
receipt=json.loads((directory/'export.json').read_text())
fail=json.loads((directory/'roundtrip.json').read_text())
output=directory/'position-diagnostic.json'
if output.exists():raise RuntimeError('Preserve prior diagnostic')
report={}
for name in ['Idle','Walk','Run','FacePerformance']:
    frame=fail['clips'][name]['worstPositionSample']['sourceFrame']
    expected=next(s for s in receipt['clips'][name]['sourceSamples'] if s['frame']==frame)['bones']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(directory/receipt['clips'][name]['file']))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');action=bpy.data.actions[0]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    bpy.context.scene.frame_set(round(action.frame_range[0]+frame-receipt['clips'][name]['frameRange'][0]))
    bpy.context.view_layer.update()
    imported={}
    for b in rig.pose.bones:
        world=rig.matrix_world@b.matrix
        imported[b.name]={'error':(world.translation-Vector(expected[b.name]['head'])).length,
            'worldHead':list(world.translation),'location':list(b.location),'basisLocation':list(b.matrix_basis.translation),
            'connected':b.bone.use_connect,'parent':b.parent.name if b.parent else None,
            'inheritScale':b.bone.inherit_scale,'localLocation':b.bone.use_local_location}
    bpy.ops.wm.open_mainfile(filepath=receipt['source'])
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'Pelvis' in o.data.bones)
    sys.path.insert(0,str(Path(__file__).parent));import export_contract
    export_contract.prepare(bpy,{})
    export_contract.select_action(bpy,rig,bpy.data.actions[name])
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    evaluated=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    source={}
    for n,data in imported.items():
        b=rig.pose.bones[n];evaluated_world=evaluated.matrix_world@evaluated.pose.bones[n].matrix
        source[n]={'worldHead':list((rig.matrix_world@b.matrix).translation),'evaluatedHead':list(evaluated_world.translation),
            'location':list(b.location),'basisLocation':list(b.matrix_basis.translation),'connected':b.bone.use_connect,
            'inheritScale':b.bone.inherit_scale,'localLocation':b.bone.use_local_location,
            'exportSampleError':(evaluated_world.translation-Vector(expected[n]['head'])).length}
    report[name]={'sourceFrame':frame,'source':source,'imported':imported,
                  'worst':sorted(imported,key=lambda n:imported[n]['error'],reverse=True)[:8]}
    print('POSITION_DIAGNOSTIC',name,[(n,imported[n]['error'],source[n]['exportSampleError']) for n in report[name]['worst']],flush=True)
output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('KRAG_KINGS_MOTION_POSITION_DIAGNOSTIC_COMPLETE',flush=True)
