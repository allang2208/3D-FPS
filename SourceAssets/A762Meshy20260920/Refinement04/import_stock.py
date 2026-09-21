"""Import the rebuilt A762 exterior at the existing runtime entry points.
Run only through the project batch mutex bridge. No PIE or acceptance calls.
"""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
R='/Game/Weapons/A762/Integrated20260920'; P='/Game/Weapons/A762/Refinement04'; PRE='/Game/Weapons/A762/Refinement01'
L=u.EditorAssetLibrary; T=u.AssetToolsHelpers.get_asset_tools(); M=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt=json.loads((O/'import.json').read_text(encoding='utf-8')) if (O/'import.json').exists() else {'backups':{},'textures':{},'materials':{},'meshes':{},'status':'in_progress','tested':False}
def record(): (O/'import.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
def save(asset):
    if not asset or not L.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+str(asset))
def connect(a,pin,b,target):
    if not M.connect_material_expressions(a,pin,b,target): raise RuntimeError('Material connection failed: '+target)
def output(a,pin,prop):
    if not M.connect_material_property(a,pin,prop): raise RuntimeError('Material output failed: '+str(prop))
def scalar(mat,name,value):
    n=M.create_material_expression(mat,u.MaterialExpressionScalarParameter); n.set_editor_property('parameter_name',name); n.set_editor_property('default_value',value); return n

old=u.load_asset(R+'/SK_A762_Manny')
if not old: raise RuntimeError('Existing A762 runtime mesh is unavailable')
skeleton=old.skeleton
bindings={str(slot.material_slot_name):slot.material_interface for slot in old.get_editor_property('materials')}
for name in ['SK_A762_Manny']:
    if name in receipt['backups']: continue
    dst=P+'/Before/'+name
    asset=u.load_asset(dst) if L.does_asset_exist(dst) else L.duplicate_asset(R+'/'+name,dst)
    if not asset: raise RuntimeError('Cannot preserve previous mesh: '+name)
    save(asset); receipt['backups'][name]=asset.get_path_name(); record()

texpath=P+'/Textures/T_A762_RebuiltFinish'
if not L.does_asset_exist(texpath):
    task=u.AssetImportTask(); task.filename=str(O/'Textures/T_A762_RebuiltFinish.png'); task.destination_path=P+'/Textures'
    task.destination_name='T_A762_RebuiltFinish'; task.automated=True; task.replace_existing=False; task.save=False
    T.import_asset_tasks([task])
tex=u.load_asset(texpath)
if not tex: raise RuntimeError('Finish texture import failed')
tex.set_editor_property('srgb',False); tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON); save(tex)
receipt['textures']['finish']=tex.get_path_name(); record()

materials={}
for name,info in auth['materials'].items():
    path=P+'/Materials/'+name
    if L.does_asset_exist(path):
        mat=u.load_asset(path); materials[name]=mat; receipt['materials'][name]=mat.get_path_name(); continue
    mat=T.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    base=M.create_material_expression(mat,u.MaterialExpressionVectorParameter)
    base.set_editor_property('parameter_name','FinishColor'); base.set_editor_property('default_value',u.LinearColor(*info['base_color_linear'],1))
    metal=scalar(mat,'Metallic',info['metallic']); rough=scalar(mat,'RoughnessCenter',info['roughness_center'])
    tx=M.create_material_expression(mat,u.MaterialExpressionTextureSample); tx.set_editor_property('texture',tex)
    tx.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    scale=M.create_material_expression(mat,u.MaterialExpressionMultiply); scale.set_editor_property('const_b',info['roughness_variation']); connect(tx,'R',scale,'A')
    offset=M.create_material_expression(mat,u.MaterialExpressionAdd); offset.set_editor_property('const_b',-info['roughness_variation']*.5); connect(scale,'',offset,'A')
    add=M.create_material_expression(mat,u.MaterialExpressionAdd); connect(rough,'',add,'A'); connect(offset,'',add,'B')
    output(base,'',u.MaterialProperty.MP_BASE_COLOR); output(metal,'',u.MaterialProperty.MP_METALLIC); output(add,'',u.MaterialProperty.MP_ROUGHNESS)
    M.recompile_material(mat); save(mat); materials[name]=mat; receipt['materials'][name]=mat.get_path_name(); record()

flag='Interchange.FeatureFlags.Import.FBX'; prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,skeletal in [('SK_A762_Manny',True)]:
        if name in receipt['meshes']: continue
        opt=u.FbxImportUI(); opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=skeletal; opt.import_mesh=True; opt.import_animations=False
        opt.import_materials=False; opt.import_textures=False; opt.create_physics_asset=False
        opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
        if skeletal:
            opt.skeleton=skeleton; data=opt.skeletal_mesh_import_data
            data.set_editor_property('update_skeleton_reference_pose',False); data.set_editor_property('use_t0_as_ref_pose',False)
            data.set_editor_property('preserve_smoothing_groups',True)
        else:
            data=opt.static_mesh_import_data; data.combine_meshes=True; data.auto_generate_collision=False; data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE; data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask(); task.filename=str(O/'Exports'/(name+'.fbx')); task.destination_path=R; task.destination_name=name
        task.options=opt; task.factory=u.FbxFactory(); task.automated=True; task.replace_existing=True; task.replace_existing_settings=True; task.save=False
        T.import_asset_tasks([task]); mesh=u.load_asset(R+'/'+name)
        if not mesh or not task.imported_object_paths: raise RuntimeError('Import failed: '+name)
        prop='materials' if skeletal else 'static_materials'; slots=mesh.get_editor_property(prop)
        for i,slot in enumerate(slots):
            slotname=str(slot.material_slot_name); binding=materials.get(slotname)
            if not binding and slotname in auth['inherited_material_paths']: binding=u.load_asset(auth['inherited_material_paths'][slotname])
            if not binding: binding=bindings.get(slotname)
            if not binding: binding=u.load_asset(PRE+'/Materials/'+slotname)
            if not binding: raise RuntimeError('Unresolved material slot: '+slotname)
            slot.material_interface=binding; slots[i]=slot
        mesh.set_editor_property(prop,slots); save(mesh)
        receipt['meshes'][name]={'asset':mesh.get_path_name(),'materials':{str(x.material_slot_name):x.material_interface.get_path_name() for x in mesh.get_editor_property(prop)}}
        record()
finally: u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['status']='imported_and_saved'; receipt['skeleton']=skeleton.get_path_name()
receipt['animations']='Existing 11 A762 clips unchanged'; receipt['audio']='Existing AKM sounds unchanged'
receipt['native_code_changed']=False; record()
u.log('A762_STOCKJOINT04_IMPORTED_AND_SAVED')
