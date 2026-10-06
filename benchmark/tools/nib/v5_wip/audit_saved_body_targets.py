import bpy,json,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[4];src=root/'benchmark/art/nib/Nib_Runtime_Optimized_v4b.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));out=[]
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
 if obj.type!='MESH' or not obj.data.shape_keys:continue
 keys=obj.data.shape_keys.key_blocks; basis=np.array([p.co[:] for p in keys[0].data]);matrix=np.array(obj.matrix_world);world=basis@matrix[:3,:3].T+matrix[:3,3]
 for key in keys:
  if not key.name.startswith('Corrective_'):continue
  delta=(np.array([p.co[:] for p in key.data])-basis)@matrix[:3,:3].T;mag=np.linalg.norm(delta,axis=1);worst=int(mag.argmax())
  out.append({'object':obj.name,'bone':obj.get('bone'),'key':key.name,'maxDeltaMeters':float(mag[worst]),'worstWorldPoint':world[worst].tolist(),'keyValue':key.value})
(root/'benchmark/art/nib/v5-study/saved-body-target-audit.json').write_text(json.dumps(out,indent=2),newline='\n')
print('NIB_SAVED_BODY_TARGET_AUDIT_COMPLETE',flush=True)
