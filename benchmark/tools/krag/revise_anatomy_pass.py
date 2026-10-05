from pathlib import Path
p=Path(__file__).with_name('build_krag.py');s=p.read_text()
# Subdued continuous thorax anatomy, rather than spherical pectorals and abdominal beads.
s=s.replace("p.rotation_euler.y=side*-.10", "p.rotation_euler.y=side*-.10\n    for v in p.data.vertices:\n        if v.co.z<0:v.co.z*=.68")
s=s.replace("for z,rx in [(1.34,.112),(1.245,.104),(1.16,.092)]:flesh('Abdominal segment',(side*.083,-.137,z),(rx,.040,.071))", "for z,rx in [(1.29,.112),(1.18,.105)]:flesh('Abdominal segment',(side*.080,-.158,z),(rx,.027,.090))")
s=s.replace("(.174,.155,.176)", "(.172,.150,.165)").replace("(.131,.134,.191)","(.124,.119,.180)")
# Join the ENTIRE natural torso + arms first. Anatomical modules later share boundaries/normals/weights.
needle="log('Clothing, boots, harness and plate armor')"
insert="""log('Continuous torso-arm surface and anatomical partition')
skin_groups={'Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R'}
skin_parts=[o for o in bpy.data.objects if o.type=='MESH' and o.get('module') in skin_groups]
unified=join_sculpt(skin_parts,'Unified natural Krag anatomy',.0032,5)
bpy.context.view_layer.objects.active=unified;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
unified.data.update();src=unified.data
bins={g:[] for g in skin_groups}
for poly in src.polygons:
    co=poly.center
    if abs(co.x)<.325:group='Body'
    else:
        side='L' if co.x>0 else 'R';sgn=1 if co.x>0 else -1
        elbow=Vector((sgn*.509,.008,1.30));axis=Vector((sgn*.09,-.02,-.257)).normalized()
        group=('BioForearm_' if (co-elbow).dot(axis)>0 else 'BioArm_')+side
    bins[group].append(poly)
for group,polys in bins.items():
    used=sorted(set(i for poly in polys for i in poly.vertices));index={v:i for i,v in enumerate(used)}
    dat=bpy.data.meshes.new(group+' continuous surface');dat.from_pydata([src.vertices[i].co for i in used],[],[tuple(index[i] for i in poly.vertices) for poly in polys]);dat.update()
    for ma in src.materials:dat.materials.append(ma)
    for a,b in zip(dat.polygons,polys):a.material_index=b.material_index;a.use_smooth=True
    try:dat.normals_split_custom_set_from_vertices([tuple(src.vertices[i].normal) for i in used])
    except Exception as e:log('Custom normal fallback '+str(e))
    o=bpy.data.objects.new(group,dat);bpy.context.collection.objects.link(o);mark(o,group)
bpy.data.objects.remove(unified,do_unlink=True)
log('Clothing, boots, harness and plate armor')"""
assert needle in s;s=s.replace(needle,insert)
# Tailored seat tapers toward a real crotch instead of ending in a horizontal box.
s=s.replace("[(.905,0,.02,.252,.18),(.99,0,.02,.265,.19),(1.065,0,.02,.25,.181),(1.10,0,.02,.247,.17)]", "[(.885,0,.02,.083,.127),(.945,0,.02,.195,.169),(1.015,0,.02,.261,.190),(1.065,0,.02,.25,.185),(1.10,0,.02,.247,.175)]")
# Broad scowling lips have a dropped corner and a protruding muzzle, not horizontal line.
s=s.replace("[(-.091,-.177,1.845),(-.060,-.191,1.850),(0,-.197,1.849),(.060,-.191,1.850),(.091,-.177,1.845)]", "[(-.095,-.175,1.825),(-.065,-.191,1.840),(0,-.207,1.843),(.065,-.191,1.840),(.095,-.175,1.825)]")
s=s.replace("[(-.071,-.183,1.836),(0,-.197,1.835),(.071,-.183,1.836)]", "[(-.080,-.183,1.819),(-.049,-.199,1.830),(0,-.207,1.833),(.049,-.199,1.830),(.080,-.183,1.819)]")
s=s.replace("[.011,.015,.011],skin,'Face'", "[.006,.011,.013,.011,.006],skin,'Face'")
# Dust-toned restrained nail plates avoid chocolate-colored spherical fingertips.
s=s.replace("(.010,.004,.014),leather,'HandDetails_", "(.008,.0025,.010),skin,'HandDetails_")
# Continuous upper trousers, with tension folds across front crotch and quadriceps.
needle="# Consolidate modules while preserving bone membership per vertex."
insert="""# Blend upper trouser cloth into one tailored surface; accessories remain separate.
trouser_parts=[o for o in bpy.data.objects if o.type=='MESH' and (o.name=='Trouser seat' or o.name.startswith('Trousers_upper_'))]
trousers=join_sculpt(trouser_parts,'Tailored trouser base',.0032,3);trousers['module']='Garments'
bpy.context.view_layer.objects.active=trousers;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in trousers.data.vertices:
    x,y,z=v.co
    if .58<z<1.07:
        pressure=math.exp(-((z-.88)/.17)**2);d=.0075*sin((z-.97+abs(x)*.44)*105)*pressure
        v.co.y+=(-1 if y<.02 else 1)*d;v.co.x+=.003*sin(z*67+abs(x)*24)*pressure*(1 if x>0 else -1)
# Reference-proportion head: compact adult cranium, broad bulldog jaw, fixed crown.
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.get('module') in {'Head','Face','BionicJaw_Iron','BionicEye_L'}:
        mat=o.matrix_world.copy();inv=mat.inverted()
        for v in o.data.vertices:
            q=mat@v.co;q.x*=.86;q.y*=.87;q.z=2.107+(q.z-2.107)*.78;v.co=inv@q
# Consolidate modules while preserving bone membership per vertex."""
assert needle in s;s=s.replace(needle,insert)
# All adjacent natural skin pieces receive identical weights to prevent split boundaries opening.
old="""    if g=='Body':allowed=['Pelvis','Spine','Chest','Neck']
    elif g.startswith('BioArm_'):side=g[-1];allowed=['Clavicle_'+side,'UpperArm_'+side,'LowerArm_'+side]
    elif g.startswith('BioForearm_'):side=g[-1];allowed=['LowerArm_'+side,'Hand_'+side]
"""
new="""    if g in ['Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R']:allowed=['Pelvis','Spine','Chest','Neck']+[a+'_'+side for side in ['L','R'] for a in ['Clavicle','UpperArm','LowerArm','Hand']]
    elif g=='Garments':allowed=['Pelvis','Thigh_L','Thigh_R','Shin_L','Shin_R']
"""
assert old in s;s=s.replace(old,new)
s=s.replace("bn('Jaw',(0,-.04,1.845),(0,-.17,1.79),'Head')", "bn('Jaw',(0,-.0348,1.9026),(0,-.1479,1.8597),'Head')")
p.write_text(s)
# Keep full detail by default; reduction becomes an explicit optional experiment.
p=Path(__file__).with_name('export_krag.py');s=p.read_text();s=s.replace("if tris>target:","if '--optimize' in sys.argv and tris>target:");p.write_text(s)
