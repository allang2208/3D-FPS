"""Save the additional 25% whirlwind range after the matching native build."""
from pathlib import Path
import json
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/WhirlwindRange20261007')
(OUT / 'Records').mkdir(parents=True, exist_ok=True)
bp = u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
cdo = u.get_default_object(bp.generated_class())
before = cdo.get_editor_property('whirlwind_trigger_range')
cdo.set_editor_property('whirlwind_trigger_range', 308.75)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save M14 whirlwind range')
report = dict(complete=True, saved=[bp.get_path_name()], old_trigger_cm=before,
    trigger_cm=308.75, outer_radius_cm=203.125, contact_radius_cm=45.5,
    damage_outer_extent_cm=248.625, additional_range_multiplier=1.25,
    tested=False, rendered=False, user_testing_pending=True)
(OUT / 'Records/ue_revision.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M14_WHIRLWIND_RANGE_20261007_SAVED')
