"""Read only the current donor and five SVD empty-reload import records."""
import unreal as u
import os,json
from pathlib import Path
O=Path(__file__).parent
auth=json.loads((O.parent/'SVDThumbUp20260923/authoring.json').read_text())
targets={k:v['path'] for k,v in auth.items() if k.endswith('/reload_empty')}
targets['AKM/reference']='/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_reload_empty'
report={'pid':os.getpid(),'command_line':u.SystemLibrary.get_command_line(),'clips':{}}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report['editor_subsystem']=bool(editor)
report['PIE_active']=bool(editor and editor.get_game_world())
report['dirty_targets']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name() in targets.values()]
for key,path in targets.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing requested animation '+path)
 report['clips'][key]={'path':path,'source':a.get_editor_property('asset_import_data').get_first_filename(),'duration':a.get_play_length(),'skeleton':a.get_editor_property('skeleton').get_path_name()}
(O/'runtime_inputs.json').write_text(json.dumps(report,indent=2))
print('SVD_CHARGE_INPUTS',json.dumps(report))
