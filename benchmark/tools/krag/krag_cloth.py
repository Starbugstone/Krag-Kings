"""Localized cloth settling against low resolution collision stand-ins.
Only the scarf is simulated; collider geometry is discarded after applying the cloth result.
"""
import bpy,math

def settle(o):
    scene=bpy.context.scene;old_frame=scene.frame_current;colliders=[]
    for center,scale in [((0,.025,1.765),(.147,.135,.20)),((0,.014,1.48),(.338,.202,.270)),((0,.07,1.66),(.270,.152,.119))]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=center);proxy=bpy.context.object;proxy.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);proxy.name='Temporary scarf collision surface';proxy.hide_render=True
        proxy.modifiers.new('Scarf cloth collision','COLLISION');proxy.collision.thickness_outer=.003;proxy.collision.cloth_friction=8;colliders.append(proxy)
    anchors=o.vertex_groups.new(name='Scarf anchored neckline')
    # Rear neckline/shoulder tuck holds the scarf; front folds are allowed to hang naturally.
    for vertex in o.data.vertices:
        if vertex.index<128 and vertex.co.y>.005:anchors.add([vertex.index],1,'REPLACE')
        elif vertex.index<256 and vertex.co.y>.07:anchors.add([vertex.index],.65,'REPLACE')
    bpy.context.view_layer.objects.active=o;cloth=o.modifiers.new('Settled hanging woven fabric','CLOTH');s=cloth.settings;s.quality=8;s.mass=.22;s.tension_stiffness=18;s.compression_stiffness=18;s.shear_stiffness=10;s.bending_stiffness=.25;s.tension_damping=7;s.compression_damping=7;s.shear_damping=7;s.air_damping=5;s.vertex_group_mass=anchors.name;s.pin_stiffness=1
    cloth.collision_settings.use_collision=True;cloth.collision_settings.distance_min=.004;cloth.collision_settings.use_self_collision=False;cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=48
    for frame in range(1,49):scene.frame_set(frame);bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=cloth.name)
    o['cloth_simulation']='48 frames; pinned rear neckline, physical gravity and low resolution torso/neck colliders'
    for proxy in colliders:bpy.data.objects.remove(proxy,do_unlink=True)
    scene.frame_set(old_frame)

def wrapped(c):
    """One continuous scarf strip winds into uneven deep-U layers, with soft rolled folds."""
    mesh,cloth=c['mesh'],c['cloth'];vs=[];fs=[];longitudinal=361;across=25;turns=2.35
    for i in range(longitudinal):
        turn=turns*i/(longitudinal-1);a=math.pi/2+2*math.pi*turn;front=max(0,-math.sin(a));side=abs(math.cos(a))
        centre_radius=.151+.022*turn+.068*front+.012*math.sin(2*a+.85*turn)
        centre_z=1.864-.032*turn-front*(.193+.009*turn)+.019*math.cos(a+.9*turn)+.009*math.sin(3*a+.7*turn)
        for j in range(across):
            u=j/(across-1)-.5;gather=.009*math.sin(5*a+4*u+.6*turn)*side**2
            radius=centre_radius+.012*math.cos(2*math.pi*u)+.005*math.sin(6*math.pi*u+a)*math.sin(math.pi*(u+.5))
            radius+=.010*front*math.sin(3*a+2.8*turn+2*u)
            z=centre_z+u*(.113+.029*math.sin(a+.4*turn))+.008*math.sin(4*math.pi*u+.6*a)+gather
            vs.append((radius*math.cos(a),.019+radius*math.sin(a),z))
    for i in range(longitudinal-1):
        for j in range(across-1):k=i*across+j;fs.append((k,k+across,k+across+1,k+1))
    o=mesh('Continuous layered desert scarf wrap',vs,fs,cloth,'Scarf','Chest');solid=o.modifiers.new('Woven scarf edge thickness','SOLIDIFY');solid.thickness=.003;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=solid.name)
    o['construction']='Continuous 2.35-turn textile strip; deep front sag and irregular rolled folds; unaccepted review geometry'
    return o
