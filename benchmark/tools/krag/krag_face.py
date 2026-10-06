"""Hybrid facial rig: jaw/eyes skeletal; FACS soft-tissue morphs from facial controls.
Mouth interiors are provisional concept-compatible anatomy, not approved canon.
Runtime drivers use coordinate-invariant deltas from imported neutral bind transforms.
"""
import bpy, math, json, sys
import numpy as np
from mathutils import Vector
from math import sin,cos,pi

def H(p):
    q=(p[0]*.93,p[1]*.94,2.107+(p[2]-2.107)*.85)
    if '--reference-head-scale' in sys.argv:
        from krag_proportions_v9f import point
        return point(q)
    return q

def H_array(points):
    q=np.asarray(points,dtype=float)*np.asarray((.93,.94,.85))
    q[:,2]+=2.107*(1-.85)
    if '--reference-head-scale' in sys.argv:
        from krag_proportions_v9f import transform
        q=transform(q)
    return q
FACIAL=['Blink_L','Blink_R','Squint_L','Squint_R','BrowRaise_L','BrowRaise_R','BrowLower_L','BrowLower_R','Smile_L','Smile_R','Frown_L','Frown_R','JawOpen','LipPress','Snarl_L','Snarl_R','NoseWrinkle']
BODY=[f'Corrective_{kind}_{side}' for kind in ['ShoulderRaise','ElbowFlex','HipFlex','KneeFlex'] for side in ['L','R']]
MORPHS=FACIAL+BODY

def geometry(c,continuous=False):
    ball,mesh,tube,box=c['uvball'],c['mesh'],c['tube'],c['box'];skin,bone,dark=c['skin'],c['bone'],c['dark']
    gum=c['mat']('Krag_OralTissue',(.13,.041,.025),0,.43);tongue=c['mat']('Krag_Tongue',(.115,.045,.032),0,.37)
    if not continuous:
        # Sculpt an actual frowning mouth aperture. Dark oral bag lies behind this cavity.
        vs=[];N=48
        for y in [-.275,-.064]:
            for j in range(N):
                a=2*pi*j/N;x=.096*cos(a);z=1.845-.018*(abs(x)/.096)**1.5+.0035*sin(a);vs.append((x,y,z))
        fs=[tuple(range(N)),tuple(reversed(range(N,2*N)))]+[(i,i+N,(i+1)%N+N,(i+1)%N) for i in range(N)]
        cutter=mesh('Provisional mouth aperture cutter',vs,fs,skin,'TEMP')
        head=bpy.data.objects.get('Head_Sculpt');bpy.context.view_layer.objects.active=head
        boolean=head.modifiers.new('Anatomical mouth aperture','BOOLEAN');boolean.operation='DIFFERENCE';boolean.solver='EXACT';boolean.object=cutter;bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
        for side in [-1,1]:
            cutter=ball('Nostril cavity cutter',(side*.026,-.215,1.912),(.012,.023,.007),skin,'TEMP','Head',seg=32,rings=20)
            bpy.context.view_layer.objects.active=head;boolean=head.modifiers.new('Recessed nostril','BOOLEAN');boolean.operation='DIFFERENCE';boolean.solver='EXACT';boolean.object=cutter;bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
            ball('Inner nasal shadow',(side*.026,-.194,1.912),(.010,.005,.005),dark,'Face','Head',seg=24,rings=16)
    ball('Oral cavity lining',(0,-.024,1.829),(.105,.138,.111),dark,'MouthInterior','Head',seg=40,rings=28)
    for upper in [True,False]:
        z=1.851 if upper else 1.809;bn='Head' if upper else 'Jaw'
        tube('Upper gum ridge' if upper else 'Lower gum ridge',[(x,-.134-.011*(1-(x/.09)**2),z) for x in [-.080,-.055,-.027,0,.027,.055,.080]],.011,gum,'MouthInterior',bn,16)
        for j in range(8):
            x=(j-3.5)*.019;y=-.144+.020*(abs(x)/.07)**1.6
            tooth=box(('Upper' if upper else 'Lower')+' provisional tooth '+str(j),(x,y,z+(-.010 if upper else .008)),(.0155,.018,.021 if upper else .018),bone,'MouthInterior',bn,bevel=.004)
            tooth.rotation_euler.y=(j-3.5)*.024
    ball('Tongue body',(0,-.073,1.808),(.050,.065,.010),tongue,'MouthInterior','Tongue_01',seg=40,rings=20)
    ball('Tongue front',(0,-.129,1.810),(.038,.035,.009),tongue,'MouthInterior','Tongue_02',seg=32,rings=20)
    tube('Tongue median groove',[(0,-.063,1.818),(0,-.097,1.818),(0,-.129,1.817)],[.0008,.001,.0005],gum,'MouthInterior','Tongue_02',8)
    if continuous:return  # Continuous cage already contains eyelids, nostrils and lip loops.
    # Physical lid ribbons attach into orbital skin; blink morphs cover cornea completely.
    for s,side in [(1,'L'),(-1,'R')]:
        cutter=ball('Orbital cavity cutter',(s*.071,-.161,1.964),(.026,.024,.019),skin,'TEMP','Head',seg=40,rings=28)
        bpy.context.view_layer.objects.active=head;boolean=head.modifiers.new('True orbital recess '+side,'BOOLEAN');boolean.operation='DIFFERENCE';boolean.solver='EXACT';boolean.object=cutter;bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
        for upper in [True,False]:
            vs=[];fs=[];nx=33;ny=7
            for k in range(ny):
                w=k/(ny-1)
                for j in range(nx):
                    u=2*j/(nx-1)-1;x=s*.071+u*.032;y=-.185+.012*u*u+.018*w
                    z=(1.964+.010*(1-u*u)+.015*w) if upper else (1.964-.007*(1-u*u)-.016*w)
                    vs.append((x,y,z))
            for k in range(ny-1):
                for j in range(nx-1):
                    i=k*nx+j;f=(i,i+1,i+nx+1,i+nx);fs.append(f if upper else tuple(reversed(f)))
            o=mesh(('Upper' if upper else 'Lower')+' eyelid '+side,vs,fs,skin,'Eyelids_'+side,'Head');so=o.modifiers.new('Lid skin thickness','SOLIDIFY');so.thickness=.0015;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=so.name)

    bpy.context.view_layer.objects.active=head;edge=head.modifiers.new('Soft anatomical cavity rims','BEVEL');edge.width=.0011;edge.segments=3;edge.limit_method='ANGLE';edge.angle_limit=.70;bpy.ops.object.modifier_apply(modifier=edge.name)
    # Low-relief facial creases are part of the same deforming skin surface.
    # These follow the frown/nasolabial anatomy rather than a repeated crack tile.
    for vertex in head.data.vertices:
        x,y,z=vertex.co;front=max(0,min(1,(-y-.055)/.080))
        if not front:continue
        crease=0
        for height,width,strength in [(2.020,.0020,.0010),(2.045,.0016,.0007)]:
            line=height+.022*(abs(x)/.135)**1.5
            crease+=strength*math.exp(-((z-line)/width)**2)*math.exp(-(x/.14)**6)
        # Paired vertical glabellar furrows and cheek-to-mouth folds.
        for side in [-1,1]:
            crease+=.0015*math.exp(-((x-side*.021)/.0025)**2)*math.exp(-((z-1.997)/.030)**4)
            t=max(0,min(1,(1.916-z)/.083));line=side*(.048+.048*t)
            crease+=.0013*math.exp(-((x-line)/.0024)**2)*math.exp(-((z-1.876)/.046)**4)
        vertex.co.y+=crease*front
    # Preserve the quieter central facial material and assign fractured skin
    # only to the outer skull/temple. Both are portable authored PBR materials.
    if skin.name not in [material.name for material in head.data.materials]:head.data.materials.append(skin)
    outer_index=next(i for i,material in enumerate(head.data.materials) if material==skin)
    head.data.update()
    for polygon in head.data.polygons:
        x,y,z=polygon.center
        if z>2.045 or abs(x)>.142 or y>-.025:polygon.material_index=outer_index

def bones(bn,landmarks=None):
    landmarks=landmarks or {}
    bn('FaceRoot',H((0,-.015,1.885)),H((0,-.015,1.985)),'Head')
    # Existing Jaw is reparented by caller after this function.
    for s,side in [(1,'L'),(-1,'R')]:
        points={'Eye':(s*.071,-.165,1.964),'LidUpper':(s*.071,-.184,1.974),'LidLower':(s*.071,-.184,1.954),'BrowInner':(s*.040,-.170,1.990),'BrowOuter':(s*.108,-.141,1.993),'Cheek':(s*.111,-.129,1.908),'MouthCorner':(s*.090,-.184,1.830)}
        for n,p in points.items():
            p=landmarks.get(n+'_'+side,p)
            tail=(p[0],p[1]-.040,p[2]) if n=='Eye' else (p[0],p[1],p[2]+.030)
            b=bn(n+'_'+side,H(p),H(tail),'FaceRoot');b.use_deform=n=='Eye'
    for n,p in [('LipUpper',(0,-.198,1.853)),('LipLower',(0,-.202,1.830)),('NoseTip',(0,-.220,1.925))]:
        p=landmarks.get(n,p)
        b=bn(n,H(p),H((p[0],p[1],p[2]+.025)),'FaceRoot');b.use_deform=False
    base=landmarks.get('TongueBase',(0,-.025,1.81));middle=landmarks.get('TongueMiddle',(0,-.095,1.81));tip=landmarks.get('TongueTip',(0,-.158,1.81))
    bn('Tongue_01',H(base),H(middle),'Jaw');bn('Tongue_02',H(middle),H(tip),'Tongue_01')

def driver_manifest():
    drivers=[]
    def d(m,b,ch,start,end,kind='facial'):drivers.append(dict(morph=m,bone=b,channel=ch,start=start,end=end,maxWeight=1.0,kind=kind))
    for side in ['L','R']:
        d('Blink_'+side,'LidUpper_'+side,'translationDistanceMeters',0,.012)
        d('Squint_'+side,'LidLower_'+side,'translationDistanceMeters',0,.006)
        d('BrowRaise_'+side,'BrowOuter_'+side,'translationDistanceMeters',0,.010)
        d('BrowLower_'+side,'BrowInner_'+side,'translationDistanceMeters',0,.007)
        d('Smile_'+side,'MouthCorner_'+side,'translationDistanceMeters',0,.007)
        d('Frown_'+side,'MouthCorner_'+side,'rotationMagnitudeDegrees',0,18)
        d('Snarl_'+side,'Cheek_'+side,'rotationMagnitudeDegrees',0,18)
        for kind,bone,start,end in [('ShoulderRaise','UpperArm',25,95),('ElbowFlex','LowerArm',20,105),('HipFlex','Thigh',20,80),('KneeFlex','Shin',20,105)]:d('Corrective_'+kind+'_'+side,bone+'_'+side,'rotationMagnitudeDegrees',start,end,'body')
    d('JawOpen','Jaw','rotationMagnitudeDegrees',0,25);d('LipPress','LipUpper','translationDistanceMeters',0,.006);d('NoseWrinkle','NoseTip','translationDistanceMeters',0,.005)
    return dict(schemaVersion=1,faceRoot='FaceRoot',drivers=drivers,morphs=MORPHS,controls='Jaw and eye bones deform directly; expression controls drive soft-tissue morphs and fine geometry wrinkles.',interiorsStatus='Provisional anatomy for review; serious Krag expression direction. No playful tongue extension.')

def _field(v,center,radius):
    return np.exp(-2*np.sum(((v-np.array(center))/np.array(radius))**2,axis=1))

def deform(group,v,name):
    delta=np.zeros_like(v);isface=group in ['Head','Face','Eyelids_L','Eyelids_R','MouthInterior','BionicJaw_Iron','BionicEye_L']
    if name in FACIAL and not isface:return delta
    face_mask=np.clip((-v[:,1]-.025)/.075,0,1)
    if name in FACIAL:
        side=name[-1] if name.endswith(('_L','_R')) else None;s=1 if side=='L' else -1
        if name.startswith('Blink'):
            cx=H((s*.071,0,0))[0];eyeZ=H((0,0,1.964))[2]
            horizontal=np.clip(1-((v[:,0]-cx)/.028)**2,0,1)**.5
            if group=='Eyelids_'+side:
                # Both ribbons approach the same contact line. Taper outer attachment influence.
                inner=np.clip((-.137-v[:,1])/.024,0,1);upper=(v[:,2]>eyeZ).astype(float);lower=1-upper
                delta[:,2]=horizontal*inner*(-.0093*upper+.004*lower)
                delta[:,1]=horizontal*inner*-.0015
            elif group in ['Head','Face']:
                w=_field(v,H((s*.071,-.166,1.975)),(.040,.030,.023))*face_mask;delta[:,2]=-.003*w;delta[:,1]=.0014*w*np.sin((v[:,2]-eyeZ)*520)
        elif name.startswith('Squint'):
            w=_field(v,H((s*.076,-.145,1.944)),(.050,.045,.026))*face_mask;delta[:,2]=.004*w;delta[:,1]=-.001*w
        elif name.startswith('BrowRaise') or name.startswith('BrowLower'):
            raiseB=name.startswith('BrowRaise');w=_field(v,H((s*.073,-.12,2.005)),(.065,.09,.041))*face_mask
            delta[:,2]=(.0085 if raiseB else -.006)*w;delta[:,0]=(-s*.003 if not raiseB else s*.001)*w
            forehead=_field(v,H((s*.066,-.11,2.04)),(.070,.08,.049))*face_mask;delta[:,1]=.0014*forehead*np.sin((v[:,2]-H((0,0,2.04))[2])*800)
        elif name.startswith('Smile') or name.startswith('Frown'):
            smile=name.startswith('Smile');w=_field(v,H((s*.09,-.16,1.836)),(.037,.065,.029))*face_mask;delta[:,2]=(.0047 if smile else -.0065)*w;delta[:,0]=s*(.0025 if smile else -.001)*w
            cheek=_field(v,H((s*.11,-.10,1.884)),(.045,.07,.04))*face_mask;delta[:,2]+=(.0018 if smile else -.0012)*cheek
        elif name.startswith('Snarl'):
            w=_field(v,H((s*.057,-.18,1.868)),(.043,.060,.026))*face_mask;delta[:,2]=.0055*w;delta[:,1]=-.002*w
        elif name=='LipPress':
            upper=_field(v,H((0,-.17,1.859)),(.11,.07,.013))*face_mask;lower=_field(v,H((0,-.17,1.827)),(.11,.07,.013))*face_mask;delta[:,2]=-.0028*upper+.002*lower;delta[:,1]=-.0015*(upper+lower)
        elif name=='NoseWrinkle':
            w=_field(v,H((0,-.17,1.919)),(.065,.065,.050))*face_mask;delta[:,2]=.002*w;delta[:,1]=.0017*w*np.sin(v[:,0]*230)
        elif name=='JawOpen':
            # Skeletal jaw provides opening; corrective maintains mouth-corner/chin volume.
            w=_field(v,H((0,-.10,1.807)),(.11,.10,.038))*face_mask;delta[:,1]=-.0025*w
        if group=='MouthInterior' and name!='JawOpen':delta*=0
        if group in ['BionicJaw_Iron','BionicEye_L']:delta*=0
        return delta
    # Geometric volume correctives near highly flexed articulated joints.
    if name.startswith('Corrective_'):
        s=1 if name.endswith('_L') else -1
        if 'ShoulderRaise' in name:
            c=(s*.352,.016,1.592);r=(.19,.21,.20);amount=.013;allowed=group in ['Body','BioArm_L','BioArm_R']
        elif 'ElbowFlex' in name:
            c=(s*.509,.008,1.300);r=(.14,.16,.15);amount=.008;allowed=group.startswith('BioArm_') or group.startswith('BioForearm_')
        elif 'HipFlex' in name:
            c=(s*.167,.019,1.018);r=(.15,.20,.19);amount=.010;allowed=group in ['Body','Garments','NaturalThigh_R'] or group.startswith('TrouserLeg')
        else:
            c=(s*.188,-.016,.570);r=(.13,.16,.15);amount=.008;allowed=group in ['Garments','NaturalThigh_R'] or group.startswith(('TrouserLeg','BioLowerLeg'))
        if not allowed:return delta
        w=_field(v,c,r);radial=v-np.array(c);radial[:,2]*=.25;radial/=np.maximum(np.linalg.norm(radial,axis=1)[:,None],.01);delta=radial*(w*amount)[:,None]
    return delta

def add_morphs(modules,rig):
    """All modules share the exact key list so Blender FBX assembly joining preserves names."""
    data=driver_manifest()
    for group,o in modules.items():
        coords=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',coords);v=coords.reshape(-1,3)
        o.shape_key_add(name='Basis',from_mix=False)
        for name in MORPHS:
            k=o.shape_key_add(name=name,from_mix=False);delta=deform(group,v,name)
            if group=='Head' and name in FACIAL and 'krag_reference_position' in o.data.attributes:
                raw=np.empty(len(v)*3,dtype=np.float32)
                o.data.attributes['krag_reference_position'].data.foreach_get('vector',raw)
                raw=raw.reshape(-1,3)
                delta=continuous_face_delta(raw,name)
            if group=='Head' and name.startswith('Blink') and 'krag_reference_position' in o.data.attributes:
                # Continuous eyelid loops close together; the old primitive
                # head's small crease corrective cannot substitute for a blink.
                raw=np.empty(len(v)*3,dtype=np.float32)
                o.data.attributes['krag_reference_position'].data.foreach_get('vector',raw)
                raw=raw.reshape(-1,3);side=1 if name.endswith('_L') else -1
                envelope=np.exp(-((raw[:,0]-side*.0358764)/.022)**8-((raw[:,2]-.3100375)/.017)**8)
                envelope*=np.clip((-raw[:,1]-.045)/.040,0,1)
                from krag_head_v9 import fit
                eye=json.loads(o['krag_reference_eye_surfaces'])['L' if side>0 else 'R']
                center=np.asarray(eye['center']);closed=raw.copy();closed[:,2]=center[2]
                sphere_front=center[1]-np.sqrt(np.maximum(0,eye['radius']**2-(raw[:,0]-center[0])**2))-.0008
                closed[:,1]=np.minimum(raw[:,1],sphere_front)
                delta=(H_array(fit(closed))-H_array(fit(raw)))*envelope[:,None]
            if name in FACIAL:
                rigid_indices={g.index for g in o.vertex_groups if g.name.startswith(('Eye_','Tongue_'))}
                for vertex in o.data.vertices:
                    if any(g.group in rigid_indices and g.weight>.5 for g in vertex.groups):delta[vertex.index]=0
                for poly in o.data.polygons:
                    if o.data.materials[poly.material_index].name=='Krag_Ivory':delta[list(poly.vertices)]=0
            target=v+delta;k.data.foreach_set('co',target.ravel())
        # Bone local control magnitude is baked in Blender review; engines reproduce using the manifest.
        for d in data['drivers']:
            key=o.data.shape_keys.key_blocks[d['morph']];fc=key.driver_add('value');drv=fc.driver;drv.type='SCRIPTED';vars=[]
            for axis in 'xyz':
                var=drv.variables.new();var.name=axis;var.type='TRANSFORMS';tar=var.targets[0];tar.id=rig;tar.bone_target=d['bone'];tar.transform_space='LOCAL_SPACE';tar.transform_type=('ROT_' if d['channel']=='rotationMagnitudeDegrees' else 'LOC_')+axis.upper();vars.append(axis)
            metric=('2*acos(min(1,abs(cos(x/2)*cos(y/2)*cos(z/2)+sin(x/2)*sin(y/2)*sin(z/2))))*57.2957795131' if d['channel']=='rotationMagnitudeDegrees' else 'sqrt(x*x+y*y+z*z)')
            drv.expression=f'min(1.0,max(0.0,(({metric})-{d["start"]})/{d["end"]-d["start"]}))'
    return data


def continuous_face_delta(raw,name):
    """Expressions remain anchored to anatomical loops as the Krag fit changes."""
    from krag_head_v9 import fit
    delta=np.zeros_like(raw);sign=1 if name.endswith('_L') else -1
    front=np.clip((-raw[:,1]-.025)/.055,0,1)
    def field(center,radius):return _field(raw,center,radius)*front
    if name.startswith('Squint'):
        w=field((sign*.0359,-.106,.301),(.025,.060,.014));delta[:,2]=.0032*w;delta[:,1]=-.0008*w
    elif name.startswith(('BrowRaise','BrowLower')):
        raising=name.startswith('BrowRaise')
        w=field((sign*.035,-.101,.338),(.035,.085,.024))
        delta[:,2]=(.0065 if raising else -.0045)*w
        delta[:,0]=sign*(.0006 if raising else -.0013)*w
    elif name.startswith(('Smile','Frown')):
        smile=name.startswith('Smile');w=field((sign*.040,-.103,.234),(.020,.070,.019))
        delta[:,2]=(.0036 if smile else -.0042)*w;delta[:,0]=sign*(.0018 if smile else -.0006)*w
        delta[:,2]+=(.0014 if smile else -.0007)*field((sign*.054,-.080,.265),(.021,.08,.027))
    elif name.startswith('Snarl'):
        w=field((sign*.024,-.113,.247),(.022,.064,.018));delta[:,2]=.0040*w;delta[:,1]=-.0008*w
    elif name=='LipPress':
        upper=field((0,-.113,.240),(.060,.060,.008));lower=field((0,-.115,.226),(.060,.060,.008))
        delta[:,2]=-.0018*upper+.0018*lower;delta[:,1]=-.0006*(upper+lower)
    elif name=='NoseWrinkle':
        w=field((0,-.114,.274),(.032,.080,.030));delta[:,2]=.0017*w;delta[:,1]=.00065*w*np.sin(raw[:,0]*380)
    elif name=='JawOpen':
        w=field((0,-.080,.196),(.065,.100,.024));delta[:,1]=-.0015*w
    return H_array(fit(raw+delta))-H_array(fit(raw))

def face_weights(modules):
    # Jaw deforms mandible; upper face is preserved while morphs express soft-tissue controls.
    for name in ['Head','Face']:
        o=modules.get(name)
        if not o:continue
        jaw=o.vertex_groups.get('Jaw') or o.vertex_groups.new(name='Jaw');head=o.vertex_groups.get('Head') or o.vertex_groups.new(name='Head')
        rigid_ivory=set()
        for polygon in o.data.polygons:
            if o.data.materials[polygon.material_index].name=='Krag_Ivory':rigid_ivory.update(polygon.vertices)
        for v in o.data.vertices:
            x,y,z=v.co
            rigid_indices={g.index for g in o.vertex_groups if g.name.startswith(('Eye_','Tongue_'))}
            if v.index in rigid_ivory or any(g.group in rigid_indices and g.weight>.5 for g in v.groups):continue
            if name=='Head' and 'krag_reference_position' in o.data.attributes:
                raw=o.data.attributes['krag_reference_position'].data[v.index].vector
                if raw.z<.168:
                    neck=o.vertex_groups.get('Neck') or o.vertex_groups.new(name='Neck')
                    t=max(0,min(1,(raw.z-.125)/.043));t=t*t*(3-2*t)
                    head.add([v.index],t,'REPLACE');neck.add([v.index],1-t,'REPLACE');jaw.add([v.index],0,'REPLACE')
                    continue
                w=max(0,min(1,(.239-raw.z)/.011));w=w*w*(3-2*w)
                depth=max(0,min(1,(.055-raw.y)/.075));depth=depth*depth*(3-2*depth)
                w*=depth
                jaw.add([v.index],w,'REPLACE');head.add([v.index],1-w,'REPLACE')
                continue
            if y<-.032 and z<H((0,0,1.857))[2]:
                w=max(0,min(1,(H((0,0,1.857))[2]-z)/.030));jaw.add([v.index],w,'REPLACE');head.add([v.index],1-w,'REPLACE')

def performance(rig):
    """Six-second acting test: focus, suspicion, contained satisfaction, irritation, intimidation."""
    rig.animation_data_create();act=bpy.data.actions.new('FacePerformance');act.use_fake_user=True;rig.animation_data.action=act
    facial=[p for p in rig.pose.bones if p.name=='FaceRoot' or any(x.name=='FaceRoot' for x in p.parent_recursive)]
    def peak(t,c,width):return max(0,1-abs(t-c)/width)
    for frame in range(1,181):
        bpy.context.scene.frame_set(frame);t=(frame-1)/179
        for p in facial:p.rotation_mode='XYZ';p.rotation_euler=(0,0,0);p.location=(0,0,0)
        blink=min(1,1.18*max(peak(t,.11,.025),peak(t,.55,.022),peak(t,.91,.03)))
        suspicious=peak(t,.28,.16);satisfaction=peak(t,.45,.13);anger=peak(t,.66,.16);intimidate=peak(t,.81,.14)
        for side in ['L','R']:
            rig.pose.bones['LidUpper_'+side].location.y=-.012*blink
            rig.pose.bones['LidLower_'+side].location.y=.006*(.3*suspicious+.65*anger)
            rig.pose.bones['BrowInner_'+side].location.y=-.007*(.35*suspicious+.85*anger+.7*intimidate)
            rig.pose.bones['BrowOuter_'+side].location.y=.010*suspicious*(.75 if side=='L' else .10)
            rig.pose.bones['MouthCorner_'+side].location.y=.0035*satisfaction
            rig.pose.bones['MouthCorner_'+side].rotation_euler.x=math.radians(18)*(.5*anger+.7*intimidate)
            rig.pose.bones['Cheek_'+side].rotation_euler.x=math.radians(18)*intimidate*(.8 if side=='L' else .55)
            rig.pose.bones['Eye_'+side].rotation_euler.z=.12*suspicious*(1 if side=='L' else 1)
            rig.pose.bones['Eye_'+side].rotation_euler.x=-.025*suspicious
        rig.pose.bones['Jaw'].rotation_euler.x=math.radians(23)*intimidate
        rig.pose.bones['LipUpper'].location.y=.006*(.55*anger+.25*suspicious)
        rig.pose.bones['NoseTip'].location.y=.005*intimidate
        for p in facial:p.keyframe_insert('rotation_euler',frame=frame,group=p.name);p.keyframe_insert('location',frame=frame,group=p.name)
    act['description']='Serious Krag facial acting test; no playful tongue protrusion; mouth anatomy provisional.'
    return act

def action_expression(rig,name,t):
    """Expressions accompany body performance, preserving serious/fearless Krag personality."""
    def pulse(center,width):return max(0,1-abs(t-center)/width)
    brow=.18;squint=.09;press=.12;snarl=0;smile=0;jaw=0;blink=0;gaze=.014*sin(2*pi*t);asymmetry=0
    if name=='Idle':
        blink=min(1,1.18*pulse(.74,.045));brow+=.04*sin(2*pi*t);press+=.025*cos(2*pi*t)
    elif name=='Walk':
        brow=.30+.035*cos(4*pi*t);squint=.14;press=.20+.025*cos(4*pi*t)
    elif name=='Run':
        effort=.5-.5*cos(4*pi*t);brow=.45+.09*effort;squint=.24+.05*effort;press=.29;jaw=.04+.04*effort;snarl=.08*effort
    elif name=='Melee':
        force=pulse(.57,.23);settle=pulse(.80,.20);brow+=.55*force;squint+=.37*force;snarl=.55*force;jaw=.18*force;press+=.2*force;smile=.16*settle
    elif name=='Shoot':
        aim=min(1,t/.22)*max(0,1-max(0,t-.78)/.22);kick=pulse(.40,.065)+.7*pulse(.58,.055)
        brow+=.45*aim;squint+=.28*aim;asymmetry=.34*aim;press+=.31*aim;blink=.30*kick;gaze=0
    elif name=='Hit':
        impact=sin(min(t/.24,1)*pi/2)*math.exp(-max(0,t-.24)*4)
        brow+=.57*impact;squint+=.44*impact;press+=.46*impact;snarl=.16*impact;jaw=.035*impact;asymmetry=.10*impact
    for side in ['L','R']:
        rig.pose.bones['LidUpper_'+side].location.y=-.012*min(1,blink)
        rig.pose.bones['LidLower_'+side].location.y=.006*min(1,squint+(asymmetry if side=='L' else 0))
        rig.pose.bones['BrowInner_'+side].location.y=-.007*brow
        rig.pose.bones['MouthCorner_'+side].location.y=.007*smile*(1 if side=='L' else .65)
        rig.pose.bones['MouthCorner_'+side].rotation_euler.x=math.radians(18)*(.18*brow)
        rig.pose.bones['Cheek_'+side].rotation_euler.x=math.radians(18)*snarl*(1 if side=='L' else .75)
        rig.pose.bones['Eye_'+side].rotation_euler.z=gaze
    rig.pose.bones['Jaw'].rotation_euler.x=math.radians(25)*jaw
    rig.pose.bones['LipUpper'].location.y=.006*press
    rig.pose.bones['NoseTip'].location.y=.005*snarl*.4
