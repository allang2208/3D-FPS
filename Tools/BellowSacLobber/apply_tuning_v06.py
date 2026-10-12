"""Save the M-09 name and four-second lob interval without changing animation assets."""
import json
from pathlib import Path
import unreal as u

TARGET = '/Game/Monsters/BellowSacLobber/BP_BellowSacLobber'
if not globals().get('BELLOW_COMMANDLET', False):
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Finish PIE before saving the monster Blueprint')
if any(p.get_path_name() == TARGET for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Target Blueprint has unsaved edits')

bp = u.load_asset(TARGET)
if not bp:
    raise RuntimeError('Monster Blueprint is missing')
cdo = u.get_default_object(bp.generated_class())
values = {'monster_display_name': '鼓囊 M-09', 'lob_cooldown_min': 4.0, 'lob_cooldown_max': 4.0}
for name, value in values.items():
    cdo.set_editor_property(name, value)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Monster Blueprint could not be saved')

report = {
    'blueprint': bp.get_path_name(),
    'saved_defaults': values,
    'lob_interval_semantics': 'start-to-start, including the 2.2-second attack animation',
    'ground_fuse_audio': 'disabled in BellowSacProjectile.cpp',
    'runtime_tested': False,
}
out = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/Records/ue_tuning_v06.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_TUNING_V06_SAVED ' + bp.get_path_name())
