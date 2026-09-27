import bpy,json,math,sys,ast
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).parent;ROOT=P.parents[1]
PRIOR=ROOT/'SourceAssets/RuneSwordElbowRepair20260920'
SOURCE=ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/Standard/Sword_PickaxeOverhead_Editable.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
source=bpy.data.actions['A_RuneSword_Overhead_Standard']
rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
zero={b.name:b.matrix.copy() for b in rig.pose.bones}
ue_zero=json.loads((PRIOR/'Standard_active.json').read_text())['clips']['Overhead']['samples'][0]['world']
C=Matrix.Diagonal(Vector((1,-1,1)))
K={n:(C@Quaternion(ue_zero[n]['q']).to_matrix()@C).inverted()@m.to_quaternion().to_matrix() for n,m in zero.items()}
tree=ast.parse((PRIOR/'pose_conversion.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('from_ue','ue_matrix','to_ue')],type_ignores=[]),'guard_conversion','exec'),globals())
sys.path.insert(0,str(ROOT/'SourceAssets/RuneSword20260913/InspectFollowThroughV82'))
from visible_bare import attach
arms=attach(rig);blade=bpy.data.objects['RuneSword_Blade']
rig.animation_data_clear()

def apply_pose(pose):
    for b in rig.pose.bones:
        parent=pose[b.parent.name] if b.parent else Matrix.Identity(4)
        b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@pose[b.name]
    bpy.context.view_layer.update()

def angle(a,b):
    q=a.rotation_difference(b);return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))

def metrics(p):
    U,F,H='upperarm_l','lowerarm_l','hand_l'
    fore=(p[H].translation-p[F].translation).normalized()
    ref=(rest[H].translation-rest[F].translation).normalized()
    ud=p[U].to_quaternion()@rest[U].to_quaternion().inverted()
    fd=p[F].to_quaternion()@rest[F].to_quaternion().inverted()
    aligned=(ud@ref).rotation_difference(fore)@ud
    delta=fd@aligned.inverted()
    seam=(math.degrees(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(fore),delta.w))+180)%360-180
    handaxis=p[H].to_quaternion()@rest[H].to_quaternion().inverted()@ref
    return {'wrist_bend_deg':math.degrees(fore.angle(handaxis)), 'elbow_seam_deg':seam,
      'upper_length_m':(p[F].translation-p[U].translation).length,
      'fore_length_m':(p[H].translation-p[F].translation).length,
      'helper_deformation_deg':{n:angle(p[n].to_quaternion()@rest[n].to_quaternion().inverted(),
          p[parent].to_quaternion()@rest[parent].to_quaternion().inverted())
          for parent in (U,F) for n in [parent[:-2]+'_twist_'+i+'_l' for i in ('01','02')]}}

def setup_render():
    for o in scene.objects:o.hide_render=o not in (arms,blade)
    arms.hide_set(False);blade.hide_set(False)
    arms.color=(.64,.39,.27,1);blade.color=(.40,.57,.72,1)
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.display.shading.background_type='WORLD';scene.world.color=(.045,.052,.068)
    scene.render.resolution_x=768;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=86
    data=bpy.data.cameras.new('GuardStudyCamera');cam=bpy.data.objects.new('GuardStudyCamera',data)
    scene.collection.objects.link(cam);scene.camera=cam;data.clip_start=.005
    return cam

def render_pose(pose,filename,close=False):
    apply_pose(pose);cam=scene.camera
    if close:
        target=(pose['hand_l'].translation+pose['lowerarm_l'].translation)*.5
        cam.location=target+Vector((-.12,-.70,.12))
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        cam.data.type='ORTHO';cam.data.ortho_scale=.46
    else:
        cam.data.type='PERSP';cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0)
        cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24
        cam.data.lens=24/(2*math.tan(math.radians(75/2)))
    scene.render.filepath=str(filename);bpy.ops.render.render(write_still=True)
