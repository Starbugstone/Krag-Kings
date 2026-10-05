"""Create the identical, meter-scale dune mesh and sand PBR maps for both engines.
Run with Blender --background --python this_file.py. No external asset dependencies.
"""
import bpy
import math
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'benchmark/shared/environment'
SOURCE = ROOT / 'benchmark/art/environment'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def height(x, y):
    foreground=.8 + 1.1*math.sin(.105*x+.035*y) + .65*math.sin(.055*x-.145*y) + .30*math.cos(.22*x+.13*y)
    # The central comparison surface is unchanged. A low-cost distant mesh carries
    # the desert to the horizon so orbiting does not expose a square terrain edge.
    t=max(0,min(1,(max(abs(x),abs(y))-40)/90))
    blend=t*t*(3-2*t)
    distant=4+7*math.sin(.019*x+.009*y)+4*math.sin(.012*x-.023*y)
    return foreground+blend*distant

foreground_n = 193
outer=[42,45,49,54,60,68,78,90,105,123,145,172,205,245,295,355,430,520,630,760]
coordinates=[-v for v in reversed(outer)]+[-40+80*i/(foreground_n-1) for i in range(foreground_n)]+outer
n=len(coordinates)
verts = []
for y in coordinates:
    for x in coordinates:
        verts.append((x, y, height(x, y)))
faces = [(j*n+i, j*n+i+1, (j+1)*n+i+1, (j+1)*n+i) for j in range(n-1) for i in range(n-1)]
mesh = bpy.data.meshes.new('Dunes_Surface')
mesh.from_pydata(verts, [], faces)
mesh.update()
uv = mesh.uv_layers.new(name='UVMap')
for polygon in mesh.polygons:
    polygon.use_smooth = True
    for loop_index in polygon.loop_indices:
        co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
        uv.data[loop_index].uv = ((co.x+40)/4, (co.y+40)/4)
obj = bpy.data.objects.new('Dunes', mesh)
bpy.context.collection.objects.link(obj)

# Seeded analytic material generation: wind ridges, fine grains, restrained mineral flecks.
# The source algorithm is reproducible and does not use concept pixels as baked shading.
size = 2048
u, v = np.meshgrid(np.arange(size,dtype=np.float32)/size, np.arange(size,dtype=np.float32)/size)
rng = np.random.default_rng(734)
grain = rng.random((size,size), dtype=np.float32)
low = .42*np.sin(2*np.pi*(u*3+v*2)) + .23*np.cos(2*np.pi*(u*7-v*4))
phase = 2*np.pi*(v*23 + .24*np.sin(2*np.pi*u*2) + .11*np.sin(2*np.pi*u*5))
ridges = (.5 + .5*np.cos(phase))**2
fine = .18*np.sin(2*np.pi*(u*91+v*127))
h = .002*ridges + .00022*grain + .00011*fine
dx = (np.roll(h,-1,1)-np.roll(h,1,1))/(8/size)
dy = (np.roll(h,-1,0)-np.roll(h,1,0))/(8/size)
normal = np.dstack((-dx,-dy,np.ones_like(dx)))
normal /= np.linalg.norm(normal,axis=2,keepdims=True)
shade = .97 + .045*low + .020*(grain-.5) + .016*(ridges-.5)
base = np.clip(np.dstack([.67*shade,.505*shade,.319*shade]),0,1)
flecks = grain>.996
base[flecks] *= .68
rough = np.clip(.84+.05*(grain-.5)+.015*low,0,1)

def image_file(name, values, color=False):
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    img.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    if values.ndim == 2: values=np.repeat(values[:,:,None],3,axis=2)
    rgba = np.concatenate([values,np.ones((size,size,1),dtype=np.float32)],axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw=str(OUT/(name+'.png'))
    img.file_format='PNG'
    img.save()
    return img

color_img=image_file('Sand_BaseColor',base,True)
normal_img=image_file('Sand_Normal',normal*.5+.5)
rough_img=image_file('Sand_Roughness',rough)
mask_img=image_file('Sand_MaskHDRP',np.dstack((np.zeros_like(rough),np.ones_like(rough),np.ones_like(rough))))
# HDRP mask: metallic R=0, AO G=1, detail B=1, smoothness A=1-roughness.
mask_pixels=np.dstack((np.zeros_like(rough),np.ones_like(rough),np.ones_like(rough),1-rough)).astype(np.float32)
mask_img.pixels.foreach_set(mask_pixels.ravel()); mask_img.save()

mat=bpy.data.materials.new('Sand')
mat.use_nodes=True
nodes=mat.node_tree.nodes; links=mat.node_tree.links
bsdf=nodes.get('Principled BSDF')
for img,input_name in [(color_img,'Base Color'),(rough_img,'Roughness')]:
    tex=nodes.new('ShaderNodeTexImage');tex.image=img
    links.new(tex.outputs['Color'],bsdf.inputs[input_name])
tex=nodes.new('ShaderNodeTexImage');tex.image=normal_img
normal_node=nodes.new('ShaderNodeNormalMap')
links.new(tex.outputs['Color'],normal_node.inputs['Color'])
links.new(normal_node.outputs['Normal'],bsdf.inputs['Normal'])
obj.data.materials.append(mat)

bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Dunes.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False,path_mode='RELATIVE')

# Persist actual editable source with relative texture paths.
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'Dunes.blend'))
for img in [color_img,normal_img,rough_img,mask_img]:
    img.filepath=bpy.path.relpath(img.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'Dunes.blend'))
(OUT/'manifest.json').write_text(json.dumps({'mesh':'Dunes.fbx','units':'meters','grid':n,'extent_m':[-760,760], 'comparison_extent_m':[-40,40],'foreground_grid':foreground_n,'vertices':len(verts),'triangles':len(faces)*2,'uv_tile_m':4,'height_blender_xy':'.8+1.1*sin(.105*x+.035*y)+.65*sin(.055*x-.145*y)+.30*cos(.22*x+.13*y)','height_formula_scope':'central comparison area; distant dunes smoothly added outside 40 meters','material':'Sand','baseColor':'Sand_BaseColor.png','normalOpenGL':'Sand_Normal.png','roughness':'Sand_Roughness.png','hdrpMask':'Sand_MaskHDRP.png'},indent=2)+'\n')
print('DUNES_EXPORT_OK', str(OUT), len(verts), len(faces)*2)
