"""Replace only the two active throw clips; no mesh, gameplay or recall edits."""
import unreal as u,json,shutil,hashlib,datetime
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
motion=json.loads((P/'motion.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved':[],'runtime_tested':False,'preview_rendered':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record();backup=P/('BeforeImport-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
A=u.AssetToolsHelpers.get_asset_tools();old=[]
for name in motion['clips']:
    file=R/'Content/Weapons/ThunderGodHammer20261028/ThunderThrowV1'/(name+'.uasset')
    if file.exists():shutil.copy2(file,backup/file.name);old.append({'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt
    A.import_asset_tasks([t]);clip=u.load_asset(D+'/'+name)
    if not clip:raise RuntimeError('Import failed '+name)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    clip.set_editor_property('rate_scale',1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+name)
    u.EditorAssetLibrary.set_metadata_tag(clip,'ThunderThrowRevision','ThrowRefineV3: arm-root clearance, hinged elbows, V9 twist 100/50, staggered release')
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()],False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append(clip.get_path_name());record()
(backup/'manifest.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
receipt.update(complete=True,backup=str(backup),weapon_track='Existing authored WPN_root retained; launch header unchanged',runtime_paths='Existing Charge and Throw references reused');record()
print('THUNDER_THROW_REFINE_V3_IMPORTED',flush=True)
