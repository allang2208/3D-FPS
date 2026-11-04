"""Import and save the hatchet's three factory modules and six common adapters."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
data=json.loads((P/'modules.json').read_text(encoding='utf-8'))
receipt={'complete':False,'assets':[],'parts':[],'runtime_tested':False}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Hatchet module assets have unsaved editor changes; preserved')

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def imported(file,name,dest,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import failed: '+name)
    return asset

def material(entry):
    if not entry['textures']:return u.load_asset('/Game/Weapons/TacticalHatchet20261101/Materials/M_TacticalHatchet')
    textures={}
    for role,path in entry['textures'].items():
        tex=imported(path,Path(path).stem,DEST+'/Textures')
        tex.set_editor_property('srgb',role=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if role=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if role=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('never_stream',False)
        if role=='Normal':tex.set_editor_property('flip_green_channel',True)
        textures[role]=tex;save(tex)
    name=entry['object'].replace('SM_','M_',1)
    mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    E.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',True);mat.set_editor_property('used_with_nanite',True)
    def node(cls,**properties):
        n=E.create_material_expression(mat,cls)
        for k,v in properties.items():n.set_editor_property(k,v)
        return n
    base=node(u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal=node(u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm=node(u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    slab=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for src,channel,pin,prop in [(base,'RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),(normal,'RGB','Normal',u.MaterialProperty.MP_NORMAL),
                               (orm,'G','Roughness',u.MaterialProperty.MP_ROUGHNESS),(orm,'B','Metallic',u.MaterialProperty.MP_METALLIC)]:
        if not E.connect_material_expressions(src,channel,slab,pin):raise RuntimeError('Material input: '+pin)
        E.connect_material_property(src,channel,prop)
    E.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if not E.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
    E.layout_material_expressions(mat);E.recompile_material(mat);save(mat);return mat

ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings=ui.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=True
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;settings.generate_lightmap_u_vs=False
for entry in list(data['factory'].values())+data['variants']:
    mat=material(entry)
    mesh=imported(entry['fbx'],entry['object'],DEST,ui)
    for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite)
    if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):raise RuntimeError('Hatchet tangent authoring failed: '+entry['object'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'HatchetInterface','factory cuts +11.5/-7.75cm; original grip frame; imported author normals')
    save(mesh)
    receipt['parts'].append({'slot':entry['slot'],'id':entry['id'],'mesh':mesh.get_path_name(),'material':mat.get_path_name(),
        'material_slot_names':[str(s.get_editor_property('material_slot_name')) for s in mesh.static_materials],'location_cm':entry['origin_cm']})
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('HATCHET_MODULES_SAVED parts='+str(len(receipt['parts'])))
