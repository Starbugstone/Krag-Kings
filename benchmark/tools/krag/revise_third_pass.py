from pathlib import Path
p=Path(__file__).with_name('build_krag.py');s=p.read_text()
# Protect the high shoulder rather than burying steel inside it.
s=s.replace("o.data.uv_layers.active.name='UVMap'\nlog('Skeletal rig')", "o.data.uv_layers.active.name='UVMap'\n    if g=='Armor':\n        for v in o.data.vertices:v.co.z+=.061;v.co.y-=.008\nlog('Skeletal rig')")
# Front scarf drapes in front of the chest surface, not through it.
s=s.replace(".028+radius*.76*sin(a)",".028+radius*1.10*sin(a)")
s=s.replace("front*.074*sin(pi*u)","front*.066*sin(pi*u)")
# Bent knees fold backward in the rig's local space; reverse hyperextension from first animation draft.
s=s.replace("rot('Shin_'+side,-max(0,-w)*.95-.08)", "rot('Shin_'+side,max(0,-w)*.95+.08)")
s=s.replace("rot('Shin_L',-.22*hit)", "rot('Shin_L',.22*hit)")
# A thin formed toe cover rather than a spherical steel lump.
old="toe=uvball('Steel toe cap',(s*.19,-.173,.109),(.123,.109,.067),steel,'Boot_'+side,'Foot_'+side)"
new="""vs=[];fs=[];rows=[(-.255,.071,.098),(-.240,.098,.125),(-.218,.112,.146),(-.190,.116,.154),(-.165,.112,.152)]
    for yy,rr,top in rows:
        for k in range(21):
            a=pi*k/20;vs.append((s*.19+rr*cos(a),yy,.052+(top-.052)*(max(0,sin(a))**.62)))
    for j in range(len(rows)-1):
        for k in range(20):a=j*21+k;fs.append((a,a+21,a+22,a+1))
    toe=mesh('Formed steel toe cover',vs,fs,steel,'Boot_'+side,'Foot_'+side);sol=toe.modifiers.new('Toe sheet thickness','SOLIDIFY');sol.thickness=.005;bpy.context.view_layer.objects.active=toe;bpy.ops.object.modifier_apply(modifier=sol.name)
    tube('Toe cover rolled rim',[(s*.19+rows[-1][1]*cos(pi*k/20),rows[-1][0],.052+(rows[-1][2]-.052)*max(0,sin(pi*k/20))**.62) for k in range(21)],.004,brass,'Boot_'+side,'Foot_'+side,8)"""
assert old in s;s=s.replace(old,new)
# Organic fracture coordinates avoid uniform reptile polygons.
old="vor.inputs['Scale'].default_value=24;l.new(tex.outputs['Object'],vor.inputs['Vector'])"
new="vor.inputs['Scale'].default_value=24;warp=n.new('ShaderNodeTexNoise');warp.inputs['Scale'].default_value=7;warp.inputs['Detail'].default_value=2;l.new(tex.outputs['Object'],warp.inputs['Vector']);mul=n.new('ShaderNodeVectorMath');mul.operation='SCALE';mul.inputs['Scale'].default_value=.054;l.new(warp.outputs['Color'],mul.inputs[0]);add=n.new('ShaderNodeVectorMath');add.operation='ADD';l.new(tex.outputs['Object'],add.inputs[0]);l.new(mul.outputs[0],add.inputs[1]);l.new(add.outputs[0],vor.inputs['Vector'])"
assert old in s;s=s.replace(old,new)
p.write_text(s)
