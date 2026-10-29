"""Read-only engine load of the configured body animations, without PIE or saving."""
from pathlib import Path
import json
import unreal as u

OUT = Path(__file__).resolve().parent
config = json.loads((OUT.parents[1]/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
rows=[]
for body, section in [('jason',config),('kaitlin',config['body_variants']['kaitlin'])]:
    mesh=u.load_asset(section['body_mesh'])
    skeleton=mesh.get_editor_property('skeleton') if mesh else None
    for role,path in section['clips'].items():
        if not (role.startswith('Kukri.FullBody.') or role.startswith('Pistol.KukriCarry.')):
            continue
        asset=u.load_asset(path)
        is_anim=isinstance(asset,u.AnimSequence)
        asset_skeleton=asset.get_editor_property('skeleton') if is_anim else None
        rows.append(dict(body=body,role=role,path=path,loaded=asset is not None,is_animation=is_anim,
                         duration=asset.get_play_length() if is_anim else None,
                         exact_skeleton_match=bool(asset_skeleton and asset_skeleton==skeleton),
                         skeleton=asset_skeleton.get_path_name() if asset_skeleton else None))
report=dict(assets=rows,failures=[r for r in rows if not r['is_animation'] or not r['exact_skeleton_match'] or r['duration']<=0],
            gameplay_started=False,assets_saved=False)
(OUT/'engine-assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KUKRI_AUDIT_ASSETS',len(rows),'FAILURES',len(report['failures']))
