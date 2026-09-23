"""A subdivided persistent channel surface; deformation is shader-only at runtime."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
nx,ny=48,132;vs=[];fs=[];colors=[]
for j in range(ny+1):
    y=-3.91+7.82*j/ny
    for i in range(nx+1):
        x=-1.41+2.82*i/nx;edge=min(1.41-abs(x),3.91-abs(y));wet=min(1,max(0,edge/.07))
        vs.append((x,y,.043+.002*math.sin(x*4.1+y*2.7)*wet))
        colors.append((wet,.5+.5*math.sin(x*4.3+y*2.1),0,1))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
mesh=bpy.data.meshes.new('SM_DungeonPusChannel');mesh.from_pydata(vs,[],fs);mesh.update()
uv=mesh.uv_layers.new(name='UVMap');color=mesh.color_attributes.new(name='FluidCoverage',type='FLOAT_COLOR',domain='CORNER')
mat=bpy.data.materials.new('DP_Pus');mesh.materials.append(mat)
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:
        vi=mesh.loops[li].vertex_index;co=mesh.vertices[vi].co;uv.data[li].uv=(co.x,co.y);color.data[li].color=colors[vi]
obj=bpy.data.objects.new('SM_DungeonPusChannel',mesh);bpy.context.scene.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_DungeonPusChannel.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonPusChannel.blend'))
(OUT/'channel.json').write_text(json.dumps({'mesh':'SM_DungeonPusChannel','fbx':str(OUT/'SM_DungeonPusChannel.fbx'),'location_cm':[2350,-3600,39],'half_size_cm':[141,391],'liquid_depth_cm':4.3,'damage_type':'/Script/FPSGAME.CorrosivePusDamage','damage_per_pulse':8,'interval':.5},indent=2),encoding='utf-8')
