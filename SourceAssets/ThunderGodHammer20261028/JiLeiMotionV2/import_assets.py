"""Replace only the two Ji Lei animation takes after preserving V1 packages."""
import datetime,hashlib,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1'
names=json.loads((P/'motion.json').read_text())['clips']
dirty={a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in names:
    if D+'/'+name in dirty:raise RuntimeError('Target animation has unsaved edits: '+name)
backup=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
receipt={'complete':False,'saved':[],'backup':str(backup),'previous':[],'gameplay_run':False}
for name in names:
    path=R/'Content/Weapons/ThunderGodHammer20261028/JiLeiSeatV1'/(name+'.uasset')
    shutil.copy2(path,backup/path.name)
    receipt['previous'].append({'asset':D+'/'+name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record()
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
A=u.AssetToolsHelpers.get_asset_tools()
for name in names:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
    opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_name=name;t.destination_path=D
    t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt
    A.import_asset_tasks([t]);clip=u.load_asset(D+'/'+name)
    if not clip or not t.imported_object_paths:raise RuntimeError('Animation import failed '+name)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    clip.set_editor_property('rate_scale',1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation finalize failed '+name)
    clip.modify()
    u.EditorAssetLibrary.set_metadata_tag(clip,'JiLeiMotion','V2 visible forward lift; continuous elbow swivel; matched reverse recovery')
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()],False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append({'asset':clip.get_path_name(),'length':clip.get_play_length()});record()
receipt['complete']=True;record()
# User requested diagnosis: read these two saved data models and the active
# native surface for scoped pose/skin comparison, without starting gameplay.
reader=P/'read_assets.py'
exec(compile(reader.read_text(encoding='utf-8'),str(reader),'exec'),{'__file__':str(reader),'__name__':'__main__'})
print('JI_LEI_MOTION_V2_SAVED',flush=True)
