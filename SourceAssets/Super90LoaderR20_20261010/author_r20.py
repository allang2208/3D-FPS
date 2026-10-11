"""R20 late-reload shoulder clearance, built on the saved R19 complete reload."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
params=json.loads((O/'phase_fit.json').read_text(encoding='utf-8'))['chosen']

def correct(p,f,end):
    a,b=params['release'],params['bolt'];t=smooth((f-122)/16)
    off=Vector(a['offset']).lerp(Vector(b['offset']),t);angle=a['angle']*(1-t)+b['angle']*t
    return support_pose(p,off,angle,envelope(f,end))

X=O/'Exports';X.mkdir(exist_ok=True)
report=dict(revision='LoaderR20-20261010',source=str(source),parameters=params,clips=[],
    scope='Normal and empty late reload; source hand, fingers, gun, audio and timing preserved',
    camera=dict(horizontal_fov=112,aspect=1276/837,author_anchor=camera),runtime_tested=False)
audit=dict(samples=0,max_bone_length_error_mm=0.,max_unchanged_world_error=0.,max_reach=0.,max_support_step_cm=0.,max_source_support_step_cm=0.,window=[88,144,180])

def compare(old,new,previous,oldprevious):
    audit['samples']+=1
    for n in names:
        if n not in changed:
            audit['max_unchanged_world_error']=max(audit['max_unchanged_world_error'],max(abs(old[n][i][j]-new[n][i][j]) for i in range(4) for j in range(4)))
    a,e,t=[new[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
    audit['max_reach']=max(audit['max_reach'],(t-a).length/((e-a).length+(t-e).length))
    for n,child in (('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')):
        audit['max_bone_length_error_mm']=max(audit['max_bone_length_error_mm'],abs((new[child].translation-new[n].translation).length-(old[child].translation-old[n].translation).length)*1000)
    if previous:
        for n in ('upperarm_l','lowerarm_l'):
            audit['max_support_step_cm']=max(audit['max_support_step_cm'],(new[n].translation-previous[n].translation).length*100)
            audit['max_source_support_step_cm']=max(audit['max_source_support_step_cm'],(old[n].translation-oldprevious[n].translation).length*100)

for branch,end in (('normal',144),('empty',180)):
    name='A_Super90_loader_'+branch+'_7';base=source_rows[branch]
    family_poses={fam:[adapt_profile(p,inputs[fam][name],f) for f,p in enumerate(base)] for fam in families}
    new=[correct(p,f,end) for f,p in enumerate(base)]
    new_family={fam:[correct(p,f,end) for f,p in enumerate(rows)] for fam,rows in family_poses.items()}
    for oldrows,newrows in [(base,new),*[(family_poses[f],new_family[f]) for f in families]]:
        for f,(p,q) in enumerate(zip(oldrows,newrows)):compare(p,q,newrows[f-1] if f else None,oldrows[f-1] if f else None)
    for count in range(1,8):
        clip_name='A_Super90_loader_'+branch+'_'+str(count)
        target=bpy.data.actions[clip_name];patch_action(target,new)
        rig.animation_data.action=target;rig.animation_data.action_slot=target.slots[0]
        scene.frame_start=0;scene.frame_end=end;scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        file=X/(clip_name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
            add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
        record=copy.deepcopy(manifest[clip_name]);record.update(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest());report['clips'].append(record)
        for fam in families:
            out=copy.deepcopy(inputs[fam][clip_name]);tracks={t['bone']:t for t in out['tracks']}
            for n in changed:
                values=[];previous=None
                for p,a in zip(new,new_family[fam]):
                    b=local_ue(p,n);t=local_ue(a,n);q=t.to_quaternion()@b.to_quaternion().inverted();q.normalize()
                    if (previous is not None and q.dot(previous)<0) or (previous is None and q.w<0):q.negate()
                    previous=q;values.extend([*(t.translation-b.translation),q.x,q.y,q.z,q.w,*(t.to_scale()-b.to_scale())])
                track=dict(bone=n,times=[f/60 for f in range(end+1)],values=values)
                if n in tracks:tracks[n].update(track)
                else:out['tracks'].append(track)
            profiles[fam]['clips'].append(out)
        print('R20_ARM_AUTHORED',clip_name,flush=True)
for fam,payload in profiles.items():(O/(fam+'_profiles.json')).write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=180;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R20.blend'))
report['source_checks']=audit
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_LOADER_R20_AUTHORED',len(report['clips']),json.dumps(audit),flush=True)
