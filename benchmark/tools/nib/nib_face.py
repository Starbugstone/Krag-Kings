"""Connected Nib facial topology, muscle targets and provisional mouth anatomy.

The dark-blue tongue is canonical. Tooth layout and mouth proportions remain
provisional until the actual expression review receives artistic approval.
"""
import bpy, math
from mathutils import Vector

FACIAL_MORPHS=['Blink_L','Blink_R','Squint_L','Squint_R','BrowRaise_L','BrowRaise_R','BrowLower_L','BrowLower_R','Smile_L','Smile_R','Frown_L','Frown_R','JawOpen','LipPress','TongueOut','CheekTension_L','CheekTension_R']
FACE_BONES={
 'FaceRoot':((0,0,1.13),(0,0,1.15),'Head'),
 'Jaw':((0,.010,1.115),(0,.010,1.139),'FaceRoot'),
 'LipUpper':((0,-.102,1.117),(0,-.102,1.130),'FaceRoot'),
 'LipLower':((0,-.104,1.105),(0,-.104,1.118),'FaceRoot'),
 'TongueBase':((0,-.033,1.106),(0,-.048,1.106),'Jaw'),
 'TongueTip':((0,-.048,1.106),(0,-.061,1.106),'TongueBase'),
}
for side,sign in [('L',1),('R',-1)]:
    for name,x,y,z in [('Eye',.039,-.026,1.165),('LidUpper',.039,-.044,1.172),('LidLower',.039,-.044,1.158),('BrowInner',.021,-.058,1.188),('BrowOuter',.060,-.043,1.191),('Cheek',.056,-.050,1.142),('MouthCorner',.034,-.095,1.111)]:
        FACE_BONES[name+'_'+side]=((sign*x,y,z),(sign*x,y,z+.012),'FaceRoot')

def smoothstep(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)

def gaussian(x,z,cx,cz,sx,sz):return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)

def face_radius(z):
    profile=[(1.052,.013),(1.067,.034),(1.085,.050),(1.111,.067),(1.140,.082),(1.166,.080),(1.194,.075),(1.222,.064),(1.246,.039),(1.260,.004)]
    for a,b in zip(profile,profile[1:]):
        if a[0]<=z<=b[0]:
            t=smoothstep(a[0],b[0],z);return a[1]*(1-t)+b[1]*t
    return profile[0][1] if z<profile[0][0] else profile[-1][1]

def surface_y(x,z):
    radius=face_radius(z);u=max(-1,min(1,x/max(.004,radius)))
    # Adult cheek planes taper toward the chin, with a short wedge muzzle.
    depth=.045*math.sqrt(max(0,1-u*u))
    y=.009-depth
    y-=.027*gaussian(x,z,0,1.140,.014,.023) # nasal bridge
    y-=.036*math.exp(-(x/.045)**4-((z-1.110)/.021)**4) # mature muzzle wedge
    y-=.008*gaussian(abs(x),z,.053,1.149,.023,.014) # cheek plane
    y+=.012*gaussian(abs(x),z,.050,1.127,.022,.014) # sub-zygomatic hollow
    y-=.013*gaussian(abs(x),z,.039,1.166,.031,.020) # projecting orbital skin surrounds inset eye
    y-=.009*gaussian(abs(x),z,.039,1.183,.030,.009) # brow shelf
    return y

def morph_delta(name,p):
    x,y,z=p;d=Vector((0,0,0));side=1 if name.endswith('_L') else -1
    if y>.008:return d
    eye=gaussian(x,z,side*.039,1.165,.028,.016)
    brow=gaussian(x,z,side*.038,1.188,.033,.016)
    corner=gaussian(x,z,side*.031,1.109,.023,.018)
    if name.startswith('Blink'):
        dz=z-1.165
        if -.017<dz<.021:
            target=1.165+side*.0024*(x-side*.039)/.024
            amount=.998 if abs(x-side*.039)<.026 and abs(dz)<.012 and y<-.035 else eye*.9
            d.z=(target-z)*amount;d.y=-.0015*eye
    elif name.startswith('Squint'):
        d.z=.0045*eye*(1 if z<1.166 else -.20);d.y=-.001*eye
    elif name.startswith('BrowRaise'):d.z=.009*brow;d.y=.001*brow
    elif name.startswith('BrowLower'):d.z=-.006*brow;d.y=-.002*brow
    elif name.startswith('Smile'):d.x=side*.006*corner;d.z=.0065*corner;d.y=.0015*corner
    elif name.startswith('Frown'):d.z=-.0055*corner;d.x=-side*.002*corner
    elif name=='JawOpen':
        weight=(1-smoothstep(1.101,1.128,z))*math.exp(-(x/.064)**4)
        d.z=-.005*weight;d.y=-.002*weight # residual soft-tissue correction; jaw bone supplies opening
    elif name=='LipPress':
        lip=gaussian(x,z,0,1.111,.042,.010);d.z=(1.111-z)*.6*lip;d.y=-.003*lip
    elif name.startswith('CheekTension'):d.y=-.004*gaussian(x,z,side*.051,1.143,.024,.017)
    return d

def add_shapes(obj,names=FACIAL_MORPHS):
    if obj.type!='MESH':return
    obj.shape_key_add(name='Basis')
    for name in names:
        key=obj.shape_key_add(name=name)
        for i,v in enumerate(obj.data.vertices):key.data[i].co=v.co+morph_delta(name,v.co)

def build_face(g):
    own=g['own'];ell=g['ell'];tube=g['tube'];box=g['box'];shade=g['shade'];uv=g['uv'];apply=g['apply']
    SKIN=g['SKIN'];HAIR=g['HAIR'];DARK=g['DARK'];EYE=g['EYE'];INNER=g['INNER']
    mouth=g['material']('Nib_MouthInterior',(.012,.007,.008),'skin',rough=.62)
    tooth=g['material']('Nib_Tooth',(.52,.44,.28),'skin',rough=.35)
    gums=g['material']('Nib_Gum',(.13,.055,.055),'skin',rough=.58)
    tongue=g['material']('Nib_Tongue',(.012,.023,.095),'skin',rough=.46)
    nx=48;nz=64;zmin=1.052;zmax=1.260;verts=[];front={};back={};faces=[]
    eye_boxes=[(7,17,32,36,-1),(31,41,32,36,1)]
    mouth_box=(10,38,17,19)
    def is_boundary(i,j,box):
        x0,x1,z0,z1=box[:4]
        return x0<=j<=x1 and z0<=i<=z1 and (j in [x0,x1] or i in [z0,z1])
    def hole_cell(i,j,box):
        x0,x1,z0,z1=box[:4];return x0<=j<x1 and z0<=i<z1
    for i in range(nz+1):
        z=zmin+(zmax-zmin)*i/nz;r=face_radius(z)
        for j in range(nx+1):
            x=(-1+2*j/nx)*r;p=Vector((x,surface_y(x,z),z))
            for boxspec in eye_boxes:
                if is_boundary(i,j,boxspec):
                    x0,x1,z0,z1,sign=boxspec;u=(j-(x0+x1)/2)/((x1-x0)/2);v=(i-(z0+z1)/2)/((z1-z0)/2);a=math.atan2(v,u)
                    p.x=sign*.039+.024*math.cos(a);p.z=1.165+.0052*math.sin(a)+sign*.0037*math.cos(a)
                    p.y=-.045+.003*abs(math.cos(a))
            if is_boundary(i,j,mouth_box):
                x0,x1,z0,z1=mouth_box;u=(j-(x0+x1)/2)/((x1-x0)/2);v=(i-(z0+z1)/2)/((z1-z0)/2);a=math.atan2(v,u)
                p.x=.036*math.cos(a);p.z=1.1105+.00055*math.sin(a)+.0015*(p.x/.036)**3;p.y=surface_y(p.x,p.z)-.0013
            front[i,j]=len(verts);verts.append(tuple(p))
        for j in range(nx+1):
            if j in [0,nx]:back[i,j]=front[i,j];continue
            x=(-1+2*j/nx)*r;u=x/max(r,.001);y=.009+.056*math.sqrt(max(0,1-u*u))
            back[i,j]=len(verts);verts.append((x,y,z))
    for i in range(nz):
        for j in range(nx):
            if not any(hole_cell(i,j,b) for b in eye_boxes+[mouth_box]):faces.append((front[i,j],front[i,j+1],front[i+1,j+1],front[i+1,j]))
            faces.append((back[i,j],back[i+1,j],back[i+1,j+1],back[i,j+1]))
    for j in range(nx):
        faces.append((front[0,j],back[0,j],back[0,j+1],front[0,j+1]))
        faces.append((front[nz,j],front[nz,j+1],back[nz,j+1],back[nz,j]))
    mesh=bpy.data.meshes.new('Nib connected facial loops');mesh.from_pydata(verts,[],faces);mesh.update()
    head=bpy.data.objects.new('Nib facial surface with eyelid and lip loops',mesh);g['COL'].objects.link(head);own(head,SKIN,'FaceSurface')
    layer=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        for li in polygon.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;layer.data[li].uv=(.5+p.x/.17,(p.z-zmin)/(zmax-zmin))
    subdivision=head.modifiers.new('Facial deformation surface','SUBSURF');subdivision.levels=1;apply(head,subdivision);shade(head)
    add_shapes(head)
    # Eyeballs are recessed behind the continuous skin openings; no floating lids.
    for side,sign in [('L',1),('R',-1)]:
        x=sign*.039
        ell('Recessed eyeball '+side,(x,-.026,1.165),(.023,.018,.014),INNER,'Eye_'+side,seg=48,rings=28)
        ell('Amber iris '+side,(x,-.0431,1.165),(.0096,.002,.0092),EYE,'Eye_'+side,seg=48,rings=24)
        ell('Nib vertical pupil '+side,(x,-.0450,1.165),(.0021,.0008,.0072),DARK,'Eye_'+side,seg=24,rings=16)
        ell('Wet eye glint '+side,(x-sign*.0025,-.0460,1.168),(.0011,.0005,.0012),g['MUZZLE'],'Eye_'+side,seg=12,rings=8)
        # Sparse short brow hairs sit on the shelf rather than forming a sausage.
        for k in range(42):
            t=k/41;xx=sign*(.015+.052*t);zz=1.186+.006*math.sin(t*math.pi*.75);yy=surface_y(xx,zz)-.001
            tube('Fine eyebrow hair '+side,[(xx,yy,zz),(xx+sign*.0018,yy-.0008,zz+.0016),(xx+sign*.003,yy,zz+.0022)],[.00027,.00017,.000025],DARK,'BrowOuter_'+side,sides=3,res=0)
    # Short wedge-shaped leathery nose; nostrils and philtrum are inset details.
    nose=ell('Small triangular Nib nose',(0,-.079,1.130),(.016,.009,.008),INNER,'Head',seg=40,rings=24)
    for v in nose.data.vertices:
        normalized=v.co.z/.008
        v.co.x*=min(1,max(.025,.90+normalized))
    for sign in [-1,1]:ell('Inset nostril',(sign*.008,-.0855,1.130),(.0027,.001,.0018),DARK,'Head',seg=16,rings=12)
    # Oral cavity and individually authored restrained teeth, pending design review.
    ell('Provisional recessed oral cavity',(0,-.025,1.110),(.028,.014,.009),mouth,'Jaw',seg=40,rings=28)
    for upper in [True,False]:
        arc=[]
        for k in range(15):
            x=(k-7)*.0045;z=1.116 if upper else 1.104
            y=max(surface_y(x+dx,z+dz) for dx in [-.0035,.0035] for dz in [-.0035,.0035])+.009
            arc.append((x,y,z))
        tube(('Upper' if upper else 'Lower')+' provisional gum ridge',arc,[.0035]*len(arc),gums,'Head' if upper else 'Jaw',sides=10,res=1)
        for k in range(10):
            x=(k-4.5)*.0057;z=1.113 if upper else 1.107
            y=max(surface_y(x+dx,z+dz) for dx in [-.0026,.0026] for dz in [-.003,.003])+.006
            o=box(('Upper' if upper else 'Lower')+' provisional tooth',(x,y,z),(.0052,.0045,.006 if upper else .005),tooth,'Head' if upper else 'Jaw',.001)
            o.rotation_euler[2]=-x*3.5
    tongue_obj=tube('Canonical dark blue Nib tongue',[(0,-.030,1.106),(0,-.040,1.106),(0,-.050,1.106),(0,-.060,1.106)],[(.004,.008),(.004,.012),(.0035,.012),(.0025,.007)],tongue,'TongueBase',sides=24,res=2)
    tongue_obj.shape_key_add(name='Basis');key=tongue_obj.shape_key_add(name='TongueOut')
    for i,v in enumerate(tongue_obj.data.vertices):
        t=smoothstep(.033,.060,-v.co.y)
        key.data[i].co=v.co+Vector((0,-.042*t,.003*math.sin(t*math.pi)))
    # Fine chin tuft replaces the solid cone from rejected passes.
    for k in range(70):
        angle=k*2.39996;r=.012*math.sqrt((k+.5)/70);x=r*math.cos(angle);z=1.076-abs(x)*.12;y=surface_y(x,z)-.001
        tube('Fine chin fur',[(x,y,z),(x*.75,y+.001,z-.010),(x*.5,y+.005,z-.022)],[.00055,.00030,.000025],HAIR,'Jaw',sides=3,res=0)
    return {'head':head,'bones':FACE_BONES,'morphs':FACIAL_MORPHS,'tongue':tongue_obj,'mouthStatus':'Dark blue tongue approved; interior anatomy and expressions provisional for review.'}

def build_deformation_contract():
    drivers=[]
    def add(morph,bone,channel,start,end,kind='facial'):
        drivers.append({'morph':morph,'bone':bone,'channel':channel,'start':start,'end':end,'maxWeight':1,'kind':kind})
    for s in ['L','R']:
        for morph,bone,distance in [('Blink','LidUpper',.007),('Squint','LidLower',.004),('BrowRaise','BrowOuter',.009),('BrowLower','BrowInner',.006),('Smile','MouthCorner',.008),('CheekTension','Cheek',.005)]:add(morph+'_'+s,bone+'_'+s,'translationDistanceMeters',0,distance)
        add('Frown_'+s,'MouthCorner_'+s,'rotationMagnitudeDegrees',0,12)
        for morph,bone,start,end in [('ShoulderRaise','UpperArm',25,90),('ElbowFlex','LowerArm',30,95),('HipFlex','Thigh',20,75),('KneeFlex','Shin',25,100)]:add('Corrective_'+morph+'_'+s,bone+'_'+s,'rotationMagnitudeDegrees',start,end,'body')
    add('JawOpen','Jaw','rotationMagnitudeDegrees',0,24)
    add('LipPress','LipUpper','translationDistanceMeters',0,.003)
    add('TongueOut','TongueTip','translationDistanceMeters',0,.03)
    return {'schemaVersion':1,'faceRoot':'FaceRoot','drivers':drivers,'personality':'Playful, technically capable adult engineer; physically weak and somewhat cowardly. Cautious glances and flinches coexist with cheeky tongue gestures.','tongueColor':'dark blue','mouthAnatomyStatus':'provisional; expression-sheet review required','coordinateConvention':'All drivers use magnitude of local transform delta from bind. Translation values are meters; angles are degrees. Never interpret raw imported Euler axes.'}
