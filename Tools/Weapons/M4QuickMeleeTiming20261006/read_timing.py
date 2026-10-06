"""Read the requested M4 quick-melee timing and current grip-profile routing."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent

def sequence(clip):
    if not clip:
        return None
    return dict(path=clip.get_path_name(), length=clip.get_play_length(),
                rate_scale=clip.get_editor_property('rate_scale'))

rows = []
for family in ('Base', 'Drum', 'Angled', 'Vertical', 'Canted', 'Prism'):
    fallback = u.load_asset(f'/Game/Weapons/M4QuickMeleeReplica20260919/{family}/A_M4_QuickCombat_{family}')
    profile_path = f'/Game/Weapons/AnimationProfiles20261001/ue_m4a1/DA_{family.lower()}'
    profile = u.load_asset(profile_path) if u.EditorAssetLibrary.does_asset_exist(profile_path) else None
    row = dict(family=family, fallback=sequence(fallback), profile=profile_path if profile else None)
    row['selected'] = row['fallback']
    if profile:
        for layer in profile.get_editor_property('clips'):
            base = layer.get_editor_property('base')
            if base and any(k in base.get_name().lower() for k in ('quick_melee', 'quickcombat')):
                retained = layer.get_editor_property('retained')
                row.update(base=sequence(base), retained=sequence(retained),
                           layer_duration=layer.get_editor_property('duration'),
                           selected=sequence(retained or base))
                break
    rows.append(row)
report = dict(rows=rows, mutates_assets=False, starts_game=False)
(OUT / 'timing_before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M4_QUICK_MELEE_TIMING ' + json.dumps(report))
