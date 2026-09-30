"""Import/save fitted 201 parts, independent finish pairs, and native FK clips."""
import unreal as u,json,hashlib,sys
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];D='/Game/Weapons/LMG201/Accessories22'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
G=json.loads((O/'geometry.json').read_text());S=json.loads((O/'sources.json').read_text());AN=json.loads((O/'animations.json').read_text())
receipt={'meshes':{},'animations':{},'materials':{},'runtime_tested':False,'rendered':False,'complete':False}
if (O/'install_receipt.json').exists():receipt=json.loads((O/'install_receipt.json').read_text())
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def clone(src,path):
    a=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(src.get_path_name(),path)
    if not a:raise RuntimeError('Cannot duplicate '+path)
    return a
sys.path.insert(0,str(O.parent/'Material21'));import finish_recipe as recipe
grain=u.load_asset(recipe.GRAIN_PATH)
wet_sources={}
for path in ['/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials','/Game/Weapons/PSO1Russian20260923/DA_PSO1_WetMaterials']:
    table=u.load_asset(path)
    if table:wet_sources.update({str(k):v for k,v in table.get_editor_property('wet_materials').items() if v})
wet_pairs={};cache={}
for path,info in receipt['materials'].items():cache[info['source']]=u.load_asset(path)
for path,material in cache.items():
    if path in wet_sources and wet_sources[path].get_path_name() in cache:
        wet_pairs[material.get_path_name()]=cache[wet_sources[path].get_path_name()]
def finish(original,key,wet=False):
    path=original.get_path_name()
    if path in cache:return cache[path]
    base=original.get_base_material()
    if base.blend_mode not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:return original
    label=('Wet' if wet else 'Dry')+'_'+key+'_'+hashlib.sha1(path.encode()).hexdigest()[:8]
    graph=clone(base,D+'/Materials/M_'+label)
    params={str(n) for n in M.get_scalar_parameter_names(graph)}
    vectors={str(n) for n in M.get_vector_parameter_names(graph)}
    settings={'scalar':{},'vector':{}}
    if 'PKM_SatinRoughness' in params:
        settings['scalar'].update(PKM_SatinRoughness=.35,PKM_MicroScratchStrength=.16,PKM_SatinColorWeight=.85)
        settings['vector']['PKM_SatinTint']=recipe.STEEL
    if 'A762CoatingRoughness' in params:
        settings['scalar'].update(A762CoatingRoughness=.35,A762CoatingMetallic=.78)
        settings['vector']['A762CoatingColor']=recipe.STEEL
    for k,v in settings['scalar'].items():recipe.parameter(graph,k,v)
    for k,v in settings['vector'].items():recipe.parameter(graph,k,v,True)
    # Swap only the fine surface grain. Original UV0 normal, AO and masks stay.
    for n in M.get_material_expressions(graph):
        if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='PKM_SatinFinishTexture':n.set_editor_property('texture',grain)
    if key.startswith('pso1'):
        for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS]:
            old=M.get_material_property_input_node(graph,prop);pin=M.get_material_property_input_node_output_name(graph,prop)
            if not old:continue
            metal=M.get_material_property_input_node(graph,u.MaterialProperty.MP_METALLIC);mp=M.get_material_property_input_node_output_name(graph,u.MaterialProperty.MP_METALLIC)
            if not metal:continue
            region=recipe.node(graph,u.MaterialExpressionSmoothStep,const_min=.25,const_max=.7);recipe.wire((metal,mp),region,'Value')
            tint=recipe.parameter(graph,'LMG20122Steel' if prop==u.MaterialProperty.MP_BASE_COLOR else 'LMG20122Roughness',recipe.STEEL if prop==u.MaterialProperty.MP_BASE_COLOR else .35,prop==u.MaterialProperty.MP_BASE_COLOR)
            blend=recipe.node(graph,u.MaterialExpressionLinearInterpolate);recipe.wire((old,pin),blend,'A');recipe.wire(tint,blend,'B');recipe.wire(region,blend,'Alpha');recipe.output(blend,prop)
    graph.set_editor_property('used_with_skeletal_mesh',False)
    E.set_metadata_tag(graph,'WeaponFinishReference','LMG201 Material21; private shared-attachment adaptation; original nonmetal/optical masks and UV0 structure')
    errors=M.recompile_material(graph)
    if errors:raise RuntimeError('Material compile '+graph.get_path_name()+' '+str(errors))
    save(graph)
    result=graph
    if isinstance(original,u.MaterialInstanceConstant):
        result=clone(original,D+'/Materials/MI_'+label);M.set_material_instance_parent(result,graph)
        for k,v in settings['scalar'].items():M.set_material_instance_scalar_parameter_value(result,k,v)
        for k,v in settings['vector'].items():M.set_material_instance_vector_parameter_value(result,k,u.LinearColor(*v,1))
        M.update_material_instance(result);save(result)
    cache[path]=result;receipt['materials'][result.get_path_name()]={'source':path,'saved':True,'wet':wet};record()
    if not wet and path in wet_sources:wet_pairs[result.get_path_name()]=finish(wet_sources[path],key,True)
    return result
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    interface_path=next(m['path'] for m in S['meshes']['vertical']['materials'] if m['slot']=='PKM14_Interface')
    for key,info in G['meshes'].items():
        if key=='pso1_4x':continue  # PSO-1 is limited to Russian weapons.
        if key in receipt['meshes']:continue
        materials={name:finish(u.load_asset(interface_path if v['path']=='201_INTERFACE' else v['path']),key+'_'+str(i)) for i,(name,v) in enumerate(info['materials'].items())}
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=info['file'];task.destination_path=D+'/Meshes';task.destination_name=info['name'];task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(task.destination_path+'/'+task.destination_name)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Import failed '+key)
        slots=mesh.static_materials
        for i,s in enumerate(slots):
            name=str(s.material_slot_name)
            if name not in materials:raise RuntimeError('Unmapped slot '+key+' '+name)
            s.material_interface=materials[name];slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        sockets=info['sockets']
        if key=='pso1_4x':
            donor=u.load_asset(info['source']);xf=info['transform_blender']
            for name in ['AimCenter','LensFront','LensRear','EyeRelief','Emitter','AimGuide']:
                s=donor.find_socket(name)
                if s:sockets[name]={'p':[s.relative_location.x+xf[0][3]*100,s.relative_location.y-xf[1][3]*100,s.relative_location.z+xf[2][3]*100],'r':list(s.relative_rotation.to_tuple()),'s':list(s.relative_scale.to_tuple())}
        for name,v in sockets.items():
            socket=mesh.find_socket(name)
            if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.relative_location=u.Vector(*v['p']);socket.relative_rotation=u.Rotator(*v['r']);socket.relative_scale=u.Vector(*v['s'])
        E.set_metadata_tag(mesh,'201AttachmentRevision','Accessories22: 201 fitted interface; donor geometry/UVs retained')
        E.set_metadata_tag(mesh,'SourceAsset',info['source']);save(mesh)
        receipt['meshes'][key]={'asset':mesh.get_path_name(),'saved':True,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'sockets':sockets};record();print('LMG20122_MESH_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
table=u.load_asset(D+'/DA_LMG201_AttachmentWetMaterials')
if not table:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    table=A.create_asset('DA_LMG201_AttachmentWetMaterials',D,u.WeatherPresentationAssets,factory)
table.set_editor_property('wet_materials',wet_pairs);save(table)
receipt['wet_pairs']=len(wet_pairs);record()
for key,info in AN['clips'].items():
    if key.split('/')[-1].startswith('reload'):continue  # Magazine24 owns current reload assets.
    if key in receipt['animations']:continue
    def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
    if sha(info['source'])!=info['source_sha256']:raise RuntimeError('Source changed during authoring '+key)
    base=u.load_asset(info['source']);clip=clone(base,info['destination']);tracks=json.loads(Path(info['keys']).read_text())
    model=clip.get_editor_property('data_model_interface');controller=clip.get_editor_property('controller')
    controller.open_bracket('201 accessory: complete native FK grip family',False)
    try:
        for n,keys in tracks.items():
            if not model.is_valid_bone_track_name(n):controller.add_bone_curve(n,False)
            if not controller.set_bone_track_keys(n,[u.Vector(*v['p']) for v in keys],[u.Quat(*v['q']) for v in keys],[u.Vector(*v['s']) for v in keys],False):raise RuntimeError('Track write failed '+n)
    finally:controller.close_bracket(False)
    E.set_metadata_tag(clip,'201GripRevision','Accessories22: PKM native complete FK grip; 201 mechanical action preserved; released sprint and timed regrip')
    E.set_metadata_tag(clip,'NativeGripDonor',info['donor']);E.set_metadata_tag(clip,'NativeGripDonorSHA256',info['donor_sha256'])
    E.set_metadata_tag(clip,'201ActionSourceSHA256',info['source_sha256'])
    u.AKMAnimationAuditLibrary.finish_animation_compression(clip);save(clip)
    receipt['animations'][key]={'asset':clip.get_path_name(),'saved':True,'seconds':clip.get_play_length(),'source':info['source']};record();print('LMG20122_ANIMATION_SAVED',key,flush=True)
receipt['complete']=True;record();print('LMG20122_INSTALL_COMPLETE',flush=True)
