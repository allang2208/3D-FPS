"""Import the approved-reference model candidates, without changing live catalogs."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent
D='/Game/Weapons/AzureRunesword20260913/Pommels20260920'
L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary;S=u.ModelingService
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing pommels; keep the editor open.')
rows=json.loads((P/'model_exports.json').read_text(encoding='utf-8'))
receipt=[]
def done(r):
    if not r.success:raise RuntimeError(r.message)
    return r
def save(asset):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
def make_material(name,category,textures):
    path=D+'/Materials/'+name
    mat=u.load_asset(path) if L.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    if not mat:raise RuntimeError('Material creation failed: '+name)
    M.delete_all_material_expressions(mat)
    def scalar(value,prop):
        node=M.create_material_expression(mat,u.MaterialExpressionConstant);node.set_editor_property('r',value)
        if not M.connect_material_property(node,'',prop):raise RuntimeError('Scalar connection failed: '+name)
    samples={}
    for channel,texture in textures.items():
        node=M.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',texture)
        sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel in ['BaseColor','Emissive'] else (u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        node.set_editor_property('sampler_type',sampler);samples[channel]=node
    for channel,output,prop in [('BaseColor','RGB',u.MaterialProperty.MP_BASE_COLOR),('Metallic','R',u.MaterialProperty.MP_METALLIC),('Roughness','R',u.MaterialProperty.MP_ROUGHNESS),('Normal','RGB',u.MaterialProperty.MP_NORMAL)]:
        if not M.connect_material_property(samples[channel],output,prop):raise RuntimeError('PBR connection failed: '+channel)
    strength=M.create_material_expression(mat,u.MaterialExpressionMultiply);strength.set_editor_property('const_b',3.)
    if not M.connect_material_expressions(samples['Emissive'],'RGB',strength,'A'):raise RuntimeError('Emissive connection failed')
    if not M.connect_material_property(strength,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emission output failed')
    if category=='Crystal':
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        scalar(.68,u.MaterialProperty.MP_OPACITY)
        scalar(.5,u.MaterialProperty.MP_SPECULAR)
    else:mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    M.layout_material_expressions(mat);M.recompile_material(mat);save(mat)
    return mat

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
    key=row['id'];textures={}
    for channel,file in row['textures'].items():
        asset_path=D+'/Textures/T_Pommel_'+key+'_'+channel
        mode='Normalmap' if channel=='Normal' else ('Default' if channel in ['BaseColor','Emissive'] else 'Masks')
        done(S.import_texture(file,asset_path,channel in ['BaseColor','Emissive'],mode,True))
        tex=u.load_asset(asset_path)
        if not tex:raise RuntimeError('Texture import failed: '+file)
        # Blender tangent maps use OpenGL +Y, UE uses DirectX -Y.
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[channel]=tex
    materials={name:make_material(name,'Crystal' if name.endswith('_Crystal') else 'Opaque',textures) for name in row['materials']}
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=D+'/Models';task.destination_name=row['mesh']
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(D+'/Models/'+row['mesh'])
    if not asset or not task.imported_object_paths:raise RuntimeError('Mesh import failed: '+row['mesh'])
    for i,slot in enumerate(asset.static_materials):
        slotname=str(slot.material_slot_name)
        match=next((mat for name,mat in materials.items() if name==slotname or slotname.startswith(name)),None)
        if not match:raise RuntimeError('No model material for imported slot: '+slotname)
        asset.set_material(i,match)
    save(asset)
    done(S.set_lods(asset.get_path_name(),[1.0,.55,.25]))
    save(asset)
    receipt.append({'id':key,'source':row['fbx'],'asset':asset.get_path_name(),
        'materials':{name:mat.get_path_name() for name,mat in materials.items()},
        'textures':{name:tex.get_path_name() for name,tex in textures.items()},
        'lod_ratios':[1,.55,.25],'interface':'azure_hilt_v1','location_cm':[0,0,-19.5],
        'live_catalog_changed':False})
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('POMMEL_MODEL_IMPORTED',key,asset.get_path_name())
print('POMMEL_CANDIDATE_IMPORT_COMPLETE',len(receipt))
