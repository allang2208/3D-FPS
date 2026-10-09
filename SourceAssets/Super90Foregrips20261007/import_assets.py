"""Import/save fitted common grips and native pose layers without gameplay."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/Super90/Foregrips20261007'
M=json.loads((O/'models.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'completed':False,'saved':[],'meshes':{},'profiles':{},'runtime_tested':False}
sources={'vertical':'/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip','canted':'/Game/Weapons/M4CantedForegrip/SM_CantedForegrip','prism':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismHandstop'}
sources['tactical_vertical']='/Game/Weapons/TacticalVerticalForegrip20260919/M4/SM_TacticalVerticalForegrip'
sources['angled']='/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/M4/SM_ResonanceGrip'
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    path=obj.get_path_name()
    if path not in receipt['saved']:receipt['saved'].append(path)
    record();return obj
materials={}
def finish(source):
    path=source.get_path_name()
    if path in materials:return materials[path]
    name='M_Super90_Grip_'+hashlib.sha256(path.encode()).hexdigest()[:10]
    target=D+'/Materials/'+name
    mat=load(target) if E.does_asset_exist(target) else E.duplicate_asset(path,target)
    E.set_metadata_tag(mat,'Super90ForegripSourceMaterial',path)
    materials[path]=save(mat);return mat
saddle=finish(load('/Game/Weapons/Super90/Optics20261007/Materials/M_Super90_RailSteel'))
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,part in M['parts'].items():
        original=load(sources[key]);original_slots=list(original.static_materials)
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_mesh=True;opts.import_as_skeletal=False;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
        opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False;opts.static_mesh_import_data.generate_lightmap_u_vs=False
        opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=part['fbx'];task.destination_path=D+'/Meshes';task.destination_name='SM_Super90_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opts
        A.import_asset_tasks([task]);mesh=load(D+'/Meshes/'+task.destination_name);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            label=str(slot.material_slot_name)
            if label.startswith('Super90_Foregrip_Saddle'):mat=saddle
            else:
                if key=='angled':
                    polymer='Polymer' in label
                    src=next(s.material_interface for s in original_slots if ('Polymer' in str(s.material_slot_name))==polymer)
                elif key=='prism':src=original_slots[0 if 'Polymer' in label else 1].material_interface
                else:src=original_slots[0].material_interface
                mat=finish(src)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(mesh,0)
        settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
        editor.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'Super90ForegripSource',sources[key]+'; existing body/UVs plus fitted underside saddle')
        save(mesh);receipt['meshes'][key]=mesh.get_path_name();record()
    for family in ('vertical','canted','prism','angled'):
        name='DA_Super90_'+family;path=D+'/Profiles/'+name
        if E.does_asset_exist(path):asset=load(path)
        else:
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
            asset=A.create_asset(name,D+'/Profiles',u.WeaponGripProfile,factory)
        payload=json.loads((O/'Profiles'/(family+'.json')).read_text(encoding='utf-8'))
        loader=O.parent/'Super90Speedloader20261007'/(family+'_profiles.json')
        if loader.exists():
            payload['clips'].extend(c for c in json.loads(loader.read_text(encoding='utf-8'))['clips'] if E.does_asset_exist(c['base']))
        sprint=O.parent/'Super90TacticalSprint20261007'/(family+'_profiles.json')
        if sprint.exists():
            payload['clips'].extend(c for c in json.loads(sprint.read_text(encoding='utf-8'))['clips'] if E.does_asset_exist(c['base']))
        if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Pose layer import failed '+family)
        E.set_metadata_tag(asset,'Super90ForegripSource','Accepted common grasp; native left-arm-only layer, right-hand feed and all native mechanical clocks retained')
        save(asset);receipt['profiles'][family]=asset.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['completed']=True;record();print('SUPER90_FOREGRIP_ASSETS_SAVED',len(receipt['saved']),flush=True)
