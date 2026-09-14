"""Author two new actions and a wider rift; keep installed V8 meshes/actions.

The complete shoulder/elbow/hand solution is baked continuously across the
charge/release boundary, then split into holdable clips at the shared pose.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;ROOT=P.parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P))
from arm_solver import ArmSolver
from heavy_motion import *
from action_timebase import rescale_action
bpy.context.preferences.filepaths.save_version=0

# Recover the exact accepted two-hand contact frames from the VRE/Manny donor.
donor=ROOT.parent/'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
bpy.context.scene.frame_set(0);r=bpy.data.objects['SK_M4_Infima']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
pose={b.name:b.matrix.copy() for b in r.pose.bones}
fit=json.loads((ROOT.parent/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G=pose['WPN_root']@Matrix(fit['grip_in_root']);S=Matrix.Diagonal((-1,1,1,1));GR=S@G@S
leftnames=[b.name for b in r.pose.bones if b.name.endswith('_l') and any(b.name.startswith(x) for x in ['index','middle','ring','pinky','thumb'])]
left_rel={n:pose['hand_l'].inverted()@pose[n] for n in leftnames}
mirrored={n[:-1]+'r':S@(pose[n]@rest[n].inverted())@S@rest[n[:-1]+'r'] for n in ['hand_l']+leftnames}
right_rel={n:mirrored['hand_r'].inverted()@m for n,m in mirrored.items() if n!='hand_r'}
HL=Matrix.Translation((0,0,.06))@G.inverted()@pose['hand_l']
HR=Matrix.Translation((0,0,.06))@GR.inverted()@mirrored['hand_r']
for grasp in [HL,HR]:
    radial=Vector((grasp.translation.x,grasp.translation.y,0))
    if radial.length>.0025:grasp.translation-=radial.normalized()*.0025

source=ROOT/'CompactRecoveryV8/AzureRunesword_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
solver=ArmSolver(rest,{'l':HL,'r':HR},{'l':left_rel,'r':right_rel});solver.ready_pose(READY)
for action in bpy.data.actions:rescale_action(action,FPS/(s.render.fps/s.render.fps_base))
s.render.fps=FPS;s.render.fps_base=1
paired=[full_pose(f/FPS) for f in range(round((CHARGE_SECONDS+RELEASE_END)*FPS)+1)]
frames=[p[0] for p in paired];hold=(round(LOAD_END*FPS),round(CHARGE_SECONDS*FPS))
print('HEAVY_SOLVING_GRASP',flush=True)
grasps=solver.fit_path(frames,False,hold)
supports=solver.fit_support(frames,grasps,hold)
supports=solver.separate_arms(frames,grasps,supports,hold)
print('HEAVY_SOLVING_BONES',flush=True)
r.animation_data.action=None
baked=[]
for f,(gf,sf) in enumerate(paired):
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:solver.apply_arm(p,side,solver.hand(side,gf,grasps[side][f]),supports[side][f])
    p['WPN_root']=sf
    for n in ['Blade_Base','Blade_Tip']:
        local=rest['WPN_root'].inverted()@rest[n];local.translation*=.8;p[n]=sf@local
    localpose={}
    for b in r.pose.bones:
        basis=localrest[b.name].inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
        localpose[b.name]=basis.decompose()
    baked.append(localpose)

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

receipt=[]
for name,start,end in [('HeavyCharge',0,round(CHARGE_SECONDS*FPS)),('HeavyRelease',round(CHARGE_SECONDS*FPS),len(baked)-1)]:
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True
    r.animation_data.action=action;s.frame_start=0;s.frame_end=end-start;previous={}
    for f,pose in enumerate(baked[start:end+1]):
        s.frame_set(f)
        for b in r.pose.bones:
            loc,q,scale=pose[b.name];q=q.copy()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    select(r)
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_RuneSword_'+name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    receipt.append({'clip':name,'seconds':(end-start)/FPS,'fps':FPS,'loop':False})
    print('HEAVY_EXPORTED '+name,flush=True)

# Broaden the swept optical ribbon through the centre and beyond the tip.
# This is visual distortion only; combat continues to use physical blade bones.
verts=[];faces=[];uvs=[];segments=120;across=10
for i in range(segments+1):
    u=i/segments;_,sf=release_pose(CONTACT_END*u)
    for j in range(across+1):
        v=j/across;verts.append(tuple(sf@Vector((0,0,.12+1.0*v))));uvs.append((u,v))
for i in range(segments):
    for j in range(across):
        a=i*(across+1)+j;faces.append((a,a+1,a+across+2,a+across+1))
mesh=bpy.data.meshes.new('RuneRift_Heavy');mesh.from_pydata(verts,[],faces);mesh.update()
ob=bpy.data.objects.new('SM_RuneRift_Heavy',mesh);s.collection.objects.link(ob)
uv=mesh.uv_layers.new(name='UVMap')
for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
select(ob)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_RuneRift_Heavy.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
ob.hide_set(True);ob.hide_render=True
r.animation_data.action=bpy.data.actions['A_RuneSword_HeavyCharge'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=round(CHARGE_SECONDS*FPS);s.frame_set(s.frame_end)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'ChargedHeavyV12','source':str(source),'donor':str(donor),'clips':receipt,'charge_seconds':CHARGE_SECONDS,'contact_seconds':[0,CONTACT_END],'release_end':RELEASE_END,'cut_arc_degrees':243,'load_guard_cm':[28,27,16],'blade_angle_degrees':-48,'rift_radial_cm':[12,112],'arm_solution':'continuous full-chain grasp and coupled elbow solution, split on identical held pose; original bone lengths/rest/weights','normal_actions':'retained V8 unchanged','retained_actions_at_480hz':True},indent=2),encoding='utf-8')
print('RUNESWORD_V12_AUTHORED',flush=True)
