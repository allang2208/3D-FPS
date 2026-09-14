"""Author the new thrust on the accepted Manny sword rig, retaining old clips."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;ROOT=P.parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P))
from arm_solver import ArmSolver
from guard_motion import *
bpy.context.preferences.filepaths.save_version=0

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

# Executed after the shared accepted two-hand donor setup in author_guard.py.
source=ROOT/'StrideThrustV16/AzureRunesword_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
solver=ArmSolver(rest,{'l':HL,'r':HR},{'l':left_rel,'r':right_rel});solver.ready_pose(READY)
s.render.fps=FPS;s.render.fps_base=1
paired=[poses(f/FPS) for f in range(round(TOTAL*FPS)+1)]
frames=[p[0] for p in paired];hold=(round(RAISE_END*FPS),round(HOLD_END*FPS))
print('GUARD_SOLVING_ARMS',flush=True)
grasps=solver.fit_path(frames,False,hold)
supports=solver.fit_support(frames,grasps,hold)
supports=solver.separate_arms(frames,grasps,supports,hold)
world=[]
for f,(gf,sf) in enumerate(paired):
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:solver.apply_arm(p,side,solver.hand(side,gf,grasps[side][f]),supports[side][f])
    p['WPN_root']=sf
    for n in ['Blade_Base','Blade_Tip']:
        local=rest['WPN_root'].inverted()@rest[n];local.translation*=.8;p[n]=sf@local
    world.append(p)

guard=world[round(RAISE_END*FPS)]
hit=[]
for f in range(round(.22*FPS)+1):
    t=f/FPS
    strength=smooth(t/.045) if t<.045 else 1-smooth((t-.045)/(.22-.045))
    # Rigid supported-arm recoil preserves the exact held grasp at both ends.
    pivot=GUARD[0].translation
    delta=Matrix.Translation(pivot+Vector((0,-.045,-.012))*strength)@Matrix.Rotation(math.radians(4)*strength,4,'X')@Matrix.Translation(-pivot)
    p={n:m.copy() for n,m in guard.items()}
    for n in p:
        if n.endswith(('_l','_r')) or n in ['WPN_root','Blade_Base','Blade_Tip']:p[n]=delta@p[n]
    hit.append(p)

def export(name,sequence):
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True;r.animation_data.action=action
    s.frame_start=0;s.frame_end=len(sequence)-1;previous={}
    for f,p in enumerate(sequence):
        s.frame_set(f)
        for b in r.pose.bones:
            basis=localrest[b.name].inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
            loc,q,scale=basis.decompose()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_RuneSword_'+name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    print('GUARD_EXPORTED_'+name,flush=True)
    return action

raise_action=export('Guard',world[:round(RAISE_END*FPS)+1])
export('GuardHit',hit)
export('GuardBreak',world[round(HOLD_END*FPS):])
r.animation_data.action=raise_action;r.animation_data.action_slot=raise_action.slots[0]
s.frame_start=0;s.frame_end=round(RAISE_END*FPS);s.frame_set(s.frame_end)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'GuardParryV18','source':str(source),'donor':str(donor),'fps':FPS,'guard_raise_seconds':.20,'guard_lower_seconds':.18,'guard_hit_seconds':len(hit)/FPS-1/FPS,'guard_break_seconds':.40,'guard_hilt_m':[.20,.46,-.14],'loop':'hold final Guard pose; non-looping hit/break','retained':'existing sword, Manny mesh, weights, two-hand grip, accepted attacks','reference':'gamedev player-shield-walk-lower-20260902/shield-all-standing-guard.png'},indent=2),encoding='utf-8')
print('RUNESWORD_V18_AUTHORED',flush=True)
