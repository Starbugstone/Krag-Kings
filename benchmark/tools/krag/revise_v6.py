from pathlib import Path
p=Path(__file__).with_name('build_krag.py');s=p.read_text()
s=s.replace("l.new(tc.outputs['Object'],node.inputs['Vector']);maps[ch]=node","mapping=n.get('Skin physical scale')\n        if mapping is None:\n            mapping=n.new('ShaderNodeVectorMath');mapping.name='Skin physical scale';mapping.operation='SCALE';mapping.inputs['Scale'].default_value=2.1;l.new(tc.outputs['Object'],mapping.inputs[0])\n        l.new(mapping.outputs[0],node.inputs['Vector']);maps[ch]=node")
s=s.replace("(.70,.62,.52,1)","(.55,.36,.19,1)").replace("relief.inputs['Distance'].default_value=.003","relief.inputs['Distance'].default_value=.0018")
s=s.replace("def finish(o,name,ma,group,bn=None,smooth=True):", "face_skin=skin.copy();face_skin.name='Krag_FacialSkin';materials[face_skin.name]=face_skin\nif face_skin.node_tree.nodes.get('Skin physical scale'):face_skin.node_tree.nodes['Skin physical scale'].inputs['Scale'].default_value=4.6\nfor node in face_skin.node_tree.nodes:\n    if node.type=='BUMP':node.inputs['Distance'].default_value*=.45\n\ndef finish(o,name,ma,group,bn=None,smooth=True):\n    if ma==skin and group in ['Head','Face','Eyelids_L','Eyelids_R']:ma=face_skin")
s=s.replace("('Deltoid',(s*.367,.012,1.609),(.172,.150,.165))","('Deltoid',(s*.367,.012,1.593),(.155,.142,.190))").replace("('Biceps',(s*.449,-.031,1.436),(.124,.119,.180))","('Biceps',(s*.445,-.025,1.442),(.128,.111,.200))").replace("('Triceps',(s*.427,.053,1.468),(.124,.131,.191))","('Triceps',(s*.429,.048,1.453),(.126,.124,.215))").replace("('Wrist',(s*.599,-.019,1.038),(.069,.063,.088))","('Wrist',(s*.599,-.019,1.045),(.077,.067,.116))")
s=s.replace("n=64,fold=.055","n=64,fold=.018")
a=s.index('# Scarf: continuous cloth shell,');b=s.index('# Hanging front sash,',a)
s=s[:a]+'''# Scarf cloth follows the shoulders at its sides and hangs in deep irregular U folds on the chest.
vs=[];fs=[];N=128;M=42
for k in range(M):
    u=k/(M-1)
    for j in range(N):
        a=2*pi*j/N;front=max(0,-sin(a));side=abs(cos(a));fold=.009*sin(5.3*pi*u+.55*sin(a*2)+.4*cos(a*3))*sin(pi*u)**.55
        radius=.148+.082*u+fold+.005*sin(a*3+u*5)*u
        z=1.813-.064*u-front*(.154*u+.020*sin(pi*u))+.010*cos(a*2+u*4)*u
        x=radius*cos(a);y=.019+(radius+front*.023*u)*sin(a)
        vs.append((x,y,z))
for k in range(M-1):
    for j in range(N):a=k*N+j;b=k*N+(j+1)%N;fs.append((a,b,b+N,a+N))
o=mesh('Loose U-fold desert scarf',vs,fs,cloth,'Scarf','Chest');sol=o.modifiers.new('Double faced woven cloth','SOLIDIFY');sol.thickness=.003;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)
# Overlapping tucked fabric end; not a flat circular collar brim.
vs=[];fs=[]
for i in range(24):
    t=i/23
    for j in range(13):
        u=j/12;x=-.115+.072*u+.044*t;y=-.146-.100*t-.011*sin(u*pi*3+t*4);z=1.777-.141*t+.012*sin(u*4+t*6)
        vs.append((x,y,z))
for i in range(23):
    for j in range(12):a=i*13+j;fs.append((a,a+1,a+14,a+13))
o=mesh('Tucked scarf end',vs,fs,cloth,'Scarf','Chest');sol=o.modifiers.new('Fabric edge thickness','SOLIDIFY');sol.thickness=.003;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)
''' +s[b:]
a=s.index("for v in trousers.data.vertices:\n");b=s.index('# Reference-proportion head:',a)
s=s[:a]+'''for v in trousers.data.vertices:
    x,y,z=v.co
    if .58<z<1.07:
        # A few broad unequal compression folds, radiating from hip/crotch and knee.
        side=1 if x>0 else -1;front=max(0,min(1,(-y+.025)/.09));xx=abs(x)
        folds=[(.951,-.29,.010,.018),(.864,.22,-.007,.022),(.714,-.19,.006,.019)] if side>0 else [(.925,.24,.009,.024),(.823,-.31,-.008,.018),(.672,.16,.006,.023)]
        delta=0
        for zz,slope,amp,width in folds:
            distance=z-zz-slope*(xx-.18);across=math.exp(-((xx-.18)/.16)**4)
            delta+=amp*(math.exp(-(distance/width)**2)-.48*math.exp(-((distance-width*1.6)/(width*1.5))**2))*across
        v.co.y-=delta*front
''' +s[b:]
# Overlapping forged plates have distinct seams and curved crowns, rather than one cone shell.
s=s.replace("shoulder_plate('Teal salvage pauldron',0,0,1.04,paint)","shoulder_plate('Dark structural pauldron',0,-.009,1.01,steel)\nfor plate,x0,x1,radius,offset in [('Inner overlapping crown',.205,.350,.207,.008),('Middle overlapping crown',.321,.444,.195,.013),('Outer overlapping crown',.418,.548,.174,.016)]:\n    vs=[];fs=[];nx=17;ny=37\n    for i in range(nx):\n        t=i/(nx-1);x=x0+(x1-x0)*t\n        for j in range(ny):\n            a=-.03+(pi+.06)*j/(ny-1);r=radius-.035*t+.008*sin(pi*t);edge=.004*sin(a*5)*sin(pi*t)\n            vs.append((x,.012+(r+edge)*cos(a),1.578+offset+r*sin(a)-.033*(x-.20)/.34))\n    for i in range(nx-1):\n        for j in range(ny-1):k=i*ny+j;fs.append((k,k+1,k+ny+1,k+ny))\n    o=mesh(plate,vs,fs,paint,'Armor','UpperArm_L');solid=o.modifiers.new('Forged overlapping plate thickness','SOLIDIFY');solid.thickness=.007;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=solid.name)\n    tube(plate+' rolled outer edge',[vs[(nx-1)*ny+j] for j in range(ny)],.0045,steel,'Armor','UpperArm_L',10)")
p.write_text(s)
