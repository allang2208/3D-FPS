"""Import metric M24 and original glTF UV/normal corners into a fresh family."""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent
ROOT='/Game/Weapons/M24/Repair20261027';NATIVE='/Game/Weapons/M24/CustomScope20261026'
src=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'saved':[],'complete':False,'clips':{},'checks':{}}
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
def material(key,static=False):
    if key.startswith('MI_Manny'):return u.load_asset('/Game/Characters/ModularOutfit20260924/BareSkinV9M4/MI_M4SkinV9')
    target=ROOT+'/Materials/M_'+key+('_Static' if static else '')
    mat=u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(NATIVE+'/Materials/M_'+key,target)
    mat.set_editor_property('used_with_skeletal_mesh',not static)
    mat.set_editor_property('automatically_set_usage_in_editor',False)
    if key in ('M24_ScopeGlass','M24_TopGlass'):
        runpy.run_path(str(O/'repair_glass.py'))['rebuild'](mat,key)
    u.MaterialEditingLibrary.recompile_material(mat);save(mat);return mat
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
    opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=load(src['mesh'],ROOT,'SK_M24_RepairedV9',opt)
    slots=list(mesh.materials)
    for i,slot in enumerate(slots):slot.material_interface=material(str(slot.material_slot_name));slots[i]=slot
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
    stat=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for key,row in src['models'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True
        opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        part=load(row['file'],ROOT,'SM_M24_'+key,opt)
        for i,slot in enumerate(part.static_materials):part.set_material(i,material(str(slot.material_slot_name),True))
        settings=stat.get_lod_build_settings(part,0);settings.recompute_normals=False;settings.recompute_tangents=False
        settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
        stat.set_lod_build_settings(part,0,settings)
        for name,pos in row['sockets_ue_cm'].items():
            socket=part.find_socket(name)
            if not socket:socket=u.StaticMeshSocket(outer=part);socket.set_editor_property('socket_name',name);part.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        save(part)
    # Read actual saved reference poses without invoking the crashing mesh exporter.
    ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
    front=u.AnimPoseExtensions.get_bone_pose(ref,'WPN_FrontSight',u.AnimPoseSpaces.WORLD).translation
    rear=u.AnimPoseExtensions.get_bone_pose(ref,'WPN_RearSight',u.AnimPoseSpaces.WORLD).translation
    length=(front-rear).length();receipt['checks']['sight_span_cm']=length
    if not 40<length<42:raise RuntimeError('Unexpected reference unit scale '+str(length))
    opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
    for role,row in receipt['clips'].items():
        clip=u.load_asset(row['asset']);spans=[]
        for t in (0.,clip.get_play_length()*.5,clip.get_play_length()):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
            f=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_FrontSight',u.AnimPoseSpaces.WORLD).translation
            r=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_RearSight',u.AnimPoseSpaces.WORLD).translation
            spans.append((f-r).length())
        row['sight_span_cm']=spans
        if any(abs(n-length)>.02 for n in spans):raise RuntimeError('Animation scale mismatch '+role)
    receipt['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_REPAIRED_ASSETS_SAVED',len(receipt['saved']),receipt['checks'],flush=True)
