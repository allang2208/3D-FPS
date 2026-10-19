"""Save the finished knit/cotton packages while chainmail cuff work continues."""
import runpy,json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
scope=runpy.run_path(str(P/'Tools/GarmentSleeveRepair/save_assets.py'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Do not replace clothing during PIE')
for row in json.loads((R/'inventory.json').read_text())['rows']:
    if row['item']=='ue_field_sweater' or (row['item']=='ue_field_sweater_charcoal' and row['profile'] in ('SVD','Super90')):
        scope['write_mesh'](row);gc.collect();u.SystemLibrary.collect_garbage()
print('KNIT_COTTON_PACKAGES_SAVED',flush=True)
