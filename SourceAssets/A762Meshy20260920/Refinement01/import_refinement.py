"""Save revised A762 geometry/materials into its existing game entry points."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R='/Game/Weapons/A762/Integrated20260920';P='/Game/Weapons/A762/Refinement01';B=P+'/Before'
T=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt=json.loads((O/'import.json').read_text(encoding='utf-8')) if (O/'import.json').exists() else {'backups':{},'textures':{},'materials':{},'meshes':{},'status':'in_progress','tested':False}

def record():
    (O/'import.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
def save(asset):
    if not asset or not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+str(asset))
def clone(src,dst):
    asset=u.load_asset(dst) if L.does_asset_exist(dst) else L.duplicate_asset(src,dst)
    if not asset:raise RuntimeError('Copy failed: '+src)
    save(asset);return asset
def connect(a,pin,b,target):
    if not M.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material connection failed: '+target)
def output(a,pin,prop):
    if not M.connect_material_property(a,pin,prop):raise RuntimeError('Material output failed: '+str(prop))
def scalar(mat,name,value):
    n=M.create_material_expression(mat,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def color(mat,name,value):
    n=M.create_material_expression(mat,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1));return n

old=u.load_asset(R+'/SK_A762_Manny')
if not old:raise RuntimeError('Current A762 runtime mesh unavailable')
bindings={str(slot.material_slot_name):slot.material_interface for slot in old.get_editor_property('materials')};skeleton=old.skeleton
for name in ['SK_A762_Manny','SM_A762_RearSight','SM_A762_FrontSight']:
    if name in receipt['backups']:continue
    copy=clone(R+'/'+name,B+'/'+name);receipt['backups'][name]=copy.get_path_name();record()

textures={}
for channel in ['base_color','roughness','normal']:
    if channel in receipt['textures']:
        textures[channel]=u.load_asset(receipt['textures'][channel]['asset']);continue
    tex=clone(R+'/Textures/T_A762_'+channel,P+'/Textures/T_A762_'+channel)
    tex.set_editor_property('srgb',channel=='base_color');tex.set_editor_property('lod_bias',0)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if channel=='normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='normal' else u.TextureCompressionSettings.TC_BC7 if channel=='base_color' else u.TextureCompressionSettings.TC_GRAYSCALE)
    if channel=='normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);textures[channel]=tex;receipt['textures'][channel]={'asset':tex.get_path_name(),'srgb':tex.get_editor_property('srgb'),'compression':str(tex.get_editor_property('compression_settings'))};record()

materials={}
for name,info in auth['materials'].items():
    path=P+'/Materials/'+name
    # Material graphs are built once under new names; never delete expressions
    # from a live referenced material (UE5.8 can assert on rooted expressions).
    if L.does_asset_exist(path):
        mat=u.load_asset(path);materials[name]=mat;receipt['materials'][name]=mat.get_path_name();continue
    mat=T.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    base=color(mat,'FinishColor',info['base_color_linear']);metal=scalar(mat,'Metallic',info['metallic']);rough=scalar(mat,'RoughnessCenter',info['roughness_center'])
    base_out=base;rough_out=rough
    uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',0)
    if info['source_uv0_normal']:
        tx={}
        for channel in ['base_color','roughness','normal']:
            n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[channel]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            connect(uv,'',n,'UVs');tx[channel]=n
        weight=scalar(mat,'SourceColorWeight',info['source_color_mix']);blend=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        connect(base,'',blend,'A');connect(tx['base_color'],'RGB',blend,'B');connect(weight,'',blend,'Alpha');base_out=blend
        scale=M.create_material_expression(mat,u.MaterialExpressionMultiply);scale.set_editor_property('const_b',.12);connect(tx['roughness'],'R',scale,'A')
        shift=M.create_material_expression(mat,u.MaterialExpressionAdd);shift.set_editor_property('const_b',-.06);connect(scale,'',shift,'A')
        add=M.create_material_expression(mat,u.MaterialExpressionAdd);connect(rough,'',add,'A');connect(shift,'',add,'B');rough_out=add
        output(tx['normal'],'RGB',u.MaterialProperty.MP_NORMAL)
    if name=='M_A762_Flash_Hider':
        regions=M.create_material_expression(mat,u.MaterialExpressionVertexColor)
        inside=color(mat,'BoreInnerColor',(.004,.006,.009));blend=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        connect(base_out,'',blend,'A');connect(inside,'',blend,'B');connect(regions,'R',blend,'Alpha');base_out=blend
        dry=scalar(mat,'BoreInnerRoughness',.79);blend=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        connect(rough_out,'',blend,'A');connect(dry,'',blend,'B');connect(regions,'R',blend,'Alpha');rough_out=blend
    output(base_out,'',u.MaterialProperty.MP_BASE_COLOR);output(metal,'',u.MaterialProperty.MP_METALLIC);output(rough_out,'',u.MaterialProperty.MP_ROUGHNESS)
    M.recompile_material(mat);save(mat);materials[name]=mat;receipt['materials'][name]=mat.get_path_name();record()

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,skeletal in [('SK_A762_Manny',True),('SM_A762_RearSight',False),('SM_A762_FrontSight',False)]:
        if name in receipt['meshes']:continue
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        if skeletal:
            opt.skeleton=skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
        else:
            data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=R;task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        T.import_asset_tasks([task]);mesh=u.load_asset(R+'/'+name)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Import failed: '+name)
        prop='materials' if skeletal else 'static_materials';slots=mesh.get_editor_property(prop)
        for i,slot in enumerate(slots):
            slotname=str(slot.material_slot_name);binding=materials.get(slotname) or bindings.get(slotname)
            if not binding:raise RuntimeError('Unresolved material slot '+slotname)
            slot.material_interface=binding;slots[i]=slot
        mesh.set_editor_property(prop,slots);save(mesh)
        receipt['meshes'][name]={'asset':mesh.get_path_name(),'materials':{str(x.material_slot_name):x.material_interface.get_path_name() for x in mesh.get_editor_property(prop)}};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['skeleton']=skeleton.get_path_name();receipt['status']='imported_and_saved';receipt['animations']='Existing 11 A762 clips unchanged';receipt['native_code_changed']=False;record()
u.log('A762_REFINEMENT_IMPORTED_AND_SAVED')
