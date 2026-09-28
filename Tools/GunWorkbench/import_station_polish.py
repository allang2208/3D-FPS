"""Import the desktop refinement and save its existing build-palette reference."""
import json
import re
import shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/GunWorkbenchPolish20260928'
RECEIPTS=ROOT/'Receipts'
RECEIPTS.mkdir(parents=True,exist_ok=True)
DEST='/Game/Building/GunWorkbenchPolish20260928'
PALETTE='/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
RECIPES=json.loads((ROOT/'Authored/surface-materials.json').read_text(encoding='utf-8'))['materials']
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong target project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Exit PIE before saving workbench assets')
receipt={'stage':'importing','materials':{},'textures':{},'tests_run':False,'renders_run':False}
def write():
    (RECEIPTS/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
def normalize(name):return re.sub(r'[^a-z0-9]','',re.sub(r'[._][0-9]{3}$','',str(name)).lower())
def node(mat,cls):return L.create_material_expression(mat,cls)
def scalar(mat,value):
    result=node(mat,u.MaterialExpressionConstant);result.r=value;return result
def color(mat,value):
    result=node(mat,u.MaterialExpressionConstant3Vector)
    result.set_editor_property('constant',u.LinearColor(*value,1));return result
def link(source,pin,target,input_name):
    inputs=list(L.get_material_expression_input_names(target))
    if input_name not in inputs and len(inputs)==1:input_name=inputs[0]
    if not L.connect_material_expressions(source,pin,target,input_name):raise RuntimeError('Material input connection failed: '+input_name)
def output(source,pin,property_name):
    if not L.connect_material_property(source,pin,getattr(u.MaterialProperty,'MP_'+property_name)):raise RuntimeError('Material property connection failed: '+property_name)

textures={}
def texture(filename,channel):
    key=str(Path(filename).resolve())
    if key in textures:return textures[key]
    asset_name='T_GW3_'+Path(filename).stem
    path=DEST+'/Textures/'+asset_name
    tex=u.load_asset(path)
    if not tex:
        task=u.AssetImportTask();task.filename=filename;task.destination_path=DEST+'/Textures'
        task.destination_name=asset_name;task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(path)
        if not tex:raise RuntimeError('Texture import failed: '+filename)
    tex.set_editor_property('srgb',channel=='BaseColor')
    tex.set_editor_property('virtual_texture_streaming',False)
    tex.set_editor_property('never_stream',False)
    tex.set_editor_property('max_texture_size',2048)
    if channel=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif channel=='BaseColor':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
    else:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[key]=tex;receipt['textures'][asset_name]=tex.get_path_name();return tex

# Original table/lamp material assets are reused without rewriting their graphs.
table=u.load_asset('/Game/Building/Workbench/Meshes/SM_WBStandalone_Workbench')
if not table:raise RuntimeError('Existing table source asset is missing')
source_materials={normalize(s.material_slot_name):s.material_interface for s in table.get_editor_property('static_materials')}
new_materials={}
for name,recipe in RECIPES.items():
    mat=u.load_asset(DEST+'/Materials/M_'+name)
    if not mat:mat=A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    output(scalar(mat,recipe['metallic']),'','METALLIC')
    if 'color' in recipe:
        output(color(mat,recipe['color']),'','BASE_COLOR')
        output(scalar(mat,recipe['roughness']),'','ROUGHNESS')
    for channel,filename in recipe.get('maps',{}).items():
        sample=node(mat,u.MaterialExpressionTextureSample);sample.texture=texture(filename,channel)
        sample.sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
            'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
            'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[channel]
        if channel=='BaseColor':
            tint=node(mat,u.MaterialExpressionMultiply);link(sample,'RGB',tint,'A');link(color(mat,recipe['color_tint']),'',tint,'B')
            output(tint,'','BASE_COLOR')
        elif channel in ('ORM','Roughness'):
            scale=node(mat,u.MaterialExpressionMultiply);link(sample,'G' if channel=='ORM' else 'R',scale,'A')
            link(scalar(mat,recipe['roughness_scale']),'',scale,'B')
            bias=node(mat,u.MaterialExpressionAdd);link(scale,'',bias,'A');link(scalar(mat,recipe['roughness_bias']),'',bias,'B')
            output(bias,'','ROUGHNESS')
            if channel=='ORM':output(sample,'B','METALLIC')
        elif channel=='Normal':
            scale=node(mat,u.MaterialExpressionMultiply);link(sample,'RGB',scale,'A');strength=recipe['normal_strength']
            link(color(mat,[strength,strength,1]),'',scale,'B')
            normalized=node(mat,u.MaterialExpressionNormalize);link(scale,'',normalized,'VectorInput')
            output(normalized,'','NORMAL')
    L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NANITE,True)
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat);new_materials[normalize(name)]=mat;receipt['materials'][name]=mat.get_path_name();write()

mesh=u.load_asset(DEST+'/SM_GunWorkbench')
if not mesh:
    # Fresh package avoids legacy static-mesh reimport retaining previous unit conversion.
    task=u.AssetImportTask();task.filename=MAN['fbx'];task.destination_path=DEST;task.destination_name='SM_GunWorkbench'
    task.automated=True;task.replace_existing=False;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_GunWorkbench')
    if not mesh:raise RuntimeError('Refined workbench mesh import failed')
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=normalize(slot.material_slot_name)
    material=new_materials.get(key) or source_materials.get(key)
    if not material:raise RuntimeError('Missing retained material: '+str(slot.material_slot_name))
    mesh.set_material(index,material)
mesh.set_editor_property('nanite_settings',table.get_editor_property('nanite_settings'))
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
save(mesh)
receipt['mesh']=mesh.get_path_name();receipt['stage']='mesh_saved';write()

# Preserve the existing prefab ID, footprint, pivot, placement and interaction fields.
palette=u.load_asset(PALETTE)
if not palette:raise RuntimeError('Build palette is missing')
components=list(palette.get_editor_property('components'))
for index,entry in enumerate(components):
    if str(entry.get_editor_property('id'))=='gun_workbench_table':
        prior=entry.get_editor_property('mesh')
        receipt['previous_mesh']=prior.get_path_name() if prior else None
        entry.set_editor_property('mesh',mesh)
        entry.set_editor_property('surface',mesh.get_material(0))
        components[index]=entry
        break
else:raise RuntimeError('Existing gun workbench prefab is missing')
before=RECEIPTS/'Before';before.mkdir(exist_ok=True)
source=PROJECT/'Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset'
if source.exists() and not (before/source.name).exists():shutil.copy2(source,before/source.name)
palette.modify();palette.set_editor_property('components',components);save(palette)
receipt.update({'stage':'assets_saved','saved':True,'palette':PALETTE,'entry':'gun_workbench_table',
    'source_materials_modified':False,'source_table_modified':False,'placement_fields_preserved':True})
write()
print('GUN_WORKBENCH_POLISH_SAVED '+json.dumps({'mesh':receipt['mesh'],'materials':len(new_materials),
    'textures':len(textures),'palette':PALETTE,'saved':True},ensure_ascii=False))
