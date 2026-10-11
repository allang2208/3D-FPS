import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
args=sys.argv[sys.argv.index('--')+1:];tag,branch=args[:2];frames=[int(x) for x in args[2:]]
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90LoaderR21_20261010/Super90_Speedloader_R21.blend'))
rig=bpy.data.objects['SK_Super90'];rig.animation_data_clear();scene=bpy.context.scene
if tag!='source' and (O/'bind_surface.json').exists():
    patch=json.loads((O/'bind_surface.json').read_text())
    mesh=bpy.data.objects['Super90_V7_M4_BareArmsV6']
    for e in patch['edits']:mesh.data.vertices[e['index']].co=e['after']
    mesh.data.normals_split_custom_set([(0.,0.,0.)]*len(mesh.data.loops))
    mesh.data.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones};I=Matrix.Identity(4)
lr={n:rest.get(parents[n],I).inverted()@m for n,m in rest.items()}
poses=json.loads((O/(tag+'_poses.json')).read_text())[branch]
keep={'SK_Super90','Super90_V7_M4_BareArmsV6','Super90_body','Super90_bolt','Super90_loading_gate','Super90_trigger','SM_Super90_LoaderGuide'}
for ob in scene.objects:
    ob.hide_render=ob.name not in keep;ob.hide_set(ob.name not in keep)
    if ob.type=='MESH' and ob.name in keep:
        m=bpy.data.materials.new('Diagnostic_'+ob.name);m.diffuse_color=(.64,.43,.32,1) if 'BareArms' in ob.name else (.09,.115,.13,1)
        ob.data.materials.clear();ob.data.materials.append(m)
        for polygon in ob.data.polygons:polygon.material_index=0
camera=json.loads((S/'Super90LoaderR20_20261010/camera_current.json').read_text());CQ=Quaternion(camera['rotation']);CP=Vector(camera['location']);Sinv=Matrix.Diagonal((.01,-.01,.01))
eye=Sinv@(CQ.inverted()@(-CP));fwd=(Sinv@(CQ.inverted()@Vector((1,0,0)))).normalized();right=(Sinv@(CQ.inverted()@Vector((0,1,0)))).normalized();up=right.cross(fwd).normalized()
camd=bpy.data.cameras.new('R23Camera');camd.sensor_fit='HORIZONTAL';camd.angle=math.radians(112);camd.clip_start=.001
cam=bpy.data.objects.new('R23Camera',camd);scene.collection.objects.link(cam);cam.matrix_world=rig.matrix_world@Matrix.LocRotScale(eye,Matrix((right,up,-fwd)).transposed().to_quaternion(),Vector((1,1,1)));scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=665;scene.render.resolution_percentage=100
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_shadows=False;sh.background_type='VIEWPORT';sh.background_color=(.065,.075,.085)
out=O/'Frames'/tag;out.mkdir(parents=True,exist_ok=True)
for f in frames:
    p={n:Matrix(m) for n,m in poses[f].items()}
    for b in rig.pose.bones:b.matrix_basis=lr[b.name].inverted()@p.get(parents[b.name],I).inverted()@p[b.name]
    bpy.context.view_layer.update();scene.render.filepath=str(out/(branch+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
