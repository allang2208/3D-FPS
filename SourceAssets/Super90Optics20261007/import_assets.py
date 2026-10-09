"""Save Super90 optic variants, fitted shoes and semantic factory sights."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/Super90/Optics20261007';R='/Game/Weapons/Super90/Cransh20261006'
M=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'saved':[],'meshes':{},'completed':False,'runtime_tested':False}
sources={k:'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/'+v for k,v in [('holographic','SM_M4_Holographic'),('panoramic_red_dot','SM_PanoramicRedDot'),('prism_scope_2x','SM_PrismScope2X'),('lpvo_1_6x','SM_LPVO1to6X'),('lpvo_ring','SM_LPVORing')]}
sources['eoth_holographic']='/Game/Weapons/CommonHK41620260930/Meshes/SM_Common_eoth_holographic'
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:receipt['saved'].append(asset.get_path_name())
    record();return asset
def clone(source,path):return load(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
def socket(mesh,name,p):
    s=mesh.find_socket(name)
    if not s:s=u.new_object(u.StaticMeshSocket,outer=mesh);s.set_editor_property('socket_name',name);mesh.add_socket(s)
    s.set_editor_property('relative_location',u.Vector(*p))
def finish(source):
    label=hashlib.sha256(source.get_path_name().encode()).hexdigest()[:10]
    mat=clone(source.get_path_name(),D+'/Materials/M_Super90_Optic_'+label)
    if isinstance(mat,u.MaterialInstanceConstant):
        scalars={str(n) for n in L.get_scalar_parameter_names(mat.get_base_material())}
        if 'R01_Roughness' in scalars:
            L.set_material_instance_scalar_parameter_value(mat,'R01_Roughness',.43)
            L.set_material_instance_vector_parameter_value(mat,'R01_ToneScale',u.LinearColor(.59,.60,.60,1))
        L.update_material_instance(mat)
    else:
        for key in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):mat.set_editor_property(key,False)
        L.recompile_material(mat)
    E.set_metadata_tag(mat,'Super90OpticSourceMaterial',source.get_path_name());return save(mat)
centers={'holographic':[-.653782,0,5.175324],'panoramic_red_dot':[2.125,0,3.25],'prism_scope_2x':[-6.15,0,4.],'lpvo_1_6x':[-12.15,0,4.]}
for key,source in sources.items():
    mesh=clone(source,D+'/Meshes/SM_Super90_'+key);slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        if any(k in str(s.material_slot_name).lower() for k in ('glass','reticle','red_dot')):continue
        s.material_interface=finish(s.material_interface);slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    if key in centers:
        c=centers[key];socket(mesh,'AimCenter',c);socket(mesh,'SightRear',c);socket(mesh,'SightFront',[c[0]+10,c[1],c[2]]);socket(mesh,'SightUp',[c[0],c[1],c[2]+1])
    if key=='lpvo_1_6x':socket(mesh,'ZoomRing',[-7.1,0,4.])
    E.set_metadata_tag(mesh,'Super90OpticSource',source);save(mesh);receipt['meshes'][key]=mesh.get_path_name()
railpath=D+'/Materials/M_Super90_RailSteel'
rail=load(railpath) if E.does_asset_exist(railpath) else A.create_asset('M_Super90_RailSteel',D+'/Materials',u.Material,u.MaterialFactoryNew())
for n in list(L.get_material_expressions(rail)):L.delete_material_expression(rail,n)
for prop,value in [('BASE_COLOR',(.036,.037,.037)),('ROUGHNESS',.43),('METALLIC',.65)]:
    n=L.create_material_expression(rail,u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
    n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value)
    if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Rail material pin '+prop)
L.recompile_material(rail);save(rail)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,entry in M['parts'].items():
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_mesh=True;opts.import_as_skeletal=False;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
        opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False;opts.static_mesh_import_data.generate_lightmap_u_vs=False
        opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=D+'/Meshes';task.destination_name='SM_Super90_Rail_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opts
        A.import_asset_tasks([task]);mesh=load(D+'/Meshes/'+task.destination_name);slots=list(mesh.static_materials)
        for s in slots:s.material_interface=rail
        mesh.set_editor_property('static_materials',slots);save(mesh);receipt['meshes']['Rail_'+key]=mesh.get_path_name()
    path=R+'/SK_Super90_V7';mesh=load(path);before=O/'Before/SK_Super90_V7.uasset'
    if not before.exists():shutil.copy2(P/'Content/Weapons/Super90/Cransh20261006/SK_Super90_V7.uasset',before)
    old={str(s.material_slot_name).removeprefix('Manny_S90_'):s for s in mesh.materials}
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=mesh.skeleton
    opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False);opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=M['mesh_fbx'];task.destination_path=R;task.destination_name='SK_Super90_V7';task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opts
    A.import_asset_tasks([task]);mesh=load(path);slots=list(mesh.materials)
    for i,s in enumerate(slots):
        key=str(s.material_slot_name).removeprefix('Manny_S90_')
        if key=='FactorySights':s.material_interface=old[key].material_interface if key in old else load(R+'/Materials/M_S90_TTI_Benelli_M4')
        else:s.material_interface=old[key].material_interface;s.material_slot_name=old[key].material_slot_name
        slots[i]=s
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(Path(M['mesh_fbx']).read_bytes()).hexdigest())
    E.set_metadata_tag(mesh,'Super90FactorySights','Separate material section for fitted optic visibility; original geometry and rig retained')
    save(mesh);receipt['material_slots']=[str(s.material_slot_name) for s in mesh.materials]
    data=P/'Content/ColdSteelData/modular_outfits.json';config=json.loads(data.read_text(encoding='utf-8-sig'))
    config['profiles'][mesh.get_path_name()]['hide_source_materials']=[i for i,s in enumerate(mesh.materials) if str(s.material_slot_name).startswith('Manny_S90_')]
    data.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['completed']=True;record();print('SUPER90_OPTICS_SAVED',len(receipt['saved']),flush=True)
