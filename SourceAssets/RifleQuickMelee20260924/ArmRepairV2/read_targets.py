"""Read current import ownership and editor state for the scoped replacement."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;jobs=json.loads((O.parent/'authoring.json').read_text())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report={'PIE_active':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'targets':{}}
for key,info in jobs.items():
 a=u.load_asset(info['path'])
 if not a:raise RuntimeError('Missing current animation '+info['path'])
 report['targets'][key]={'path':info['path'],'source':a.get_editor_property('asset_import_data').get_first_filename(),'dirty':info['path'] in dirty}
(O/'runtime_targets.json').write_text(json.dumps(report,indent=2))
print('ARM_SKIN_TARGETS',json.dumps(report),flush=True)
