"""Current saved native geometry and dense animation, scoped to bipod/idle/aim."""
from pathlib import Path
import unreal as u,pickle,json,hashlib
r=Path(__file__).resolve().parent
# Reuse the proven geometry extractor, excluding its old reload reads and probes.
code=(r.parent/'Repair06/collect.py').read_text().split("for role in ('idle','reload','reload_empty'):")[0]
exec(compile(code,'M249_current_geometry','exec'))
paths={'bipod':'/Game/Weapons/M249/Bipod/A_M249_Bipod','idle':'/Game/Weapons/M249/Animations/A_M249_idle','aim':'/Game/Weapons/M249/Animations/A_M249_idle'}
for role,path in paths.items():
    clip=u.load_asset(path);dm=clip.get_editor_property('data_model_interface');rate=dm.get_frame_rate();native=rate.numerator/rate.denominator
    fps=600 if role=='bipod' else native;count=round(clip.get_play_length()*fps)+1 if role!='aim' else 1
    rows=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)] for i in range(count)]
    with (r/(role+'_saved.pkl')).open('wb') as f:pickle.dump(dict(names=names,parents=d['parents'],fps=fps,duration=clip.get_play_length(),frames=rows,path=path),f)
    print('M249_BIPOD_CURRENT',role,count,flush=True)
profile=u.load_asset('/Game/Weapons/M249/Bipod/DA_M249_Bipod')
(r/'current_assets.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')],
    slots=[dict(slot=str(s.material_slot_name),imported=str(s.imported_material_slot_name),material=s.material_interface.get_path_name()) for s in mesh.materials],
    profiles=[dict(base=c.get_editor_property('base').get_path_name(),duration=c.get_editor_property('duration'),tracks=len(c.get_editor_property('tracks'))) for c in profile.get_editor_property('clips')]),indent=2))
