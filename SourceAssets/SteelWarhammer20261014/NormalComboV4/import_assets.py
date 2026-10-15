"""Import and save ordinary hammer animations; never replace mesh/materials."""
import unreal as u
import json
from pathlib import Path

P=Path(__file__).resolve().parent
R=P.parents[2]
D='/Game/Weapons/SteelWarhammer20261014/NormalComboV4'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
source=json.loads((P/'authored.json').read_text())
receipt={'saved':[],'complete':False,'runtime_tested':False}
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in source['clips']:
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True
    opt.import_materials=False;opt.import_textures=False
    opt.skeleton=mesh.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',source['fps'])
    task=u.AssetImportTask()
    task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=D;task.destination_name=name
    task.automated=True;task.save=False
    task.replace_existing=True;task.replace_existing_settings=True;task.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    anim=u.load_asset(D+'/'+name)
    if not anim:raise RuntimeError('Animation import failed: '+name)
    anim.set_editor_property('bone_compression_settings',compression)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(anim):raise RuntimeError('Animation finalization failed: '+name)
    if not u.EditorLoadingAndSavingUtils.save_packages([anim.get_outermost()],False):raise RuntimeError('Animation save failed: '+name)
    receipt['saved'].append(anim.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_NORMAL_COMBO_SAVED '+json.dumps(receipt))
