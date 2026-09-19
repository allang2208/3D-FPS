"""Reconnect the upper arms while preserving the V40 hands, sword and forearms.

The shoulder cut loop is constrained outside the reference camera. The upper
arm rotates as one complete segment about its elbow, without changing length,
wrist articulation, skin weights or the reference finger/weapon choreography.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

P=Path(__file__).parent;V40=P.parent/'ForwardGroupFlowV40'
SOURCE=V40/'AzureRunesword_ForwardGroupFlowV40.blend'
FPS=120;DURATION=2.9;COUNT=round(FPS*DURATION)+1
K=math.tan(math.radians(37.5));ASPECT=16/9;MARGIN=.015
AWAY={side:Vector((0.,-K,-1.)).normalized() for side in ('l','r')}
OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export']
action=bpy.data.actions['A_RuneSword_Inspect'];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
before=json.loads((P/'Review_ForwardGroupFlowV40/source_audit.json').read_text())
loops={side:next(g['vertices'] for g in before['boundaries'] if g['weights'][0][0].endswith('_'+side)) for side in ('l','r')}
segments={side:[f'{base}_{side}' for base in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02')] for side in ('l','r')}
poses=[];boundaries=[]
for f in range(COUNT):
    s.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
    er=r.evaluated_get(dg);ea=arms.evaluated_get(dg);mesh=ea.to_mesh()
    poses.append({b.name:b.matrix.copy() for b in er.pose.bones})
    boundaries.append({side:[ea.matrix_world@mesh.vertices[i].co for i in ids] for side,ids in loops.items()})
    ea.to_mesh_clear()


def transform(f,side,amount):
    pose=poses[f];a=pose['upperarm_'+side].translation;e=pose['lowerarm_'+side].translation
    old=(a-e).normalized();new=old.lerp(AWAY[side],amount).normalized()
    q=old.rotation_difference(new)
    return Matrix.Translation(e)@q.to_matrix().to_4x4()@Matrix.Translation(-e)


def clearance(points):
    # The complete loop must lie beyond one common frustum plane. This also
    # excludes edges whose vertices happen to sit beyond different screen sides.
    return max(min(-v.z-K*v.y for v in points),
               min(v.x-K*ASPECT*v.y for v in points),
               min(-v.x-K*ASPECT*v.y for v in points),min(.005-v.y for v in points))


def required_amount(f,side):
    points=boundaries[f][side]
    if clearance(points)>=MARGIN:return 0.
    low=0.
    for step in range(1,81):
        high=step/80
        delta=transform(f,side,high)
        if clearance([delta@v for v in points])>=MARGIN:
            for _ in range(20):
                mid=(low+high)*.5;trial=transform(f,side,mid)
                if clearance([trial@v for v in points])>=MARGIN:high=mid
                else:low=mid
            return high
        low=high
    debug={'frame':f,'side':side,'A':list(poses[f]['upperarm_'+side].translation),
           'E':list(poses[f]['lowerarm_'+side].translation),'points':[list(v) for v in points],
           'candidate_margins':[clearance([transform(f,side,k/20)@v for v in points]) for k in range(21)]}
    (P/'connection_failure.json').write_text(json.dumps(debug,indent=2))
    raise RuntimeError(f'No supported upper-arm connection at frame {f}, side {side}')


def smooth_envelope(values):
    # Expand before filtering so smoothing cannot undercut the required shoulder
    # clearance at a narrow motion peak. Twelve frames cover 0.10 seconds.
    radius=6
    expanded=[max(values[max(0,i-radius):min(COUNT,i+radius+1)]) for i in range(COUNT)]
    weights=[math.exp(-.5*(j/3.)**2) for j in range(-radius,radius+1)]
    total=sum(weights)
    result=[sum(w*expanded[min(COUNT-1,max(0,i+j))] for j,w in zip(range(-radius,radius+1),weights))/total for i in range(COUNT)]
    result[0]=result[-1]=0.
    return result


# At the entrance's maximum forward swing, the existing elbow is too high for
# a full-length upper arm to put its entire open shoulder rim below the camera.
# Add only the small common downward displacement needed at these frames.
# The hand, sword and forearm still receive exactly the same displacement.
down_required=[]
for f in range(COUNT):
    needed=0.
    for side in ('l','r'):
        if clearance(boundaries[f][side])>=MARGIN:continue
        delta=transform(f,side,1.)
        points=[delta@v for v in boundaries[f][side]]
        bottom=min(-v.z-K*v.y for v in points)
        needed=max(needed,MARGIN+.004-bottom)
    down_required.append(max(0.,needed))
down=smooth_envelope(down_required)
print('ENTRANCE_DOWNWARD_ADJUSTMENT_M',max(down),flush=True)
if max(down)>.05:raise RuntimeError('Required hand displacement exceeds the planned small correction')
for f in range(COUNT):
    common=Matrix.Translation(Vector((0.,0.,-down[f])))
    poses[f]={n:common@m for n,m in poses[f].items()}
    boundaries[f]={side:[common@v for v in points] for side,points in boundaries[f].items()}
requirements={side:[required_amount(f,side) for f in range(COUNT)] for side in ('l','r')}
amounts={side:smooth_envelope(values) for side,values in requirements.items()}
action.name='RETAINED_V40_A_RuneSword_Inspect';action.use_fake_user=True
new=bpy.data.actions.new('A_RuneSword_Inspect');new.use_fake_user=True;r.animation_data.action=new
previous={};report=[]
for f,source in enumerate(poses):
    pose={n:m.copy() for n,m in source.items()};row={'frame':f,'time':f/FPS,'common_down_m':down[f],'sides':{}}
    for side in ('l','r'):
        delta=transform(f,side,amounts[side][f])
        for n in segments[side]:pose[n]=delta@source[n]
        margin=clearance([delta@v for v in boundaries[f][side]])
        if margin<MARGIN-.00001 and f not in (0,COUNT-1):
            raise RuntimeError(f'Smoothed shoulder constraint failed: {f}, {side}, {margin}')
        row['sides'][side]={'required':requirements[side][f],'amount':amounts[side][f],
                            'clearance_m':margin,'upper_arm_swing_deg':math.degrees(delta.to_quaternion().angle)}
    report.append(row)
    for n,bone in r.pose.bones.items():
        local=pose[parents[n]].inverted()@pose[n] if parents[n] else pose[n]
        loc,q,scale=(local_rest[n].inverted()@local).decompose()
        if n in previous and q.dot(previous[n])<0:q.negate()
        previous[n]=q.copy();bone.rotation_mode='QUATERNION'
        bone.location,bone.rotation_quaternion,bone.scale=loc,q,scale
        for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=f,group=n)
r.animation_data.action_slot=new.slots[0]
for layer in new.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
s.render.fps=FPS;s.render.fps_base=1.;s.frame_start=0;s.frame_end=COUNT-1;s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_RuneSword_Inspect.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
r['AnchoredArmFlowV41']='Upper-arm cut loops outside camera; hands, forearms and sword retain V40 motion'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_AnchoredArmFlowV41.blend'))
(P/'construction.json').write_text(json.dumps({'revision':'AnchoredArmFlowV41','source':str(SOURCE),
  'fps':FPS,'duration':DURATION,'camera_vertical_fov':75,'camera_aspect':ASPECT,'cut_loop_margin_m':MARGIN,
  'method':'Complete upper-segment swing about unchanged elbow; smoothed camera-clearance envelope',
  'mesh_weights_rest_unchanged':True,'samples':report},indent=2),encoding='utf-8')
print('ANCHORED_ARM_V41_AUTHORING_COMPLETE',flush=True)
