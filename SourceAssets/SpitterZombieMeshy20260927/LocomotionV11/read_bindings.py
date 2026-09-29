import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bp=u.load_asset('/Game/Monsters/SpitterZombie/BP_SpitterZombie');cdo=u.get_default_object(bp.generated_class())
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(pie=bool(level and level.is_in_play_in_editor()),
    movements=[a.get_path_name() if a else None for a in cdo.get_editor_property('movement_clips')],
    speeds=list(cdo.get_editor_property('movement_reference_speeds')),
    attack=cdo.get_editor_property('attack_clip').get_path_name(),
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        if p.get_path_name().startswith('/Game/Monsters/SpitterZombie/')])
(ROOT/'bindings_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SPITTER_V11_BINDINGS '+json.dumps(report))
