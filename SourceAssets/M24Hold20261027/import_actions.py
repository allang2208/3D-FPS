"""Save corrected metric V9 hold family; reuse the repaired gun materials and parts."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;ROOT='/Game/Weapons/M24/Hold20261027'
src=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'saved':[],'complete':False,'clips':{}}
def save(ob):
    if not E.save_loaded_asset(ob,False):raise RuntimeError('Save failed '+ob.get_path_name())
    if ob.get_path_name() not in receipt['saved']:receipt['saved'].append(ob.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(file,folder,name,opt):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.options=opt
    A.import_asset_tasks([t]);ob=u.load_asset(folder+'/'+name)
    if not ob:raise RuntimeError('Import failed '+name)
    return ob
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
    opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=load(src['mesh'],ROOT,'SK_M24_HoldV9',opt)
    slots=list(mesh.materials)
    for i,slot in enumerate(slots):
        key=str(slot.material_slot_name)
        path='/Game/Characters/ModularOutfit20260924/BareSkinV9M4/MI_M4SkinV9' if key.startswith('MI_Manny') else '/Game/Weapons/M24/Repair20261027/Materials/M_'+key
        mat=u.load_asset(path)
        if not mat:raise RuntimeError('Missing retained material '+path)
        slot.material_interface=mat;slots[i]=slot
    mesh.set_editor_property('materials',slots)
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=sub.get_lod_build_settings(mesh,0)
    settings.recompute_normals=False;settings.recompute_tangents=False;settings.compute_weighted_normals=False
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    sub.set_lod_build_settings(mesh,0,settings);save(mesh);save(mesh.skeleton)
    receipt['mesh']=mesh.get_path_name();receipt['skeleton']=mesh.skeleton.get_path_name()
    receipt['arm_materials']=[i for i,v in enumerate(slots) if str(v.material_slot_name).startswith('MI_Manny')]
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    for role,row in src['clips'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        clip=load(row['file'],ROOT+'/Animations','A_M24_'+role,opt)
        clip.set_editor_property('bone_compression_settings',compression);save(clip)
        receipt['clips'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()}
    receipt['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_HOLD_ASSETS_SAVED',len(receipt['saved']),receipt['arm_materials'],flush=True)
