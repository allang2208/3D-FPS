"""Save the range increase after building the matching native collision code."""
from pathlib import Path
import json, shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004'
OUT=ROOT/'ProductionV20'
(OUT/'Records').mkdir(parents=True,exist_ok=True)
(OUT/'Before').mkdir(parents=True,exist_ok=True)
backup=OUT/'Before/BP_SpiralPillarM14.uasset'
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset',backup)
bp=u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
cdo=u.get_default_object(bp.generated_class())
before=cdo.get_editor_property('whirlwind_trigger_range')
cdo.set_editor_property('whirlwind_trigger_range',247.)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):
    raise RuntimeError('Could not save M14 whirlwind range')
report=dict(complete=True,saved=[bp.get_path_name()],old_trigger_cm=before,
    trigger_cm=247.,outer_radius_cm=162.5,contact_radius_cm=36.4,
    damage_outer_extent_cm=198.9,range_multiplier=1.3,
    tested=False,rendered=False,user_testing_pending=True)
(OUT/'Records/ue_revision.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
manifest_path=ROOT/'source_manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8'))
manifest['production_v20']={'scope':'whirlwind trigger and contact range +30 percent',
    'trigger_cm':247.,'outer_radius_cm':162.5,'contact_radius_cm':36.4,
    'importer':'Tools/SpiralPillarM14/import_whirlwind_range_v20.py',
    'ue_saved':True,'tested':False,'user_testing_pending':True}
manifest['current_revision']='ProductionV20'
if 'pending_production_revisions' in manifest:
    manifest['pending_production_revisions']=[item for item in manifest['pending_production_revisions'] if item['revision']!='ProductionV20']
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V20_WHIRLWIND_RANGE_SAVED')
