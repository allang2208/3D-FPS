"""Save the modular M24 mesh and independently installable factory assemblies."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[1]
ROOT='/Game/Weapons/M24/Modular20261027';NATIVE='/Game/Weapons/M24/CustomScope20261026'
src=json.loads((O/'authoring.json').read_text());A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'complete':False,'saved':[],'tested':False}
def save(ob):
    if not E.save_loaded_asset(ob,False):raise RuntimeError('Save failed '+ob.get_path_name())
    if ob.get_path_name() not in receipt['saved']:receipt['saved'].append(ob.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(file,name,options):
    if ROOT+'/'+name+'.'+name in receipt['saved']:return u.load_asset(ROOT+'/'+name)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=ROOT;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;t.options=options
    A.import_asset_tasks([t]);ob=u.load_asset(ROOT+'/'+name)
    if not ob:raise RuntimeError('Import failed '+name)
    return ob
def material(key,static=False):
    key=src['section_material_source'].get(key,key)
    path='/Game/Characters/ModularOutfit20260924/BareSkinV9M4/MI_M4SkinV9' if key.startswith('MI_Manny') else NATIVE+'/Materials/M_'+key
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing material '+path)
    if static:
        target=ROOT+'/Materials/M_'+key+'_Static'
        copy=u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(path,target)
        copy.set_editor_property('used_with_skeletal_mesh',False)
        copy.set_editor_property('automatically_set_usage_in_editor',False)
        u.MaterialEditingLibrary.recompile_material(copy);save(copy)
        return copy
    return mat
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    skeleton=u.load_asset('/Game/Weapons/M24/Gameplay20261026/SK_M24_V9_Skeleton')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
    opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    opt.create_physics_asset=False;opt.skeleton=skeleton
    opt.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
    mesh=load(src['mesh'],'SK_M24_ModularV9',opt)
    slots=list(mesh.materials)
    for i,slot in enumerate(slots):slot.material_interface=material(str(slot.material_slot_name));slots[i]=slot
    mesh.set_editor_property('materials',slots)
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=sub.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;sub.set_lod_build_settings(mesh,0,settings)
    save(mesh)
    receipt['arm_materials']=[i for i,slot in enumerate(slots) if str(slot.material_slot_name).startswith('MI_Manny')]
    receipt['mesh']=mesh.get_path_name();receipt['skeleton']=mesh.skeleton.get_path_name()
    for key,row in src['models'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False
        opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False
        part=load(row['file'],'SM_M24_'+key,opt)
        for i,slot in enumerate(part.static_materials):part.set_material(i,material(str(slot.material_slot_name),True))
        for name,pos in row['sockets_ue_cm'].items():
            socket=part.find_socket(name)
            if not socket:socket=u.StaticMeshSocket(outer=part);socket.set_editor_property('socket_name',name);part.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        E.set_metadata_tag(part,'SourceAttribution','M37_R / DJMaesen / MaximDeduytsche CC BY 4.0; M24CustomScope20261026/ATTRIBUTION.md')
        save(part)
    receipt['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_MODULAR_ASSETS_SAVED',len(set(receipt['saved'])),flush=True)
