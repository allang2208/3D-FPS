from pathlib import Path
import json,unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/KnockdownGroundV21')
report=dict(pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),dirty_m66=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith('/Game/Monsters/IncineratorBossM66/')])
(ROOT/'Records/editor-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_RECOVERY_EDITOR_STATE '+json.dumps(report))
