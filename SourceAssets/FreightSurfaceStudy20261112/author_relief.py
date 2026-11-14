from pathlib import Path
import bpy, numpy as np
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
grid=np.load(ROOT/'relief-grid.npz')
a,h=grid['alpha'],grid['depth'];n=len(a)
verts=[];uvs=[];faces=[];lookup={}
def vid(i,j):
    key=(i,j)
    if key not in lookup:
        u,v=i/(n-1),j/(n-1)
        lookup[key]=len(verts)
        verts.append(((.5-u)*.94,h[j,i]*.01,(.5-v)*.94))
        uvs.append((u,1-v))
    return lookup[key]
for j in range(n-1):
    for i in range(n-1):
        if np.max(a[j:j+2,i:i+2])<.10:continue
        faces.append(tuple(vid(x,y) for x,y in [(i,j),(i,j+1),(i+1,j+1),(i+1,j)]))
mesh=bpy.data.meshes.new('SM_PackingConcreteRelief');mesh.from_pydata(verts,[],faces);mesh.update()
ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
mesh.materials.append(bpy.data.materials.new('RegisteredScan'))
uv=mesh.uv_layers.new(name='UVMap')
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(ROOT/(mesh.name+'.fbx')),use_selection=True,axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
