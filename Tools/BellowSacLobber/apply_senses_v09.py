"""Save the damage/range/hearing revision after updating the native Editor module."""
import json
from pathlib import Path
import unreal as u

TARGET = '/Game/Monsters/BellowSacLobber/BP_BellowSacLobber'
if any(p.get_path_name() == TARGET for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Target Blueprint has unsaved changes')
bp = u.load_asset(TARGET)
cdo = u.get_default_object(bp.generated_class())
values = dict(blast_damage=48., shove_damage=24., lob_max_range=2800., preferred_range=1800.,
              shove_range=450., aggro_radius=3200., sound_sensitive=True, hearing_radius=3600.)
before = {name: cdo.get_editor_property(name) for name in values}
for name, value in values.items():
    cdo.set_editor_property(name, value)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save Bellow senses revision')
report = dict(blueprint=bp.get_path_name(), saved_defaults=values, before=before,
    animation_set=cdo.get_editor_property('animation_set').get_path_name(),
    remaining=dict(blast_radius=cdo.get_editor_property('blast_radius'),
        impact_fuse=cdo.get_editor_property('impact_fuse'),
        lob_min_range=cdo.get_editor_property('lob_min_range'),
        lob_cooldown_min=cdo.get_editor_property('lob_cooldown_min'),
        lob_cooldown_max=cdo.get_editor_property('lob_cooldown_max')),
    status='saved', runtime_tested=False, audio_assets_added=False)
out = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/Records/ue_senses_v09.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_SENSES_V09_SAVED ' + bp.get_path_name())
