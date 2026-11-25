"""Create the editable head, native body fitting reference and scalp-fitted low bun."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parents[4]
out=root/'SourceAssets/HillsVillageStable/StablemasterR2'
nun=root/'SourceAssets/ChapelNun20261115'
def read(p):return json.loads(p.read_bytes())
native=read(nun/'ProductionR1/Inputs/native_head.json')
original=read(nun/'FaceOriginalRestoreR6/Authored/head.json')
body=read(root/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/SKM_MHC_Kaitlin_BodyMesh.json')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.preferences.filepaths.save_version=0
def surface(name,d):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(d['positions'],[],[t[::-1] for t in d['triangles']]);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for p in mesh.polygons:p.use_smooth=True
    return ob
head=surface('Stablemaster head',native);me=head.data
p=np.array(native['positions']);q=p.copy()
rect=lambda a,b,x:np.clip((x-a)/(b-a),0,1)**2*(3-2*np.clip((x-a)/(b-a),0,1))
falloff=rect(144,146,p[:,2])*rect(1.5,4.,p[:,1])
# In the capture, actual dynamics sections 1,3,4 contain teeth and globes.
tris=np.asarray(native['triangles']);m=np.asarray(native['triangle_materials'])
rigid=np.unique(tris[np.isin(m,[1,3,4])]);falloff[rigid]=0
for brush in read(out/'sculpt.json')['brushes']:
    d=((p-brush['center'])/brush['radius']);r2=np.sum(d*d,axis=1)
    q+=(np.exp(-r2)*(r2<10)*falloff)[:,None]*brush['offset']
head.shape_key_add(name='Kaitlin native');key=head.shape_key_add(name='Stablemaster R2');key.data.foreach_set('co',q.astype('f').ravel());key.value=1.
uv=me.uv_layers.new(name='Native skin UV')
for poly,tex in zip(me.polygons,native['uv']):
    for li,(u,v) in zip(poly.loop_indices,tex[::-1]):uv.data[li].uv=(u,1-v)
for b in native['bones']:head.vertex_groups.new(name=b['name'])
for vi,row in enumerate(native['weights']):
    for bi,weight in row:head.vertex_groups[bi].add([vi],weight,'REPLACE')
for name,color in [('Skin',(.43,.26,.18,1)),('Teeth',(.76,.70,.61,1)),('Oral',(.28,.09,.07,1)),('Iris L',(.12,.21,.19,1)),('Iris R',(.12,.21,.19,1)),('Shell',(.15,.12,.10,1)),('Lashes',(.04,.023,.02,1)),('Tearline',(.38,.21,.17,1)),('Cartilage',(.47,.26,.21,1))]:
    mat=bpy.data.materials.new(name);mat.diffuse_color=color;me.materials.append(mat)
me.polygons.foreach_set('material_index',m.astype('i'))
mat=me.materials[0];mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF')
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(out/'T_Stablemaster_Face_BC.png'));tex.image.pack()
mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.48
ref=surface('Kaitlin body fitting reference',body);ref.hide_set(True);ref.hide_render=True
center=np.array([0.,.1,158.9])
def radii(data,points,slots):
    tree=BVHTree.FromPolygons([Vector(v) for v in points],[t for t,i in zip(data['triangles'],data['triangle_materials']) if i in slots],all_triangles=True)
    table=np.empty((96,193),np.float32)
    for j,phi in enumerate(np.linspace(.001,2.65,len(table))):
        for i,theta in enumerate(np.linspace(-math.pi,math.pi,193)):
            direction=Vector((math.sin(phi)*math.sin(theta),math.sin(phi)*math.cos(theta),math.cos(phi)))
            hit=tree.ray_cast(Vector(center),direction,40)[0]
            if hit is None:hit=tree.find_nearest(Vector(center)+direction*8)[0]
            table[j,i]=(hit-Vector(center)).length
    return table
diff=radii(native,q,{0})-radii(original,original['positions'],{0,2})
def adapt(a):
    v=a-center;d=np.linalg.norm(v,axis=-1);n=v/np.maximum(d[...,None],.001)
    t=(np.arctan2(n[...,0],n[...,1])+math.pi)*(192/(2*math.pi))
    f=np.clip(np.arccos(np.clip(n[...,2],-1,1))*(95/2.65),0,94.999)
    i=np.clip(t.astype(int),0,191);j=f.astype(int);x=t-i;y=f-j
    delta=diff[j,i]*(1-x)*(1-y)+diff[j,i+1]*x*(1-y)+diff[j+1,i]*(1-x)*y+diff[j+1,i+1]*x*y
    return a+n*delta[...,None]
hairmat=bpy.data.materials.new('Espresso riding bun');hairmat.diffuse_color=(.025,.014,.009,1)
curves=bpy.data.curves.new('Scalp comb and riding bun','CURVE');curves.dimensions='3D';curves.resolution_u=1
ob=bpy.data.objects.new('Stablemaster_LowBun',curves);bpy.context.collection.objects.link(ob)
curves.materials.append(hairmat);ob['groom_group_id']=0
for part,stride in [('Core',2),('Loose',1)]:
    data=np.load(nun/'HairNativeCombR9/Authored'/('Nun_LowBun_'+part+'_R5_points.npy'),mmap_mode='r')[::stride,::2]
    for block in np.array_split(data,max(1,len(data)//400+1)):
        for strand in adapt(block):
            spline=curves.splines.new('POLY');spline.points.add(len(strand)-1)
            spline.points.foreach_set('co',np.c_[strand,np.ones(len(strand))].astype('f').ravel())
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.wm.alembic_export(filepath=str(out/'Stablemaster_LowBun.abc'),selected=True,start=1,end=1,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Stablemaster.blend'),compress=True)
