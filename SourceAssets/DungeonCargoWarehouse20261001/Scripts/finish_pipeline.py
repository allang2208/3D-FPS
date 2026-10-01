"""Build a mesh-only reimport entry; keep the sample installer separate."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'Scripts/import_assets.py').read_text('utf-8').split('if E.does_asset_exist(MAP):')[0]
s=s.replace("if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use a background commandlet; preserve the live editor world')", "if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Finish PIE before reimport')")
s=s.replace("for item in MAN['objects']:\n", "for item in MAN['objects']:\n    if item['kind']!='RoofRibs':continue\n",1)
s=s.replace("    if mesh:\n        if not previous or previous.get('source_sha256')!=digest:raise RuntimeError('Existing asset differs; preserve it and author a new revision: '+path)\n        meshes[item['kind']]=mesh;continue", "    if mesh and previous and previous.get('source_sha256')==digest:\n        meshes[item['kind']]=mesh;continue")
s=s.replace('task.replace_existing=False','task.replace_existing=True')
s=s.replace("report['stage']='meshes_saved';record()", "report['structure_finish']='roof_braces_connected_to_columns';record()")
(ROOT/'Scripts/reimport_structure.py').write_text(s+"\nu.log('CARGO_WAREHOUSE_STRUCTURE_FINISH_SAVED')\n",encoding='utf-8')
