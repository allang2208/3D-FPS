"""Bake the ordinary-attack left palm contact for Static Field / Coil only.

Read the saved native poses (including BareSkin fixes), keep weapon, right arm,
finger locals and intentional hand exchanges; publish a small grip layer.
"""
import ast,json,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/NormalGripFix20261031'
NAME='DA_ThunderHammer_ConductiveGrip'
BASE='/Game/Weapons/SteelWarhammer20261014/NormalComboV4/'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve active PIE')
existing=u.load_asset(D+'/'+NAME) if u.EditorAssetLibrary.does_asset_exist(D+'/'+NAME) else None
if existing:
    if u.EditorAssetLibrary.get_metadata_tag(existing,'ThorGrip.Scope')!='static_field_grip,coil_grip; ordinary three-hit combo and recoveries':
        raise RuntimeError('Preserve an asset not owned by this repair')
    if existing.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Preserve unsaved profile edits')

# Pure vector/quaternion helpers from the established modular-grip authoring.
module=ast.parse((R/'SourceAssets/FrostSwordGrips20260919/author_long_grip_animation.py').read_text(encoding='utf-8'))
helpers={'add','sub','mul','dot','length','unit','cross','inverse','qmul','rotate','between','unpack','smooth'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<grip_math>','exec'))

mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=mesh
comp=u.AnimPoseEvaluationOptions();comp.evaluation_type=u.AnimDataEvalType.COMPRESSED;comp.optional_skeletal_mesh=mesh
anim=u.load_asset(BASE+'A_Warhammer_Slash1')
pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,opt)
bones=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
parents={n:str(component.get_parent_bone(n)) for n in bones}
chain=['upperarm_l','lowerarm_l','hand_l']
twists=[n for n in bones if n.startswith(('upperarm_twist','lowerarm_twist')) and n.endswith('_l')]
changed=['clavicle_l']+chain+twists+(['ik_hand_l'] if 'ik_hand_l' in bones else [])
read_names=set(changed+['WPN_root'])|{parents[n] for n in changed}
def world(p):return {n:unpack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)) for n in read_names}
def local(a,b):
    return {'p':tuple(v/s for v,s in zip(rotate(inverse(b['q']),sub(a['p'],b['p'])),b['s'])),
            'q':unit(qmul(inverse(b['q']),a['q'])),'s':tuple(x/y for x,y in zip(a['s'],b['s']))}
def apply_point(a,p):return add(a['p'],rotate(a['q'],tuple(v*s for v,s in zip(p,a['s']))))
def inverse_point(a,p):return tuple(v/s for v,s in zip(rotate(inverse(a['q']),sub(p,a['p'])),a['s']))

idle=world(pose);wi=idle['WPN_root'];hi=idle['hand_l']
centre=(-.00045,.00105) # measured Thor shaft centre in imported WPN coordinates
idle_wp=inverse_point(wi,hi['p'])
anchor=inverse_point(hi,apply_point(wi,(*centre,idle_wp[2])))
legacy=u.load_asset('/Game/Weapons/SteelWarhammer20261014/RhythmClearanceV2/DA_Warhammer_Clearance')
document={'family':'thunder_conductive_grip_contact','clips':[]}
for clip in legacy.get_editor_property('clips'):
    if clip.get_editor_property('retained'):raise RuntimeError('Unexpected retained legacy clip')
    document['clips'].append({'base':clip.get_editor_property('base').get_path_name(),
        'duration':clip.get_editor_property('duration'),'tracks':[
            {'bone':str(tr.get_editor_property('bone')),'times':list(tr.get_editor_property('times')),
             'values':list(tr.get_editor_property('values'))} for tr in clip.get_editor_property('tracks')]})
receipt={'assets':[],'clips':{},'runtime_tested':False,'normal_attacks_only':True}

def correct(src,swap):
    out={n:{k:v for k,v in tr.items()} for n,tr in src.items()}
    w,h=src['WPN_root'],src['hand_l']
    palm=inverse_point(w,apply_point(h,anchor))
    err=(centre[0]-palm[0],centre[1]-palm[1],0.)
    gap=math.hypot(*err[:2])
    # The authored swap lifts the palm ~9 cm. It is a release, not a contact
    # failure: leave it intact and blend into the correction only on regrip.
    wrist_local=inverse_point(w,h['p'])
    radius=math.hypot(wrist_local[0]-centre[0],wrist_local[1]-centre[1])
    weight=1.-smooth((radius-.071)/.016) if swap else 1.
    delta=rotate(w['q'],tuple(v*s*weight for v,s in zip(err,w['s'])))
    shoulder,elbow,wrist=[src[n]['p'] for n in chain]
    goal=add(wrist,delta);upper=sub(elbow,shoulder);fore=sub(wrist,elbow)
    l1,l2=length(upper),length(fore);reach=sub(goal,shoulder);dist=length(reach)
    # Never straighten an already-extended authored arm further. A sub-centimetre
    # clavicle support shift retains its bend while keeping the palm on the grip.
    old_ratio=length(sub(wrist,shoulder))/(l1+l2)
    support=mul(unit(reach),max(0.,dist-max(.96,old_ratio)*(l1+l2)))
    shoulder=add(shoulder,support);reach=sub(goal,shoulder);dist=length(reach)
    if dist>=l1+l2-.001 or dist<=abs(l1-l2)+.001:
        raise RuntimeError('Contact correction exceeds native arm reach')
    axis=unit(reach);guide=sub(upper,mul(axis,dot(upper,axis)))
    if length(guide)<1e-6:raise RuntimeError('Degenerate authored elbow pole')
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    e=add(add(shoulder,mul(axis,along)),mul(unit(guide),math.sqrt(max(0.,l1*l1-along*along))))
    du=between(upper,sub(e,shoulder));dl=between(fore,sub(goal,e))
    out['clavicle_l']['p']=add(src['clavicle_l']['p'],support)
    out['upperarm_l']['p']=shoulder
    out['upperarm_l']['q']=unit(qmul(du,src['upperarm_l']['q']))
    out['lowerarm_l']['p']=e;out['lowerarm_l']['q']=unit(qmul(dl,src['lowerarm_l']['q']))
    out['hand_l']['p']=goal # palm orientation, finger curls and release timing survive
    for n in twists:
        pivot,target,q=(src['upperarm_l']['p'],shoulder,du) if n.startswith('upperarm') else (elbow,e,dl)
        out[n]['p']=add(target,rotate(q,sub(src[n]['p'],pivot)))
        out[n]['q']=unit(qmul(q,src[n]['q']))
    if 'ik_hand_l' in out:out['ik_hand_l']['p']=add(src['ik_hand_l']['p'],delta)
    final_palm=inverse_point(w,apply_point(out['hand_l'],anchor))
    return out,{'gap_before_mm':gap*1000,'gap_after_mm':math.hypot(final_palm[0]-centre[0],final_palm[1]-centre[1])*1000,
                'weight':weight,'wrist_shift_cm':length(delta),'support_shift_cm':length(support),'reach_ratio':dist/(l1+l2),'source_reach_ratio':old_ratio}

for stage in range(1,4):
    for suffix in ('','Recover'):
        name=f'A_Warhammer_Slash{stage}{suffix}';anim=u.load_asset(BASE+name)
        source_frames=u.AnimationLibrary.get_num_frames(anim);frames=source_frames*2;seconds=anim.get_play_length()
        tracks={n:{'bone':n,'times':[],'values':[]} for n in changed};stats=[]
        # Sample all frames before writing any asset; shared source is never mutated.
        for frame in range(frames+1):
            t=seconds*frame/frames;p=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,opt)
            src=world(p);target,m=correct(src,stage==2 and not suffix and t<.6);m['t']=t;stats.append(m)
            for n in changed:
                a=local(src[n],src[parents[n]]);b=local(target[n],target[parents[n]])
                q=unit(qmul(b['q'],inverse(a['q'])))
                if q[3]<0:q=mul(q,-1)
                tr=tracks[n];tr['times'].append(t);tr['values'].extend((*sub(b['p'],a['p']),*q,*sub(b['s'],a['s'])))
        # Compress only numerically zero tracks; retain high-speed contact keys.
        kept=[]
        for n,tr in tracks.items():
            v=tr['values']
            if max(max(abs(v[i+j]) for j in (0,1,2,3,4,5,7,8,9)) for i in range(0,len(v),10))>1e-7:kept.append(tr)
        document['clips'].append({'base':anim.get_path_name(),'duration':seconds,'tracks':kept})
        contact=[s for s in stats if s['weight']>1.-1e-6]
        free=[s for s in stats if s['weight']<1e-6]
        # Check compressed playback at contact/release samples against the layer.
        compressed_max=0.
        for sample in stats[::max(1,frames//120)]:
            t=sample['t']
            a=world(u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,opt))
            b=world(u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,comp))
            ca=inverse_point(a['WPN_root'],apply_point(a['hand_l'],anchor))
            cb=inverse_point(b['WPN_root'],apply_point(b['hand_l'],anchor))
            compressed_max=max(compressed_max,length(sub(ca,cb))*1000)
        receipt['clips'][name]={'frames':frames,'source_frames':source_frames,'seconds':seconds,'tracks':len(kept),
            'contact_before_max_mm':max(s['gap_before_mm'] for s in contact),'contact_after_max_mm':max(s['gap_after_mm'] for s in contact),
            'free_samples_preserved':len(free),'free_max_wrist_shift_cm':max([s['wrist_shift_cm'] for s in free] or [0]),
            'max_wrist_shift_cm':max(s['wrist_shift_cm'] for s in stats),'max_reach_ratio':max(s['reach_ratio'] for s in stats),
            'max_support_shift_cm':max(s['support_shift_cm'] for s in stats),'source_max_reach_ratio':max(s['source_reach_ratio'] for s in stats),
            'source_compressed_contact_difference_mm':compressed_max}
        print('THOR_GRIP_BAKED '+name+' '+json.dumps(receipt['clips'][name]))

(P/'contact_layer_editable.json').write_text(json.dumps(document,separators=(',',':')),encoding='utf-8')
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
asset=existing or u.AssetToolsHelpers.get_asset_tools().create_asset(NAME,D,u.WeaponGripProfile,factory)
if not asset or not asset.set_shared_clips_from_json(json.dumps(document)):raise RuntimeError('Grip layer import failed')
u.EditorAssetLibrary.set_metadata_tag(asset,'ThorGrip.Source','Saved native NormalComboV4, BareSkin corrections retained')
u.EditorAssetLibrary.set_metadata_tag(asset,'ThorGrip.Scope','static_field_grip,coil_grip; ordinary three-hit combo and recoveries')
if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Profile save failed')
receipt.update(complete=True,assets=[asset.get_path_name()],anchor_hand_local=list(anchor))
(P/'contact_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('THOR_GRIP_SAVED '+asset.get_path_name())
