"""Read saved Super90 timing for the user's reported too-fast reload.

No game world, animation playback, capture, render, or asset save.
"""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
ANIM='/Game/Weapons/Super90/Speedloader20261007/Animations/'
out={'animations':[],'profiles':{},'game_started':False}
for branch in ('normal','empty'):
    for count in range(1,8):
        name='A_Super90_loader_'+branch+'_'+str(count)
        obj=u.load_asset(ANIM+name)
        if not obj:raise RuntimeError('Missing animation '+name)
        out['animations'].append(dict(name=name,duration=float(obj.get_play_length()),
            rate_scale=float(obj.get_editor_property('rate_scale')),
            source=u.EditorAssetLibrary.get_metadata_tag(obj,'Super90SpeedloaderSource')))
for family in ('vertical','canted','prism','angled'):
    obj=u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family)
    out['profiles'][family]=[]
    for clip in obj.get_editor_property('clips'):
        base=clip.get_editor_property('base').get_path_name()
        if '_loader_normal_' in base or '_loader_empty_' in base:
            out['profiles'][family].append(dict(base=base,duration=float(clip.get_editor_property('duration'))))
(O/'saved_timing.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SUPER90_SAVED_TIMING',json.dumps(out['animations'],ensure_ascii=False),flush=True)
