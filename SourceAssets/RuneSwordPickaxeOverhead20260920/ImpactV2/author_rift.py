"""Build a dedicated top-to-bottom optical ribbon for the overhead chop."""
import bpy,math,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[];uvs=[];faces=[];segments=96;across=8
for i in range(segments+1):
    u=i/segments
    half_width=.045+.145*math.sin(math.pi*u)**.7
    for j in range(across+1):
        v=j/across
        # Blender +Y is the view's forward axis after the sword import basis.
        # Keep every row centred; UV.x explicitly reveals from top to bottom.
        verts.append(((2*v-1)*half_width,.88,.82-1.70*u));uvs.append((u,v))
for i in range(segments):
    for j in range(across):
        a=i*(across+1)+j;faces.append((a,a+1,a+across+2,a+across+1))
mesh=bpy.data.meshes.new('OverheadVerticalRift');mesh.from_pydata(verts,[],faces);mesh.update()
ob=bpy.data.objects.new('SM_RuneRift_Overhead',mesh);bpy.context.scene.collection.objects.link(ob)
uv=mesh.uv_layers.new(name='UVMap')
for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(P/'SM_RuneRift_Overhead.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Overhead_VerticalRift_Editable.blend'))
(P/'rift_authoring.json').write_text(json.dumps({'height_m':1.70,'maximum_width_m':.38,'depth_m':.88,
    'reveal':'UV.x from top to bottom','runtime_material':'WristRiftV3/M_RuneRift','collision':False,
    'runtime_tested':False},indent=2),encoding='utf-8')
print('OVERHEAD_VERTICAL_RIFT_AUTHORED',flush=True)
