"""Open-palm blade brace using the current spell-release digit pose; no renders/tests."""
import sys,json,math,ast,hashlib
from pathlib import Path
TASK=Path(__file__).parent;ROOT=TASK.parents[1]
V22=ROOT/'SourceAssets/SwordGuardLeftRepair20260926'
sys.path.insert(0,str(V22))
from guard_source import *
P=TASK;ONE=Vector((1,1,1))
# Reuse the supported whole-arm solver without executing V22 authoring/rendering.
tree=ast.parse((V22/'author.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('ease','blend','frame','arm')],type_ignores=[]),'guard_support_solver','exec'),globals())
cast_source=ROOT/'SourceAssets/FireballCast20260914/author_cast.py'
tree=ast.parse(cast_source.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='semantic_frame'],type_ignores=[]),'casting_semantic_frame','exec'),globals())
cfg_path=ROOT/'Content/ColdSteelData/Skills/fireball_hand_pose.json'
cfg=json.loads(cfg_path.read_text())
spread={'index':-9.,'middle':0.,'ring':8.,'pinky':16.}
finger_names=[n for n in rest if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))]
left_names=[n for n in rest if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','index','middle','ring','pinky','thumb'))]
wrist=rest['hand_l'].translation
ref_normal=(rest['pinky_01_l'].translation-wrist).cross(rest['index_01_l'].translation-wrist).normalized()
ref_palm=semantic_frame(rest['middle_01_l'].translation-wrist,ref_normal)

def open_digits():
    p={n:m.copy() for n,m in rest.items()}
    for n in finger_names:
        par=parents[n];m=p[par]@local_rest[n];parts=n.split('_')
        if len(parts)==3 and parts[1].isdigit():
            k=int(parts[1])-1;digit=cfg['digits'][parts[0]];next_name=f'{parts[0]}_{k+2:02d}_l'
            if next_name in rest:rd=rest[next_name].translation-rest[n].translation
            else:rd=rest[n].to_quaternion()@(rest[par].to_quaternion().inverted()@(rest[n].translation-rest[par].translation))
            # Same release flex as the live spell. Fan the four fingers for the guard.
            s=math.radians(spread.get(parts[0],digit['spread'][k]));f=math.radians(digit['release_flex'][k])
            target=ref_palm@Vector((math.cos(f)*math.cos(s),math.cos(f)*math.sin(s),math.sin(f)))
            q=(semantic_frame(target,ref_palm.col[2])@semantic_frame(rd,ref_normal).inverted()@rest[n].to_3x3()).to_quaternion()
            m=Matrix.LocRotScale(m.translation,q,ONE)
        p[n]=m
    return {n:p[parents[n]].inverted()@p[n] for n in finger_names}

OPEN=open_digits()
receipt=json.loads((V22/'import_receipt.json').read_text())
record={'revision':'GuardPalmPushV23','reference_config':str(cfg_path),'reference_sha256':hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
    'reference':'Current spell-release semantic palm and release_flex; adapted onto sword rig',
    'finger_fan_degrees':spread,'thumb_spread_degrees':cfg['digits']['thumb']['spread'],
    'palm_contact':'Palm toward blade / away from camera; fingers up and spread',
    'rendered':False,'tested':False,'variants':{}}
(P/'spell_pose_reference.json').write_text(json.dumps(cfg,indent=2))
for variant in ('Standard','LongGrip'):
    data=json.loads((V22/'After'/variant/'installed.json').read_text())
    idle=from_ue(data['clips']['Idle']['samples'][0]['world'])
    old=from_ue(data['clips']['Guard']['samples'][-1]['world'])
    sword=old['WPN_root'];axis=(old['Blade_Tip'].translation-old['Blade_Base'].translation).normalized()
    normal=Vector((0,1,0));up=normal.cross(axis).normalized()
    # Palm and spread digits lie against the near broad face. The chosen sword
    # orientation stays exactly V22; only the left-arm chain is authored.
    qh=(semantic_frame(up,normal)@ref_palm.inverted()@rest['hand_l'].to_3x3()).to_quaternion()
    pad_world=wrist+(((rest['index_01_l'].translation+rest['pinky_01_l'].translation)*.5)-wrist)*.62
    pad_local=rest['hand_l'].inverted()@pad_world
    contact=sword.translation+axis*.32
    hand=Matrix.LocRotScale(contact-qh@pad_local,qh,ONE)
    candidate={n:m.copy() for n,m in old.items()};arm(candidate,'l',hand,idle,1.)
    for n in finger_names:candidate[n]=candidate[parents[n]]@OPEN[n]
    # Authoring fit on the accepted V7 palm surface, not on a wrist bone pivot.
    apply_pose(candidate);deps=bpy.context.evaluated_depsgraph_get()
    ev=arms.evaluated_get(deps);sk=ev.to_mesh();group=arms.vertex_groups['hand_l'].index
    palm_points=[]
    for v in arms.data.vertices:
        p=ref_palm.inverted()@(v.co-wrist)
        if .022<p.x<.073 and abs(p.y)<.030 and any(g.group==group and g.weight>.5 for g in v.groups):
            palm_points.append((ev.matrix_world@sk.vertices[v.index].co).y)
    be=blade.evaluated_get(deps);bm=be.to_mesh();blade_points=[]
    for v in bm.vertices:
        p=be.matrix_world@v.co
        if .24<(p-sword.translation).dot(axis)<.40:blade_points.append(p.y)
    palm_shift=min(blade_points)-.001-max(palm_points)
    ev.to_mesh_clear();be.to_mesh_clear();hand.translation.y+=palm_shift
    shift=hand.translation-old['hand_l'].translation
    turn=hand.to_quaternion()@old['hand_l'].to_quaternion().inverted()
    ilocal={n:idle[parents[n]].inverted()@idle[n] for n in finger_names}
    dest=P/'Final'/variant;dest.mkdir(parents=True,exist_ok=True)
    record['variants'][variant]={'palm_fit_shift_m':palm_shift,'held_wrist_m':list(hand.translation),'clips':{}}
    for clip in ('Guard','GuardHit','GuardBreak'):
        info=data['clips'][clip];poses=[];rows=[];previous={}
        for i,row in enumerate(info['samples']):
            t=row['seconds'];duration=info['seconds'];p=from_ue(row['world'])
            if clip=='Guard':w=ease(t/duration);opened=ease((t-.012)/.145)
            elif clip=='GuardHit':w=1.;opened=1.
            else:w=1-ease((t-.105)/(duration-.105));opened=1-ease((t-.16)/(duration-.16))
            if w>1e-8:
                # Transport the held-pose correction through the existing sword motion.
                delta=p['WPN_root'].to_quaternion()@sword.to_quaternion().inverted()
                worldturn=delta@turn@delta.inverted()
                targetq=worldturn@p['hand_l'].to_quaternion()
                target=Matrix.LocRotScale(p['hand_l'].translation+(delta@shift)*w,
                    p['hand_l'].to_quaternion().slerp(targetq,w),ONE)
                arm(p,'l',target,idle,w)
                for n in finger_names:p[n]=p[parents[n]]@blend(ilocal[n],OPEN[n],opened)
            poses.append(p);native=to_ue(p,row['world']);keys={}
            for n in left_names:
                par=data['parents'][n];m=native[par].inverted()@native[n]
                pos,q,_=m.decompose();original=ue_matrix(row['world'][par]).inverted()@ue_matrix(row['world'][n])
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n]=q.copy();keys[n]={'p':list(pos),'q':list(q),'s':list(original.to_scale())}
            rows.append({'seconds':t,'bones':keys})
        baseline=receipt['assets'][variant+'/'+clip+'_patch']['after_sha256']
        patch={'revision':'GuardPalmPushV23','asset':info['asset'],'source_sha256':baseline,'intervals':info['intervals'],'seconds':info['seconds'],'edited_bones':left_names,'samples':rows}
        (dest/(clip+'_patch.json')).write_text(json.dumps(patch,separators=(',',':')))
        action=bpy.data.actions.new('GuardV23_'+variant+'_'+clip);action.use_fake_user=True
        rig.animation_data_create();rig.animation_data.action=action;scene.render.fps=480;scene.render.fps_base=1
        previous_q={}
        for f,p in enumerate(poses):
            scene.frame_set(f);apply_pose(p)
            for b in rig.pose.bones:
                b.rotation_mode='QUATERNION'
                if b.name in previous_q and b.rotation_quaternion.dot(previous_q[b.name])<0:b.rotation_quaternion.negate()
                previous_q[b.name]=b.rotation_quaternion.copy()
                for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f,group=b.name)
        rig.animation_data.action_slot=action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for k in curve.keyframe_points:k.interpolation='LINEAR'
        rig.animation_data_clear()
        record['variants'][variant]['clips'][clip]={'asset':info['asset'],'intervals':info['intervals'],'seconds':info['seconds']}
(P/'authoring.json').write_text(json.dumps(record,indent=2))
rig.animation_data_create();rig.animation_data.action=bpy.data.actions['GuardV23_Standard_Guard']
rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_start=0;scene.frame_end=96;scene.frame_set(96)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuardPalmPushV23_Editable.blend'))
print('GUARD_PALM_V23_AUTHORED',flush=True)
