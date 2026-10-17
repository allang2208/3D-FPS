"""Save AKM-referenced arm support in all 13 M870 clips; preserve the incoming hand and sight tracks."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
ROOT='/Game/Weapons/M870/Tactical20261015'
auth=json.loads((O/'authoring.json').read_text())
assets=u.AssetToolsHelpers.get_asset_tools();library=u.EditorAssetLibrary
report=dict(saved=[],clips={},completed=False,runtime_tested=False,visual_tested=False,auditioned=False)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('M870 import deferred: the existing editor is playing; no animation assets were changed.')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
targets={ROOT+'/Animations/A_M870_'+role for role in auth['clips']}
if dirty.intersection(targets):raise RuntimeError('M870 animations have unsaved editor changes: '+str(sorted(dirty.intersection(targets))))
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([ROOT],True)
mesh=u.load_asset(ROOT+'/SK_M870_V7');compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if not mesh or not compression:raise RuntimeError('Installed M870 and compression assets are required')
report['skeleton']=mesh.skeleton.get_path_name()
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for role,entry in auth['clips'].items():
        name='A_M870_'+role;package=ROOT+'/Animations/'+name
        physical=P/'Content/Weapons/M870/Tactical20261015/Animations'/(name+'.uasset')
        backup=O/'Before/Animations'/physical.name;backup.parent.mkdir(parents=True,exist_ok=True)
        if physical.exists() and not backup.exists():shutil.copy2(physical,backup)
        task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=ROOT+'/Animations';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.skeleton=mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        task.options=options;task.factory=u.FbxFactory();assets.import_asset_tasks([task])
        clip=u.load_asset(package)
        if not clip or not task.imported_object_paths:raise RuntimeError('Animation import did not return '+package)
        clip.set_editor_property('bone_compression_settings',compression)
        if role=='quick_melee':
            curve='Super90MeleeArmAuthored'
            if u.AnimationLibrary.does_curve_exist(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,curve)
            u.AnimationLibrary.add_curve(clip,curve)
            u.AnimationLibrary.add_float_curve_keys(clip,curve,[0.,entry['duration']],[1.,1.])
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Cannot finalize M870 melee ownership')
        library.set_metadata_tag(clip,'M870AnimationAuthor','M870AKMArmSupport20261016')
        library.set_metadata_tag(clip,'M870AnimationSourceSHA256',hashlib.sha256(Path(entry['file']).read_bytes()).hexdigest())
        if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()],False):raise RuntimeError('Could not save '+package)
        report['saved'].append(clip.get_path_name());report['clips'][role]=dict(path=clip.get_path_name(),length=clip.get_play_length(),source=entry['file'])
        (O/'install_receipt.json').write_text(json.dumps(report,indent=2))
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
report['completed']=True;(O/'install_receipt.json').write_text(json.dumps(report,indent=2))
print('M870_AKM_SUPPORT_SAVED',len(report['saved']),'animations')
