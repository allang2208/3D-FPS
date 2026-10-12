"""User-requested audio coverage and current-default inventory; no playback or gameplay."""
import json
from pathlib import Path
import unreal as u

BASE = '/Game/Monsters/BellowSacLobber'
bp = u.load_asset(BASE + '/BP_BellowSacLobber')
cdo = u.get_default_object(bp.generated_class())
values = {key: cdo.get_editor_property(key) for key in (
    'blast_damage', 'shove_damage', 'lob_min_range', 'lob_max_range', 'preferred_range',
    'shove_range', 'aggro_radius', 'leash_radius', 'lob_cooldown_min', 'lob_cooldown_max')}
sounds = {}
for name in ('S_BellowFlight', 'S_BellowContact', 'S_BellowRupture', 'S_BellowFuse'):
    sound = u.load_asset(BASE + '/V04/Audio/' + name)
    sounds[name] = dict(asset=sound.get_path_name() if sound else None,
        duration=sound.get_editor_property('duration') if sound else None,
        active=name != 'S_BellowFuse')
components = [dict(component=c.get_name(), sound=str(c.get_editor_property('sound')))
              for c in cdo.get_components_by_class(u.AudioComponent)]
report = dict(defaults=values, projectile_sounds=sounds, monster_audio_components=components,
    animation_set=cdo.get_editor_property('animation_set').get_path_name(),
    code_coverage='Bellow actor, Wolf base and quadruped template have no creature sound events',
    missing=['alert', 'charge_and_release', 'death', 'footsteps', 'hurt', 'shove', 'idle_breath'],
    auditioned=False, game_run=False)
out = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/Records/audio_inventory_v09.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_AUDIO_V09 ' + json.dumps(report, ensure_ascii=False))
