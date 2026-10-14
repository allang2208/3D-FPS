"""Save the three refined meshes in place; map transforms and gameplay stay saved."""
from pathlib import Path
import json,runpy,unreal as u
ROOT=Path(__file__).resolve().parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active gameplay')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
items=[i for i in json.loads((ROOT/'geometry.json').read_text('utf-8-sig'))['meshes'] if 'previous_sha256' in i]
if any(i['mesh'] in dirty for i in items):raise RuntimeError('Preserve unsaved mesh changes')
import_mesh=runpy.run_path(str(ROOT/'install.py'))['import_mesh'];saved=[]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for item in items:
        item['force_reimport']=True;item['authored_tangents']=True;item.pop('tangent_basis',None);saved.append(import_mesh(item))
finally:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX '+str(previous))
manifest=json.loads((ROOT/'geometry.json').read_text('utf-8-sig'))
for item in manifest['meshes']:
    if item['mesh'] in saved:item['authored_tangents']=True;item.pop('tangent_basis',None)
(ROOT/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
receipt=ROOT/'Receipts/install.json';report=json.loads(receipt.read_text('utf-8-sig'))
report['refined_uv_assets']=saved;report['uv_source']=json.loads((ROOT/'Receipts/uv-source.json').read_text('utf8'))
report['equipment_tangents']='Authored MikkTSpace with double-precision UV derivative fallback for zero corners; full-precision import'
receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('FACILITY_UV_REFINEMENT_SAVED',len(saved))
