"""Bake six arm corrections onto existing clips and save only the grip profile."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/SteelWarhammer20261014/RhythmClearanceV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
tools=u.AssetToolsHelpers.get_asset_tools()
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
profile=u.load_asset(D+'/DA_Warhammer_Clearance')
if profile:raise RuntimeError('Profile already exists; preserve saved production')
profile=tools.create_asset('DA_Warhammer_Clearance',D,u.WeaponGripProfile,factory)
profile.set_editor_property('family','warhammer_shoulder_clearance')
receipt={'clips':[],'saved':False,'gameplay_tested':False}
for spec in json.loads((P/'authored.json').read_text())['clips']:
    base=u.load_asset(spec['base'])
    if not base:raise RuntimeError('Missing base: '+spec['base'])
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=base.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',150)
    task=u.AssetImportTask();task.filename=spec['file'];task.destination_path=D+'/Authoring';task.destination_name=spec['name']
    task.automated=True;task.save=False;task.replace_existing=False;task.options=opt
    tools.import_asset_tasks([task])
    authored=u.load_asset(D+'/Authoring/'+spec['name'])
    if not authored or not profile.bake_clip(base,authored):raise RuntimeError('Profile bake failed: '+spec['name'])
    receipt['clips'].append({'base':base.get_path_name(),'source':spec['file'],'duration':base.get_play_length()})
# Authored sequences are temporary bake inputs, never saved or referenced by
# the runtime profile. The editable blend and FBXs remain recovery sources.
if not u.EditorLoadingAndSavingUtils.save_packages([profile.get_outermost()],False):raise RuntimeError('Profile save failed')
receipt.update(saved=True,asset=profile.get_path_name())
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_CLEARANCE_SAVED '+json.dumps(receipt))
