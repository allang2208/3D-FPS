"""Author the M66 inhale/burst/recovery and one local oral-opening morph."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'FurnaceBreathV17'
for d in ('Authoring','Export','Records'):(ROOT/d).mkdir(parents=True,exist_ok=True)
prefix=(BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0]
prefix=prefix.replace("ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'","ROOT.parent/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'")
exec(compile(prefix,'M66_native_rig','exec'));ROOT=BASE/'FurnaceBreathV17'
pose_frame('Idle',0.);bpy.context.view_layer.update()
neutral={n:rig.pose.bones[n].matrix.copy() for n in ordered}
nlocal={n:neutral[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in neutral.items()}
base_feet={side:neutral[foot].translation.copy() for side,_,_,foot in chains}
for node in ast.parse((BASE/'ReactionsV03/author_reactions.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in {'apply_worlds','solve_planted_legs'}:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'M66_native_support','exec'))

# A shape key opens only the continuous oral lining. V10 vertex weights, UVs,
# topology, hands and hanging tissue remain the original accepted mesh.
pos=np.array([v.co[:] for v in mesh.data.vertices]);x,y,z=pos.T
def ramp(a,b,v):
    t=np.clip((v-a)/(b-a),0.,1.);return t*t*(3-2*t)
small=np.load(BASE/'SmallHandSeparationV09/Records/small_arm_surface.npy')
giant=np.load(BASE/'ThumbDrapeV10/Records/giant_hand.npy')
mask=ramp(-.52,-.38,x)*(1-ramp(.43,.60,x))*(1-ramp(-.40,-.22,y))
mask*=ramp(1.28,1.48,z)*(1-ramp(2.73,2.98,z));mask[small|giant]=0.
if not mesh.data.shape_keys:mesh.shape_key_add(name='Basis')
mouth=mesh.shape_key_add(name='M66_FurnaceOpen')
delta=np.zeros_like(pos);delta[:,0]=np.tanh((x-.08)/.16)*.045*mask
delta[:,1]=-.025*mask;delta[:,2]=np.tanh((z-2.12)/.35)*.025*mask
for i in np.flatnonzero(mask>1e-7):mouth.data[int(i)].co=Vector(pos[i]+delta[i])
mouth.value=0.

rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
skin=ROOT/'Export/SK_M66_Furnace_V17.fbx'
bpy.ops.export_scene.fbx(filepath=str(skin),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
FPS=120;END=3.4;COUNT=409;scene.render.fps=FPS;scene.frame_start=0;scene.frame_end=COUNT-1
action=bpy.data.actions.new('A_M66_FurnaceBreath_V17');action.use_fake_user=True;rig.animation_data.action=action;previous={}
def values(t):
    inhale=smooth(t/.95)
    thrust=smooth((t-1.08)/.12)
    release=1-smooth((t-2.8)/.6)
    pulse=(math.sin((t-1.2)*math.pi*10)*math.exp(-max(0.,t-1.2)*1.4) if 1.2<t<2.4 else 0.)
    return inhale,thrust,release,pulse
for frame in range(COUNT):
    scene.frame_set(frame);t=frame/FPS;inhale,thrust,release,pulse=values(t);worlds={}
    for n in ordered:
        m=worlds[parents[n]]@nlocal[n] if parents[n] else nlocal[n].copy()
        if n=='Bone_000':m.translation+=Vector((-.018*inhale*release,(.035*inhale-.075*thrust)*release,-(.045*inhale+.045*thrust)*release))
        if n in ('Bone_007','Bone_006','Bone_005'):
            gain={'Bone_007':.65,'Bone_006':1.,'Bone_005':.65}[n]
            m=rotate(m,(1,0,0),(-.045*inhale+.102*thrust+.006*pulse)*release*gain)
        if n=='Bone_027':m=rotate(m,(0,1,0),(.11*inhale+.03*thrust)*release)
        if n=='Bone_026':m=rotate(m,(1,0,0),.055*inhale*release)
        if n=='Bone_032':m=rotate(m,(0,1,0),-.085*inhale*release)
        if n=='Bone_031':m=rotate(m,(1,0,0),-.035*inhale*release)
        if n.startswith('M66_Sac'):
            amount=(.040*inhale-.030*thrust+.004*pulse)*release
            m=m@Matrix.Diagonal((1+amount,1+amount*.55,1+amount*.75,1))
        if n.startswith('M66_Vent') and n.endswith('_Tip'):m=rotate(m,(1,0,0),(.035*inhale-.025*thrust)*release)
        worlds[n]=m
    solve_planted_legs(worlds);apply_worlds(worlds)
    for pb in rig.pose.bones:
        q=pb.rotation_quaternion.copy()
        if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
        previous[pb.name]=q.copy();pb.rotation_quaternion=q
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
if action.slots:rig.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for curve in strip.channelbag(action.slots[0]).fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
action['M66_contract']='0-.95 inhale; .95 aim lock; 1.08-1.20 fast thrust; 1.20-2.40 breath; 2.40-2.80 hold; 2.80-3.40 recovery'
scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/A_M66_FurnaceBreath_V17.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
authoring=ROOT/'Authoring/M66_furnace_breath_v17.blend';bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
manifest={'source':str(BASE/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'),'authoring':str(authoring),'fbx':str(skin),
    'clips':[{'role':'FurnaceBreath','action':action.name,'fbx':str(fbx),'seconds':END,'fps':FPS,'frames':COUNT,'loop':False}],
    'morph':'M66_FurnaceOpen','morph_vertices':int((mask>1e-7).sum()),'neutral_geometry_modified':False,'weights_modified':False,
    'mouth_source_m':[.08,-.70,2.15],'mouth_bone':'Bone_006',
    'source_reference_bones':{n:list(rest[n].translation) for n in ('Bone_001','Bone_006','Bone_010','Bone_015')},
    'runtime_tested':False,'rendered':False}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2));(ROOT/'Records/skin_manifest.json').write_text(json.dumps(manifest,indent=2))
print('M66_FURNACE_AUTHORED '+json.dumps({'frames':COUNT,'morph_vertices':manifest['morph_vertices'],'skin':str(skin),'animation':str(fbx)}),flush=True)
