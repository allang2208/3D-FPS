"""Local source comparison limited to the reported right-arm strike phases."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;args=sys.argv[sys.argv.index('--')+1:];tag=args[0]
data=json.loads((O/('source_pose_frames.json' if tag=='before' else 'authored_poses.json')).read_text())['base']
if tag=='probe':data={'49':json.loads((O/'grip_probe.json').read_text())['pose']}
if tag=='preview':data=json.loads((O/'preview_poses.json').read_text())
cal=json.loads((O.parent/'LeftArmR5/author_space.json').read_text());camera=json.loads((O.parent/'LeftArmR5/camera_basis.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O.parents[1]/'Super90LoaderR23_20261010/Super90_Speedloader_R23.blend'),use_scripts=False)
rig=bpy.data.objects['SK_Super90'];rig.animation_data_clear();scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones};I=Matrix.Identity(4)
lr={n:rest.get(parents[n],I).inverted()@m for n,m in rest.items()}
keep={'SK_Super90','Super90_V7_M4_BareArmsV6','Super90_body','Super90_bolt','Super90_loading_gate','Super90_trigger','SM_Super90_LoaderGuide'}
for ob in scene.objects:
    ob.hide_render=ob.name not in keep;ob.hide_set(ob.name not in keep)
    if ob.type=='MESH' and ob.name in keep:
        material=bpy.data.materials.new('Source_'+ob.name);material.diffuse_color=(.66,.47,.38,1) if 'BareArms' in ob.name else (.07,.085,.10,1)
        ob.data.materials.clear();ob.data.materials.append(material)
        for polygon in ob.data.polygons:polygon.material_index=0
cl=Matrix(camera['linear']);co=Vector(camera['origin_m']);eye=cl.inverted()@(-co)
forward=(cl.inverted()@Vector((1,0,0))).normalized();right=(cl.inverted()@Vector((0,1,0))).normalized();up=right.cross(forward).normalized()
camd=bpy.data.cameras.new('ReportedRightArmSource');camd.sensor_fit='HORIZONTAL';camd.angle=math.radians(112);camd.clip_start=.001
cam=bpy.data.objects.new('ReportedRightArmSource',camd);scene.collection.objects.link(cam)
cam.matrix_world=rig.matrix_world@Matrix.LocRotScale(eye,Matrix((right,up,-forward)).transposed().to_quaternion(),Vector((1,1,1)));scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1200;scene.render.resolution_y=675;scene.render.resolution_percentage=100
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_shadows=False;sh.background_type='VIEWPORT';sh.background_color=(.07,.08,.10)
out=O/'Frames'/tag;out.mkdir(parents=True,exist_ok=True)
for frame in ([49] if tag=='probe' else [27,40,49]):
    p={n:Matrix(m) for n,m in (data[str(frame)] if isinstance(data,dict) else data[frame]).items()}
    for bone in rig.pose.bones:bone.matrix_basis=lr[bone.name].inverted()@p.get(parents[bone.name],I).inverted()@p[bone.name]
    bpy.context.view_layer.update();scene.render.filepath=str(out/(str(frame)+'.png'));bpy.ops.render.render(write_still=True)
