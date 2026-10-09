"""Background import/save of the original loader prop, animations and grip layers."""
import unreal as u, json, shutil, hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/Super90/Speedloader20261007'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
M=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt={'completed':False,'saved':[],'profiles':{},'runtime_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:receipt['saved'].append(obj.get_path_name())
    record();return obj
def backup(obj):
    rel=obj.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset';src=P/'Content'/rel;dst=O/'Before'/rel
    if src.exists() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def material(name,metal,rough,color):
    path=D+'/Materials/MI_'+name
    obj=load(path) if E.does_asset_exist(path) else A.create_asset('MI_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    obj.set_editor_property('parent',load('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanAnodized'))
    values={'Metallic':metal,'EdgeMetallic':metal,'Roughness':rough,'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':0.,'GrainTileCm':2.,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0.,'ScratchAmount':0.,'HandlingPolish':0.,'Stipple':0.,'EdgeWear':0.,'EdgeHighlight':.06,'CavityDarken':0.,'CavityRoughness':0.,'AOStrength':0.,'WeaponWetness':0.}
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(obj,key,value)
    L.set_material_instance_vector_parameter_value(obj,'FinishColor',u.LinearColor(*color,1))
    L.set_material_instance_texture_parameter_value(obj,'SurfaceNormal',load('/Engine/EngineMaterials/DefaultNormal'))
    L.set_material_instance_texture_parameter_value(obj,'SurfaceMask',load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral'))
    L.update_material_instance(obj);E.set_metadata_tag(obj,'Super90SurfaceStandard','WS1 clean finish; dedicated UVs; flat structural normal; no original gun atlas')
    return save(obj)
materials={'S90Loader_Steel':material('S90Loader_Steel',1.,.42,(.025,.026,.028)),
           'S90Loader_Polymer':material('S90Loader_Polymer',0.,.54,(.018,.018,.019)),
           'S90Loader_Rod':material('S90Loader_Rod',1.,.30,(.13,.14,.15))}
skeleton=load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7').skeleton
def import_fbx(file,name,destination,kind):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=kind;opt.import_mesh=kind!=u.FBXImportType.FBXIT_ANIMATION
    opt.import_as_skeletal=kind==u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    if kind!=u.FBXImportType.FBXIT_STATIC_MESH:opt.skeleton=skeleton
    if kind==u.FBXImportType.FBXIT_STATIC_MESH:
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    elif kind==u.FBXImportType.FBXIT_SKELETAL_MESH:
        opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    else:
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=destination
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('FBX import failed '+name)
    obj=load(destination+'/'+name)
    E.set_metadata_tag(obj,'Super90SpeedloaderSource','Original game prop / authored native V7 animation; reference timing BV11wTe6sEsS 40-44s')
    E.set_metadata_tag(obj,'Super90SourceSHA256',hashlib.sha256(Path(file).read_bytes()).hexdigest())
    return obj
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    guide=import_fbx(M['meshes']['guide'],'SM_Super90_LoaderGuide',D,u.FBXImportType.FBXIT_STATIC_MESH)
    slots=list(guide.static_materials)
    for index,slot in enumerate(slots):slot.material_interface=materials[str(slot.material_slot_name)];slots[index]=slot
    guide.set_editor_property('static_materials',slots);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(guide)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings=editor.get_lod_build_settings(guide,0);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(guide,0,settings);save(guide)
    props=import_fbx(M['meshes']['props'],'SK_Super90_LoaderProps',D,u.FBXImportType.FBXIT_SKELETAL_MESH)
    slots=list(props.materials)
    for index,slot in enumerate(slots):slot.material_interface=materials[str(slot.material_slot_name)];slots[index]=slot
    props.set_editor_property('materials',slots);props.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(props,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(props,0,settings);save(props)
    compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    for clip in M['clips']:
        obj=import_fbx(clip['file'],clip['name'],D+'/Animations',u.FBXImportType.FBXIT_ANIMATION)
        obj.set_editor_property('bone_compression_settings',compression);save(obj)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
# Preserve the installed grip profiles and all older actions as plain data before
# replacing the reflected array; no live struct references survive the mutation.
for family in ('vertical','canted','prism','angled'):
    asset=load('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family);backup(asset)
    combined={'family':family,'clips':[]};retained={}
    for clip in asset.get_editor_property('clips'):
        base=clip.get_editor_property('base').get_path_name()
        if base.startswith(D+'/Animations/'):continue
        combined['clips'].append({'base':base,'duration':float(clip.get_editor_property('duration')),'tracks':[
            {'bone':str(track.get_editor_property('bone')),'times':list(track.get_editor_property('times')),'values':list(track.get_editor_property('values'))} for track in clip.get_editor_property('tracks')]})
        retained_clip=clip.get_editor_property('retained')
        if retained_clip:retained[base]=retained_clip
    combined['clips'].extend(json.loads((O/(family+'_profiles.json')).read_text(encoding='utf-8'))['clips'])
    if not asset.set_shared_clips_from_json(json.dumps(combined)):raise RuntimeError('Grip extension failed '+family)
    if retained:
        rows=list(asset.get_editor_property('clips'))
        for index,clip in enumerate(rows):
            base=clip.get_editor_property('base').get_path_name()
            if base in retained:clip.set_editor_property('retained',retained[base]);rows[index]=clip
        asset.set_editor_property('clips',rows)
    E.set_metadata_tag(asset,'Super90SpeedloaderGrip','Native left arm entry/return layers; original actions retained')
    save(asset);receipt['profiles'][family]={'path':asset.get_path_name(),'clip_count':len(combined['clips'])};record()
icon_name='reload_device_super90_tube_loader'
icon_dir='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
icon_png=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(icon_name+'.png')
shutil.copy2(O/'speedloader_framed.png',icon_png)
task=u.AssetImportTask();task.filename=str(icon_png);task.destination_path=icon_dir;task.destination_name=icon_name
task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
icon=load(icon_dir+'/'+icon_name);icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI
icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.srgb=True;icon.never_stream=True
E.set_metadata_tag(icon,'Super90SpeedloaderIcon','Built-in imagegen: exact authored prop reference + approved FramedFirearms mother; source recipe in Super90Speedloader20261007')
save(icon)
receipt['completed']=True;record();print('SUPER90_SPEEDLOADER_ASSETS_SAVED',len(receipt['saved']),flush=True)
