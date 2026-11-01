"""Save the dedicated Ji Lei animation, area indicator and standard icon."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1'
A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'saved':[],'runtime_tested':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (P/'motion_ui_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in json.loads((P/'motion.json').read_text(encoding='utf-8'))['clips']:
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
    opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt
    A.import_asset_tasks([task]);clip=u.load_asset(D+'/'+name)
    if not clip or not task.imported_object_paths:raise RuntimeError('Import failed '+name)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    clip.set_editor_property('rate_scale',1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+name)
    u.EditorAssetLibrary.set_metadata_tag(clip,'JiLeiMotion','V1 fixed right grip, relaxed left, single-hand charge and release')
    save(clip)
# Keep the same AoE grammar as the existing magic preview, in its own package.
aim=u.load_asset(D+'/M_JiLeiAim')
if not aim:
    aim=u.EditorAssetLibrary.duplicate_asset('/Game/Skills/FireMagic20260921/PreviewSurface20261022/M_MeteorAimPreview',D+'/M_JiLeiAim')
if not aim:raise RuntimeError('Missing AoE preview material source')
save(aim)
key='ue_thunder_god_hammer_head_mount_ji_lei_seat'
folder='/Game/ColdSteelData/AttachmentIcons20260913'
task=u.AssetImportTask();task.filename=str(R/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png'))
task.destination_path=folder;task.destination_name=key;task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
A.import_asset_tasks([task]);icon=u.load_asset(folder+'/'+key)
if not icon:raise RuntimeError('Icon import failed')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
save(icon)
receipt['complete']=True
(P/'motion_ui_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('JI_LEI_MOTION_UI_SAVED',flush=True)
