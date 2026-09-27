"""Save the requested movement/palm push tuning and inspect bound reaction assets."""
from pathlib import Path
import json
import shutil
import unreal as u

root = Path(__file__).resolve().parent
project = root.parents[1]
output = root / 'Mobility20260927'
if Path(u.Paths.project_dir()).resolve() != project.resolve():
    raise RuntimeError('Wrong UE project')
output.mkdir(parents=True, exist_ok=True)
paths = ['/Game/Monsters/FleshHand/BP_FleshHand', '/Game/Monsters/FleshHand/BP_FleshHandMinion']
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):
    raise RuntimeError('Preserving unsaved FleshHand Blueprint changes: ' + str(dirty.intersection(paths)))

def describe(clip):
    if clip is None:
        return None
    skeleton = clip.get_editor_property('skeleton')
    return {'asset': clip.get_path_name(), 'seconds': clip.get_play_length(),
            'skeleton': skeleton.get_path_name() if skeleton else None,
            'rate_scale': clip.get_editor_property('rate_scale')}

pending = []
for path in paths:
    bp = u.load_asset(path)
    if bp is None:
        raise RuntimeError('Missing hand Blueprint: ' + path)
    cdo = u.get_default_object(bp.generated_class())
    minion = path.endswith('Minion')
    settings = {'walk_speed': 324. if minion else 259.2,
                'animation_walk_speed': 270. if minion else 216.,
                'slam_knockback_distance': 150.}
    before = {key: cdo.get_editor_property(key) for key in settings}
    pending.append((bp, cdo, settings, before))

report = {'state': 'saving', 'saved': [], 'characters': {},
          'animation_assets': list(u.EditorAssetLibrary.list_assets('/Game/Monsters/FleshHand/Animations', True, False)),
          'reaction_scope': 'FleshHand main and minion only; source and saved bindings inspected',
          'missing_reactions': [],
          'missing_reaction_stage': 'Derived from current hand knockdown component bindings below',
          'runtime_tested': False, 'game_started': False}

def record():
    (output / 'installation_and_reactions.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

record()
for bp, cdo, settings, before in pending:
    name = bp.get_name()
    backup = (Path(__file__).resolve().parents[2] / 'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Mobility20260927/BeforeMobility') / (name + '.uasset')
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project / 'Content/Monsters/FleshHand' / (name + '.uasset'), backup)
    bp.modify()
    cdo.modify()
    for key, value in settings.items():
        cdo.set_editor_property(key, value)
    u.EditorAssetLibrary.set_metadata_tag(bp, 'FleshHand.Mobility', 'Speed120PercentPalmPush150cm20260927')
    if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError('Cannot save ' + bp.get_path_name())
    report['saved'].append(bp.get_path_name())
    combat = cdo.get_editor_property('combat')
    mesh = cdo.get_editor_property('visual_mesh')
    skeleton = mesh.get_editor_property('skeleton') if mesh else None
    clips = {role: describe(cdo.get_editor_property(prop)) for role, prop in
             [('walk', 'move_clip'), ('death', 'death_clip'), ('charge_recover', 'charge_recover_clip')]}
    clips.update(stagger=describe(combat.get_editor_property('hit_clip')),
                 stun=describe(combat.get_editor_property('dizzy_clip')))
    knockdown = cdo.get_editor_property('knockdown')
    for role in ('launch_palm', 'launch_back', 'air_palm', 'air_back', 'land_palm', 'land_back',
                 'down_palm', 'down_back', 'get_up_palm', 'get_up_back'):
        clips[role] = describe(knockdown.get_editor_property(role + '_clip')) if knockdown else None
        if clips[role] is None:
            report['missing_reactions'].append(name + ':' + role)
    report['characters'][name] = {'before': before,
        'saved_settings': {key: cdo.get_editor_property(key) for key in settings},
        'full_speed_move_rate': settings['walk_speed'] / settings['animation_walk_speed'],
        'visual_skeleton': skeleton.get_path_name() if skeleton else None,
        'clips': clips,
        'stagger_seconds': combat.get_editor_property('stagger_duration'),
        'toughness_break_seconds': combat.get_editor_property('toughness_break_seconds')}
    record()
report['state'] = 'assets_saved_and_reactions_inspected'
record()
print('FLESHHAND_MOBILITY_SAVED ' + str(output / 'installation_and_reactions.json'))
for name, row in report['characters'].items():
    print(name + ' ' + json.dumps(row, ensure_ascii=False))
