"""Import/save RealisticV2 ice surfaces and modules with Unreal Python commandlet."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()); SRC=ROOT/'SourceAssets/IceWall20260930/RealisticV2'
DEST='/Game/Skills/IceWall/RealisticV2'
TOOLS=u.AssetToolsHelpers.get_asset_tools(); EAL=u.EditorAssetLibrary; LIB=u.MaterialEditingLibrary
EAL.make_directory(DEST); saved=[]

def save(asset):
    if not asset or not EAL.save_loaded_asset(asset,False): raise RuntimeError('Ice V2 save failed: '+str(asset))
    saved.append(asset.get_path_name())

def import_task(name, extension, options=None):
    task=u.AssetImportTask(); task.filename=str(SRC/(name+extension)); task.destination_path=DEST
    task.destination_name=name; task.automated=True; task.replace_existing=True; task.save=True
    if options: task.options=options
    TOOLS.import_asset_tasks([task]); asset=u.load_asset(DEST+'/'+name)
    if not asset: raise RuntimeError('Ice V2 import failed: '+name)
    return asset

masks=import_task('T_IceSurfaceMasks','.png')
masks.set_editor_property('srgb',False); masks.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS); save(masks)
normal=import_task('T_IceSurfaceNormal','.png')
normal.set_editor_property('srgb',False); normal.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP); save(normal)
path=DEST+'/M_IceWall'
mat=u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset('M_IceWall',DEST,u.Material,u.MaterialFactoryNew())
LIB.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
LIB.set_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)

def node(cls): return LIB.create_material_expression(mat,cls)
def wire(source,channel,target,pin):
    if not LIB.connect_material_expressions(source,channel,target,pin): raise RuntimeError('Ice V2 pin failed: '+pin)
def output(source,channel,prop):
    if not LIB.connect_material_property(source,channel,prop): raise RuntimeError('Ice V2 output failed: '+str(prop))
def custom(code,inputs,vector=False):
    n=node(u.MaterialExpressionCustom); n.set_editor_property('code',code)
    n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins=[]
    for key in inputs:
        p=u.CustomInput(); p.set_editor_property('input_name',key); pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,(source,channel) in inputs.items(): wire(source,channel,n,key)
    return n

uv=node(u.MaterialExpressionTextureCoordinate)
uv.set_editor_property('u_tiling',3.2); uv.set_editor_property('v_tiling',3.2)
sample=node(u.MaterialExpressionTextureSample); sample.set_editor_property('texture',masks)
sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS); wire(uv,'',sample,'UVs')
norm=node(u.MaterialExpressionTextureSample); norm.set_editor_property('texture',normal)
norm.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL); wire(uv,'',norm,'UVs')
vertex=node(u.MaterialExpressionVertexColor); random=node(u.MaterialExpressionPerInstanceRandom)
frost=custom('return saturate(M.r*.8+M.g*.14+M.b*.18+V*.14);',{'M':(sample,'RGB'),'V':(vertex,'R')})
base=custom('return lerp(float3(.19,.265,.285),float3(.43,.495,.505),F)*lerp(.94,1.035,R);',{'F':(frost,''),'R':(random,'')},True)
rough=custom('return clamp(.17+F*.46+M.b*.12,.17,.53);',{'F':(frost,''),'M':(sample,'RGB')})
output(base,'',u.MaterialProperty.MP_BASE_COLOR); output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
output(norm,'RGB',u.MaterialProperty.MP_NORMAL)
for prop,value in [(u.MaterialProperty.MP_METALLIC,0),(u.MaterialProperty.MP_SPECULAR,.23),(u.MaterialProperty.MP_OPACITY,.42)]:
    constant=node(u.MaterialExpressionConstant); constant.set_editor_property('r',value); output(constant,'',prop)
sub=node(u.MaterialExpressionConstant3Vector); sub.set_editor_property('constant',u.LinearColor(.31,.43,.46,1))
output(sub,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
LIB.recompile_material(mat); save(mat)
for index in range(1,5):
    name=f'SM_IceBlock_{index:02d}'; options=u.FbxImportUI()
    options.import_mesh=True; options.import_materials=False; options.import_textures=False
    options.automated_import_should_detect_type=False; options.import_as_skeletal=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data; data.combine_meshes=True; data.auto_generate_collision=False
    data.convert_scene_unit=True; data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_task(name,'.fbx',options); mesh.set_material(0,mat); save(mesh)
receipt=ROOT/'Saved/IceWallRealisticV2/assets-saved.json'; receipt.parent.mkdir(parents=True,exist_ok=True)
receipt.write_text(json.dumps({'saved_assets':saved,'runtime_tested':False,'style':'desaturated lit thick ice; shallow melt, sparse fractures, frost'},indent=2),encoding='utf-8')
u.log('ICE_WALL_REALISTIC_V2_SAVED '+str(receipt))
