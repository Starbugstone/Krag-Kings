"""Content-addressed PBR tile reuse; graph/source changes invalidate cached maps."""
import bpy,json,hashlib
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def value(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    try:return [float(x) for x in v]
    except Exception:return str(v)
def recipe(material):
    nodes=[]
    for n in material.node_tree.nodes:
        item={'name':n.name,'type':n.bl_idname,'inputs':[(i.identifier,value(i.default_value)) for i in n.inputs if hasattr(i,'default_value')]}
        for name in ['operation','blend_type','feature','distance','noise_dimensions','voronoi_dimensions','normalize','projection','projection_blend','extension','interpolation','wave_type','bands_direction','rings_direction','convert_from','convert_to','vector_type','space','mode','use_clamp','data_type','factor_mode','interpolation_type','domain']:
            if hasattr(n,name):item[name]=value(getattr(n,name))
        if n.type=='TEX_IMAGE' and n.image:
            path=Path(bpy.path.abspath(n.image.filepath));item['image']={'sha256':sha(path),'colorSpace':n.image.colorspace_settings.name}
        if hasattr(n,'color_ramp'):
            r=n.color_ramp;item['ramp']={'interpolation':r.interpolation,'colorMode':r.color_mode,'elements':[(e.position,list(e.color)) for e in r.elements]}
        nodes.append(item)
    links=sorted((x.from_node.name,x.from_socket.identifier,x.to_node.name,x.to_socket.identifier) for x in material.node_tree.links)
    data={'nodes':sorted(nodes,key=lambda x:x['name']),'links':links,'tileMeters':1,'normalConvention':'OpenGL','normalSpace':'TANGENT','pngAlpha':False,'recipeSchema':1,'blenderVersion':bpy.app.version_string,'baseNormalResolution':2048 if material.name=='Krag_SandstoneSkin' else (256 if material.name in ['Krag_Recess','Krag_Amber','Krag_EyeWhite','Krag_Ivory'] else 1024),'maskResolution':32 if material.name in ['Krag_Recess','Krag_Amber','Krag_EyeWhite','Krag_Ivory'] else 128,'bakeSamples':4}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
def valid(entry,recipe_hash,directory):
    if not entry or entry.get('recipeHash')!=recipe_hash:return False
    for ch,path in entry['maps'].items():
        file=Path(directory)/path
        if not file.is_file() or sha(file)!=entry['mapHashes'][ch]:return False
    return True
