from pathlib import Path
p=Path(__file__).with_name('build_krag.py');s=p.read_text()
s=s.replace("(s*.542,-.128,.905)", "(s*.568,-.131,.920)")
s=s.replace("skin,'HandDetails_'+side,'Hand_'+side)\n    lower.append", "skin,'HandDetails_'+side,'Finger2_'+str(j)+'_'+side)\n    lower.append")
# Exactly matched phalange positions, used by both skin weighting and authored grip poses.
needle="for j,dx in enumerate([-.106,0,.106]):bn('Claw_'"
insert="""for s,side in [(-1,'R'),(1,'L')]:
    for j in range(4):
        x=s*(.570+j*.035);z=.901+abs(j-1.5)*.012
        a=(x,-.053,z);b=(x+s*.009,-.053,z-.048);c=(x-s*.002,-.111,z-.091)
        bn('Finger1_'+str(j)+'_'+side,a,b,'Hand_'+side);bn('Finger2_'+str(j)+'_'+side,b,c,'Finger1_'+str(j)+'_'+side)
    bn('Thumb1_'+side,(s*.555,-.038,.986),(s*.523,-.112,.919),'Hand_'+side);bn('Thumb2_'+side,(s*.523,-.112,.919),(s*.568,-.131,.920),'Thumb1_'+side)
for j,dx in enumerate([-.106,0,.106]):bn('Claw_'"""
assert needle in s;s=s.replace(needle,insert)
# Dedicated articulated hand weights, rest of body uses consistent shared skin-boundary weights.
s=s.replace("vgs={n:o.vertex_groups.new(name=n) for n in allowed}", "extra=[n for n in bones if n.startswith('Finger') or n.startswith('Thumb')] if g in ['Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R'] else []\n        vgs={n:o.vertex_groups.new(name=n) for n in allowed+extra}")
s=s.replace("ds=sorted([(distseg(v.co,*bones[n]),n) for n in allowed]);pairs=ds[:2]", "candidates=allowed\n            if extra and abs(v.co.x)>.48 and v.co.z<1.05:\n                side='L' if v.co.x>0 else 'R';candidates=['Hand_'+side,'LowerArm_'+side]+[n for n in extra if n.endswith('_'+side)]\n            ds=sorted([(distseg(v.co,*bones[n]),n) for n in candidates]);pairs=ds[:2]")
# Runtime carries a hand cannon on right; free left has relaxed staggered fingers.
s=s.replace("reset();t=(f-1)/(frames-1);wave=sin(t*2*pi)", "reset();t=(f-1)/(frames-1);wave=sin(t*2*pi)\n        for j in range(4):\n            rot('Finger1_'+str(j)+'_R',-.68,0,(j-1.5)*.018);rot('Finger2_'+str(j)+'_R',-.78)\n            curl=.80 if name=='Melee' else .11+j*.018\n            rot('Finger1_'+str(j)+'_L',-curl,0,(j-1.5)*.035);rot('Finger2_'+str(j)+'_L',-curl*.8)\n        rot('Thumb1_R',-.18,0,.34);rot('Thumb2_R',-.14);rot('Thumb1_L',-.06,0,-.08)")
p.write_text(s)
# Neutral source art review omits firearm and relaxes hand grip; action/runtime evidence keeps full clips.
p=Path(__file__).with_name('review_krag.py');s=p.read_text()
s=s.replace("for o in bpy.data.objects:\n    if o.type=='MESH'", "if not opt.runtime and opt.clip=='Idle':\n    rig.animation_data.action=None\n    for pb in rig.pose.bones:\n        if pb.name.startswith('Finger') or pb.name.startswith('Thumb'):pb.rotation_euler=(0,0,0)\n    bpy.context.view_layer.update()\nfor o in bpy.data.objects:\n    if o.type=='MESH'")
p.write_text(s)
