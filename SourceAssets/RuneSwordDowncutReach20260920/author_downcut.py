"""Bake a reach correction onto the two installed V4 overhead clips only."""
import ast,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).parent;ROOT=P.parents[1];sys.path.insert(0,str(P))
from reach_solver import solve
OLD=ROOT/'SourceAssets/RuneSwordElbowRepair20260920'
SOURCE=ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/Standard/Sword_PickaxeOverhead_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
action=bpy.data.actions['A_RuneSword_Overhead_Standard'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update();zero={b.name:b.matrix.copy() for b in rig.pose.bones}
ue_zero=json.loads((OLD/'Standard_active.json').read_text())['clips']['Overhead']['samples'][0]['world']
C=Matrix.Diagonal(Vector((1,-1,1)))
K={n:(C@Quaternion(ue_zero[n]['q']).to_matrix()@C).inverted()@m.to_quaternion().to_matrix() for n,m in zero.items()}
tree=ast.parse((OLD/'pose_conversion.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'from_ue','ue_matrix','to_ue','qangle'}],type_ignores=[]),str(OLD/'pose_conversion.py'),'exec'),globals())
edited=[n+'_'+s for s in ('l','r') for n in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]+['WPN_root']
report={'revision':'DowncutReachV5','target_elbow_interior_degrees':160.,'contact_window_seconds':[1.22,1.40],
 'grasp':'V4 wrist orientation and sword-local palm/finger transforms retained',
 'scope':'Standard and LongGrip Overhead only; all other clips retain V4','runtime_tested':False,'variants':{}}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/(variant+'_input.json')).read_text());out=P/variant;out.mkdir(exist_ok=True)
    action=bpy.data.actions.new('DowncutReachV5_'+variant+'_Overhead');action.use_fake_user=True;rig.animation_data.action=action
    scene.render.fps=120;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=data['intervals']
    previous={};blend_previous={};rows=[];metrics=[]
    for i,row in enumerate(data['samples']):
        original=from_ue(row['world']);pose,stat=solve(original,data['parents'],row['seconds'])
        stat.update({'seconds':row['seconds'],'sides':{}})
        for side in ('l','r'):
            u,f,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
            def angle(p):
                a,e,w=[p[n].translation for n in (u,f,h)]
                return math.degrees((a-e).angle(w-e))
            old_grip=original['WPN_root'].inverted()@original[h];new_grip=pose['WPN_root'].inverted()@pose[h]
            stat['sides'][side]={'before_deg':angle(original),'after_deg':angle(pose),
                'grip_error_m':(old_grip.translation-new_grip.translation).length,
                'hand_rotation_error_deg':math.degrees(qangle(pose[h].to_quaternion(),original[h].to_quaternion())),
                'segment_length_error_m':max(abs((pose[b].translation-pose[a].translation).length-(original[b].translation-original[a].translation).length) for a,b in ((u,f),(f,h)))}
        metrics.append(stat)
        desired=to_ue(pose,row['world']);keys={}
        for n in edited:
            parent=data['parents'][n];local=desired[parent].inverted()@desired[n];p,q,s=local.decompose()
            s=(ue_matrix(row['world'][parent]).inverted()@ue_matrix(row['world'][n])).decompose()[2]
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();keys[n]={'p':list(p),'q':list(q),'s':list(s)}
        rows.append({'seconds':row['seconds'],'bones':keys})
        scene.frame_set(i)
        for b in rig.pose.bones:
            parent=pose[b.parent.name] if b.parent else Matrix.Identity(4)
            b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@pose[b.name];b.rotation_mode='QUATERNION'
            q=b.rotation_quaternion.copy()
            if b.name in blend_previous and q.dot(blend_previous[b.name])<0:q.negate()
            b.rotation_quaternion=q;blend_previous[b.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=i,group=b.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for k in curve.keyframe_points:k.interpolation='LINEAR'
    scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_Overhead_DowncutReachV5.blend'))
    patch={k:data[k] for k in ('asset','intervals','seconds')};patch.update({'source_sha256':data['sha256'],'edited_bones':edited,'samples':rows})
    (out/'Overhead_patch.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    (out/'path_diagnosis.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    down=[r for r in metrics if 1.11<=r['seconds']<=1.50]
    report['variants'][variant]={'asset':data['asset'],'frames':len(rows),'seconds':data['seconds'],
        'min_downcut_angle_deg':{s:min(r['sides'][s]['after_deg'] for r in down) for s in ('l','r')},
        'max_forward_shift_m':max(r['forward_m'] for r in metrics),
        'max_shoulder_shift_m':max(max(r['shoulder_m'].values()) for r in metrics),
        'max_grip_error_m':max(r['sides'][s]['grip_error_m'] for r in metrics for s in ('l','r')),
        'max_hand_rotation_error_deg':max(r['sides'][s]['hand_rotation_error_deg'] for r in metrics for s in ('l','r')),
        'max_segment_length_error_m':max(r['sides'][s]['segment_length_error_m'] for r in metrics for s in ('l','r'))}
    print('DOWNCUT_AUTHORED '+variant+' '+json.dumps(report['variants'][variant]),flush=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
