from pathlib import Path
import unreal as u,json
O=Path(__file__).resolve().parent
targets={r['path'] for r in json.loads((O/'Inputs/manifest.json').read_text()).values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
result={'project':str(Path(u.Paths.project_dir()).resolve()),'pie_active':bool(editor.get_game_world()),'dirty_targets':sorted(targets&dirty)}
(O/'editor-probe.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
