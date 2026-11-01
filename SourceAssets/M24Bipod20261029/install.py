"""Import fitted PKM geometry and native V9 hand clips, then save their profile."""
import unreal as u,json,gzip
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/Bipod20261029';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'saved':[],'runtime_tested':False,'rendered':False}
animations_only=globals().get('ANIMATIONS_ONLY',False)
receipt_path=O/('Quick048/install_receipt.json' if animations_only else 'install_receipt.json')
def save(ob):
    if not E.save_loaded_asset(ob,False):raise RuntimeError('Could not save '+ob.get_path_name())
    receipt['saved'].append(ob.get_path_name());receipt_path.write_text(json.dumps(receipt,indent=2))
if any(p.get_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved bipod edits retained')
source=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Bipod26/SM_PKM_Bipod_Base')
material=source.static_materials[0].material_interface
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for part in (() if animations_only else ('Base','LegA','LegB')):
        name='SM_M24_Bipod_'+part;opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
        task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Bipod mesh import failed '+part)
        slots=mesh.static_materials
        for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
        mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'Source','PKM Bipod26; M24 fitted collar, 80% leg length');save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
with gzip.open(O/'authored.json.gz','rt',encoding='utf-8') as f:spec=json.load(f)
rig=u.load_asset(spec['mesh']);factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',rig.skeleton);factory.set_editor_property('preview_skeletal_mesh',rig)
clips=[]
for family,entry in spec['clips'].items():
    name='A_M24_Bipod_'+family;path=D+'/'+name
    clip=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,D,u.AnimSequence,factory)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Initialize clip '+family)
    ctl=clip.get_editor_property('controller');frames=entry['frames'];ctl.open_bracket('Author M24 folding bipod hands',False)
    try:
        # Bridge the previous 120 Hz source to 200 Hz through their common multiple.
        # UE permits only integral frame-rate ratios on an already populated model.
        ctl.set_frame_rate(u.FrameRate(600,1),False)
        ctl.set_frame_rate(u.FrameRate(spec['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for j,bone in enumerate(spec['names']):
            ctl.add_bone_curve(bone,False);keys=[f[j] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError('Write bone '+bone)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate clip '+family)
    finally:ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(rig);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    E.set_metadata_tag(clip,'ContactTimeline','One pull 0.12-0.30 opens both legs; support hand returned 0.44; seat 0.48; reversible')
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize clip '+family)
    save(clip);clips.append({'base':clip.get_path_name(),'duration':spec['duration'],'tracks':[]})
name='DA_M24_Bipod';profile=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else None
if profile is None:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile);profile=A.create_asset(name,D,u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json(json.dumps({'family':'bipod','clips':clips})):raise RuntimeError('Write bipod profile')
save(profile);receipt['complete']=True;receipt['material']=material.get_path_name();receipt['duration']=spec['duration'];receipt_path.write_text(json.dumps(receipt,indent=2))
print('M24_BIPOD_ASSETS_SAVED',len(receipt['saved']),flush=True)
