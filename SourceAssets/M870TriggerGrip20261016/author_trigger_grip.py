"""Apply the original M870 stock grip and preserve the authored reload operation."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;R=O.parent/'M870ReloadSource20261016';X=O/'Exports/Animations';X.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(R/'author_source_reload.py')}
exec(compile((R/'author_source_reload.py').read_text(encoding='utf-8').split('tree=ast.parse')[0],str(R/'author_source_reload.py'),'exec'),ns)
bpy.ops.wm.open_mainfile(filepath=str(R/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;s.render.fps=60;s.render.fps_base=1
D=json.loads((O/'grip_input.json').read_text(encoding='utf-8'));fit=json.loads((O/'grip_fit.json').read_text(encoding='utf-8'));pad=json.loads((O/'trigger_pad.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents=D['parents'];names=list(rest);I=Matrix.Identity(4)
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
idle={n:Matrix(m) for n,m in D['idle'].items()};grip={n:Matrix(m) for n,m in fit['hand_world'].items()}
source=ns['sp']['Idle'][0];root_delta=grip['hand_r']@Matrix(D['reference_hand']['hand_r']).inverted();registration=root_delta@Matrix(D['registration'])
template=ns['support']({n:m.copy() for n,m in idle.items()},source,registration,grip['hand_r'])
template.update(grip);under=ns['under'];ease=ns['ease'];mix=ns['mix'];right=[n for n in names if under(n,'clavicle_r')]
# Skin-space trigger contact is selected from the native distal index pad.
contact=Vector()
for i in pad['vertices']:
 v=Vector(D['native_points'][i]);point=Vector()
 for n,w in D['weights'][i].items():
  if n in grip:point+=(grip[n]@rest[n].inverted()@v)*w
 contact+=point
contact/=len(pad['vertices']);pad_local=grip['index_03_r'].inverted()@contact
index_names=[f'index_{j:02d}_r' for j in (1,2,3)]
index_local={n:grip[parents[n]].inverted()@grip[n] for n in index_names}
axes={n:Vector(fit['joint_axes'][n]) for n in index_names}
oldgun_inverse=idle['WPN_root'].inverted();oldtrigger_inverse=idle['WPN_Trigger'].inverted()

def follow_trigger(row,gm):
    delta=row['WPN_Trigger']@oldtrigger_inverse@gm.inverted()
    target=delta@(gm@contact)
    def evaluate(angles):
        out={}
        for j,n in enumerate(index_names):
            m=index_local[n].copy();m=m@Quaternion(axes[n],float(angles[j])).to_matrix().to_4x4()
            parent=out.get(parents[n],row[parents[n]])
            out[n]=parent@m
        return out,out['index_03_r']@pad_local
    angles=np.zeros(3);desired=np.array(target)
    for k in range(7):
        posed,p=evaluate(angles);err=desired-np.array(p)
        if np.linalg.norm(err)<.00015:break
        jac=[]
        for j in range(3):
            q=angles.copy();q[j]+=.001;_,tip=evaluate(q);jac.append((np.array(tip)-np.array(p))/.001)
        J=np.array(jac).T;change=np.linalg.solve(J.T@J+np.eye(3)*.000004,J.T@err-angles*.000004)
        angles=np.clip(angles+change,-math.radians(8),math.radians(8))
    posed,_=evaluate(angles)
    row.update(posed)
    return float(max(abs(angles)))

def held_weight(role,t):
    if not role.startswith('reload_'):return 1.
    f=t*60
    if f<18:return 1-ease(f/18)
    if f<360:return 0.
    _,phase=ns['source_clock'](f,role)
    return ease(phase/9)

def apply_grip(original,role,t):
    weight=held_weight(role,t)
    if weight<=0:return {n:m.copy() for n,m in original.items()},0.
    gm=original['WPN_root']@oldgun_inverse
    held={n:m.copy() for n,m in original.items()};oldheld={n:m.copy() for n,m in original.items()}
    for n in right:
        held[n]=gm@template[n];oldheld[n]=gm@idle[n]
    flex=follow_trigger(held,gm)
    if weight>=1:return held,flex
    # Change only the held-pose contribution at entry/return. Native local
    # offsets remain intact, and all active loading frames are exact input.
    row={n:m.copy() for n,m in original.items()}
    for n in right:
        parent=parents[n]
        old=oldheld[parent].inverted()@oldheld[n]
        new=held[parent].inverted()@held[n]
        current=original[parent].inverted()@original[n]
        dq=new.to_quaternion()@old.to_quaternion().inverted()
        if dq.w<0:dq=-dq
        q=Quaternion().slerp(dq,weight)@current.to_quaternion()
        v=current.translation.copy()
        if n=='clavicle_r':v+=(new.translation-old.translation)*weight
        row[n]=row[parent]@Matrix.LocRotScale(v,q,current.to_scale())
    return row,flex

def bake(role,rows,rate):
    action=bpy.data.actions.new('A_M870_'+role);action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action
    for b in r.pose.bones:
        b.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves};values={n:[] for n in names};previous={}
    for row in rows:
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];v,q,sc=(local_rest[n].inverted()@local).decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();values[n].append((v,q,sc))
    step=60/rate
    for n in names:
        for prop,k,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(rows));curve.keyframe_points.foreach_set('co',[v for i,row in enumerate(values[n]) for v in (i*step,row[k][axis])])
                for key in curve.keyframe_points:key.interpolation='LINEAR'
                curve.update()
    s.frame_start=0;s.frame_end=round((len(rows)-1)*step);r.animation_data.action_slot=action.slots[0];s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    file=X/('A_M870_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=step,bake_anim_simplify_factor=0)
    return {'file':str(file),'duration':(len(rows)-1)/rate,'action':action.name,'sample_rate':rate,'samples':len(rows)}

report={'reference':'UC original M870 Idle, whole-hand contact adjustment and bounded flexion only','input':str(R/'M870_ReloadSource_Editable.blend'),'clips':{},'scope':{},'runtime_tested':False,'visual_tested':False}
for role,entry in D['manifest'].items():
    action=bpy.data.actions[entry['action']];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];rate=entry['sample_rate'];count=round(entry['duration']*rate)+1;rows=[];maxflex=0.;kept=0
    for i in range(count):
        frame=i*60/rate;s.frame_set(int(frame),subframe=frame-int(frame));original={b.name:b.matrix.copy() for b in r.pose.bones};row,flex=apply_grip(original,role,i/rate);rows.append(row);maxflex=max(maxflex,flex)
        if held_weight(role,i/rate)<=0:kept+=1
    report['clips'][role]=bake(role,rows,rate)
    report['scope'][role]={'input_action':entry['action'],'held_pose_updated':True,'untouched_loading_samples':kept,'max_trigger_follow_flexion_deg':math.degrees(maxflex)}
    print('M870_TRIGGER_GRIP_AUTHORED',role,count,flush=True)
a=bpy.data.actions[report['clips']['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_TriggerGrip_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
