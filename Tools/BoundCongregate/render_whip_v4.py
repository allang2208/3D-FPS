"""Diagnostic views using exact component-space skin deltas from the UE proxy."""
from pathlib import Path
import bpy,json,sys,math
from mathutils import Matrix,Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BoundCongregate_TentacleV4.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.animation_data.action=None
for ob in list(scene.objects):
    if ob.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.name.endswith('_SimulationProxy'):ob.hide_render=True
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=800;scene.render.resolution_y=560;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=8
scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('TentacleDiagnostic');scene.world.use_nodes=True
nodes=scene.world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');out=nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],out.inputs['Surface']);bg.inputs[0].default_value=(.18,.20,.23,1);bg.inputs[1].default_value=.45
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));floor=bpy.context.object
mat=bpy.data.materials.new('ReviewFloor');mat.diffuse_color=(.105,.12,.135,1);floor.data.materials.append(mat)
target=Vector((0,0,1.65))
for name,p,power,size in [('Key',(-3,-5,7),1500,4),('Fill',(4,-2,4),1000,3),('Rim',(1,4,5),1200,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=p;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.ortho_scale=10.;cam.location=(7,-4,3.5);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
poses=json.loads((ROOT/'ue_attack_poses.json').read_text())['poses']
convert=Matrix.Diagonal(Vector((.01,-.01,.01,1)));inverse=convert.inverted()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
selected=[59,125,133,145,161,184]
if '--all-poses' in sys.argv:selected=list(range(45,188,3))
for pose in poses:
    if pose['frame'] not in selected:continue
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    matrices={}
    for bone in pose['bones']:
        a=bone['delta'];m=Matrix([a[i:i+4] for i in range(0,16,4)]).transposed()
        if bone['name'] in rest:matrices[bone['name']]=convert@m@inverse@rest[bone['name']]
    for pb in rig.pose.bones:
        if pb.name not in matrices:continue
        parent=pb.parent
        parent_rest=rest[parent.name] if parent else Matrix.Identity(4)
        parent_pose=matrices.get(parent.name,parent_rest) if parent else Matrix.Identity(4)
        local_rest=parent_rest.inverted()@rest[pb.name]
        pb.matrix_basis=local_rest.inverted()@parent_pose.inverted()@matrices[pb.name]
    bpy.context.view_layer.update()
    scene.render.filepath=str(ROOT/f"pose_{pose['frame']:03}.png");bpy.ops.render.render(write_still=True)
print('V4_ACTUAL_UE_POSE_RENDER_COMPLETE',flush=True)
