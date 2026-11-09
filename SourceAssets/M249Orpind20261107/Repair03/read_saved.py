"""Focused round-trip inspection: native key times, V9 shapes and optical slots."""
from pathlib import Path
import unreal as u,json,gzip,math
r=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
report=dict(morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')],clips={},slots=[])
for s in mesh.materials:
    report['slots'].append(dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name()))
for role in ('idle','reload','reload_empty'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role)
    dm=clip.get_editor_property('data_model_interface');count=dm.get_number_of_keys();rate=dm.get_frame_rate()
    fps=rate.numerator/rate.denominator
    with gzip.open(r.parent/'Motion'/f'{role}.json.gz','rt',encoding='utf8') as f:authored=json.load(f)
    names=list(authored['tracks']);pos_error=rot_error=scale_error=0.
    # Include both sides of all authored stop/return contacts, plus regular keys.
    frames=sorted(set(range(0,count,8))|{count-1}|{min(count-1,round(t*fps)) for t in (1.34,2.17,3.55,4.7,5.13,5.36,5.48,5.78,5.82)})
    for i in frames:
        poses=u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)
        for n,p in zip(names,poses):
            rows=authored['tracks'][n]
            expected=rows[0 if len(rows)==1 else i]
            pos_error=max(pos_error,math.dist(p.translation.to_tuple(),expected[:3]))
            q=(p.rotation.x,p.rotation.y,p.rotation.z,p.rotation.w);ref=expected[3:7]
            dot=abs(sum(a*b for a,b in zip(q,ref)))/math.sqrt(sum(a*a for a in q)*sum(a*a for a in ref))
            rot_error=max(rot_error,math.degrees(2*math.acos(min(1.,dot))))
            scale_error=max(scale_error,math.dist(p.scale3d.to_tuple(),expected[7:]))
    report['clips'][role]=dict(keys=count,fps=fps,seconds=clip.get_play_length(),samples=len(frames),max_local_position_error=pos_error,max_rotation_error_degrees=rot_error,max_scale_error=scale_error)
groups=[]
for key in ('holographic','magnifier'):
    p='/Game/Weapons/M249/Assembly/SM_M249_'+key;a=u.load_asset(p)
    groups.append(dict(name=key,parts=[dict(mesh=p,after=[s.material_interface.get_path_name() for s in a.static_materials])],camera_cm=[30,22,26],target_cm=[0,0,0]))
(r/'optic_surface_manifest.json').write_text(json.dumps(dict(after_only=True,groups=groups),indent=2))
for name in ('M_M249_OpticHousing','M_M249_Glass'):
    m=u.load_asset('/Game/Weapons/M249/Materials/'+name)
    report[name]=dict(blend=str(m.get_editor_property('blend_mode')),two_sided=m.get_editor_property('two_sided'))
(r/'saved_inspection.json').write_text(json.dumps(report,indent=2))
print('M249_REPAIR03_SAVED_INSPECTION',len(report['morphs']),json.dumps(report['clips']),flush=True)
