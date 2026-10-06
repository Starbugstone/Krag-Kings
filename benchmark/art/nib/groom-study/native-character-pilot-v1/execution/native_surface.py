"""Native groom attachment against exact isolated skin copies.

No scene side effects on import. Original mesh geometry, UVs, keys and weights
remain unchanged. A private per-polygon UV atlas avoids ambiguous mirrored UV
roots in Blender's native Deform Curves on Surface node.
"""
import bisect, math, random
import bpy
import numpy as np
from mathutils import Vector


def surface_copy(source, collection):
    target=source.copy();target.data=source.data.copy();target.name='Native groom support '+source.name
    collection.objects.link(target);target.hide_render=True;target.hide_set(False)
    target['native_groom_support']=True;target['source_surface']=source.name
    mesh=target.data;uv=mesh.uv_layers.new(name='NativeGroomAttachment')
    side=math.ceil(math.sqrt(len(mesh.polygons)))
    for poly in mesh.polygons:
        ids=list(poly.vertices);points=np.asarray([mesh.vertices[i].co[:]for i in ids],float)
        normal=np.asarray(poly.normal[:]);drop=int(np.argmax(abs(normal)));plane=np.delete(points,drop,axis=1)
        low=plane.min(axis=0);span=plane.max(axis=0)-low;scale=float(span.max())
        if scale<=1e-10:raise RuntimeError('Degenerate attachment polygon '+str((source.name,poly.index)))
        local=(plane-low)/scale;local+=(1-span/scale)*.5
        cell=np.array((poly.index%side,poly.index//side),float)
        values=(cell+.08+.84*local)/side
        for loop,value in zip(poly.loop_indices,values):uv.data[loop].uv=value
    rest=mesh.attributes.get('rest_position') or mesh.attributes.new('rest_position','FLOAT_VECTOR','POINT')
    xyz=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',xyz);rest.data.foreach_set('vector',xyz)
    # Mesh.copy retains the shape-key animation drivers; do not replace them.
    if source.data.shape_keys:
        if not mesh.shape_keys or len(mesh.shape_keys.key_blocks)!=len(source.data.shape_keys.key_blocks):
            raise RuntimeError('Attachment duplicate lost shape targets')
        a=source.data.shape_keys.animation_data;b=mesh.shape_keys.animation_data
        if (len(a.drivers)if a else 0)!=(len(b.drivers)if b else 0):raise RuntimeError('Attachment duplicate lost shape drivers')
    mesh.update();return target


class Sampler:
    def __init__(self, source, support, selector):
        self.source=source;self.support=support;mesh=source.data;mesh.calc_loop_triangles()
        source_attr=mesh.attributes.get('nib_source_position');self.rows=[];self.cumulative=[];self.total=0.
        matrix=source.matrix_world;normals=matrix.to_3x3().inverted().transposed()
        for index,tri in enumerate(mesh.loop_triangles):
            ids=list(tri.vertices);p=[matrix@mesh.vertices[i].co for i in ids]
            n=[(normals@mesh.vertices[i].normal).normalized()for i in ids]
            s=[Vector(source_attr.data[i].vector)if source_attr else p[j]for j,i in enumerate(ids)]
            center=sum(p,Vector())/3;normal=sum(n,Vector()).normalized();hint=sum(s,Vector())/3
            if not selector(center,normal,hint):continue
            area=(p[1]-p[0]).cross(p[2]-p[0]).length*.5
            if area<=1e-13:continue
            self.total+=area;self.cumulative.append(self.total)
            self.rows.append((index,tri.polygon_index,ids,list(tri.loops),p,n,s))
        if not self.rows:raise RuntimeError('No native groom support region on '+source.name)

    def sample(self, count, seed, root_filter=None):
        rng=random.Random(seed);samples=[];attempts=0;uv=self.support.data.uv_layers['NativeGroomAttachment']
        source_uv=self.source.data.uv_layers.active
        while len(samples)<count:
            attempts+=1
            if attempts>count*30:raise RuntimeError('Native root region cannot fit requested valid samples')
            row=self.rows[bisect.bisect_left(self.cumulative,rng.random()*self.total)]
            index,polygon,ids,loops,p,n,s=row
            a=math.sqrt(rng.random());b=rng.random();w=np.array((1-a,a*(1-b),a*b),float)
            point=sum((v*float(t)for v,t in zip(p,w)),Vector())
            if root_filter and not root_filter(point):continue
            normal=sum((v*float(t)for v,t in zip(n,w)),Vector()).normalized()
            hint=sum((v*float(t)for v,t in zip(s,w)),Vector())
            attachment=sum((uv.data[j].uv*float(t)for j,t in zip(loops,w)),Vector((0,0)))
            original_uv=sum((source_uv.data[j].uv*float(t)for j,t in zip(loops,w)),Vector((0,0)))if source_uv else Vector((0,0))
            weights={}
            for vertex,t in zip(ids,w):
                for group in self.source.data.vertices[vertex].groups:
                    name=self.source.vertex_groups[group.group].name
                    weights[name]=weights.get(name,0.)+float(t)*group.weight
            weights={k:v for k,v in weights.items()if v>1e-8};total=sum(weights.values())
            if abs(total-1)>2e-5:raise RuntimeError('Native root skin weights do not sum to one')
            weights={k:v/total for k,v in weights.items()}
            samples.append({'point':list(point),'normal':list(normal),'sourceHint':list(hint),
                            'triangle':index,'polygon':polygon,'vertices':ids,'barycentric':w.tolist(),
                            'attachmentUv':list(attachment),'sourceUv':list(original_uv),'weights':weights})
        return samples,{'areaMetersSquared':self.total,'eligibleTriangles':len(self.rows),'rootSamples':count,'attempts':attempts}


def native_deformer(curves, support):
    curves.data.surface=support;curves.data.surface_uv_map='NativeGroomAttachment'
    group=bpy.data.node_groups.new('Native surface deformation '+curves.name,'GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    start=group.nodes.new('NodeGroupInput');end=group.nodes.new('NodeGroupOutput')
    deform=group.nodes.new('GeometryNodeDeformCurvesOnSurface')
    group.links.new(start.outputs['Geometry'],deform.inputs['Curves'])
    group.links.new(deform.outputs['Curves'],end.inputs['Geometry'])
    modifier=curves.modifiers.new('Native skin and ear attachment','NODES');modifier.node_group=group
    return modifier
