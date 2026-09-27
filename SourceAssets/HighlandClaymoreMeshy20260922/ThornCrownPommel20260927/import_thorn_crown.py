"""Save the finished Thorn Crown model as an independent UE asset.

No gameplay modifiers, catalog entries, existing pommel replacement or PIE.
Headless Python commandlet when closed; mutex bridge in an existing editor.
"""
from pathlib import Path
from datetime import datetime
import json
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
spec=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
D=spec['ue_folder']
A=u.AssetToolsHelpers.get_asset_tools()
L=u.EditorAssetLibrary
E=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End active PIE before creating the pommel assets.')
catalog=json.loads((ROOT/'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
donor=u.load_asset(catalog['slots']['pommel']['factory']['mesh'])
if donor is None:raise RuntimeError('The real Highland socket material source is missing.')
source_mat=donor.static_materials[0].material_interface
receipt_path=P/'import_receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {
    'time':datetime.now().isoformat(),'complete':False,'assets':[],
    'model_only':True,'catalogs_modified':False,'gameplay_stats_set':False,'tested':False}
done={a['asset'] for a in receipt['assets']}

def save(obj,source=''):
    if not L.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    path=obj.get_path_name()
    if path not in done:
        receipt['assets'].append({'asset':path,'source':str(source),'saved':True})
        done.add(path)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return obj

def imported(path,name,folder,options=None,factory=None):
    package=folder+'/'+name
    if L.does_asset_exist(package):
        obj=u.load_asset(package)
        if obj.get_path_name() in done:return obj
        raise RuntimeError('Independent target already exists outside this receipt: '+package)
    task=u.AssetImportTask()
    task.filename=str(path);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False
    if options:task.options=options
    if factory:task.factory=factory
    A.import_asset_tasks([task])
    obj=u.load_asset(package)
    if obj is None or not task.imported_object_paths:raise RuntimeError('Import failed: '+str(path))
    return obj

textures={}
for key in ['BaseColor','NormalGL','ORM']:
    path=P/'Textures'/('T_ThornCrown_'+key+'.png')
    tex=imported(path,'T_ThornCrown_'+key,D+'/Textures',factory=u.TextureFactory())
    tex.set_editor_property('srgb',key=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='NormalGL'
                            else u.TextureCompressionSettings.TC_MASKS if key=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    if key=='NormalGL':tex.set_editor_property('flip_green_channel',True)
    textures[key]=save(tex,path)

material_path=D+'/Materials/M_ThornCrown_PBR'
if L.does_asset_exist(material_path):
    material=u.load_asset(material_path)
    if material.get_path_name() not in done:raise RuntimeError('Existing material is not owned by this import.')
else:
    material=A.create_asset('M_ThornCrown_PBR',D+'/Materials',u.Material,u.MaterialFactoryNew())
    for key in ['BaseColor','NormalGL','ORM']:
        sample=E.create_material_expression(material,u.MaterialExpressionTextureSample)
        sample.set_editor_property('texture',textures[key])
        sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='NormalGL'
                                  else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        targets=[('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)] if key=='ORM' else [('RGB',u.MaterialProperty.MP_NORMAL if key=='NormalGL' else u.MaterialProperty.MP_BASE_COLOR)]
        for pin,target in targets:
            if not E.connect_material_property(sample,pin,target):raise RuntimeError('Material output failed: '+key)
    E.layout_material_expressions(material);E.recompile_material(material)
    save(material,'Baked PBR atlas; opaque nonmetal gemstones, satin silver steel')

options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal=False;options.import_mesh=True
options.import_materials=False;options.import_textures=False;options.import_animations=False
cfg=options.static_mesh_import_data
cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
cfg.import_uniform_scale=1.;cfg.convert_scene=True;cfg.convert_scene_unit=True;cfg.force_front_x_axis=False
mesh=imported(spec['fbx'],spec['mesh'],D+'/Meshes',options,u.FbxFactory())
for index,slot in enumerate(mesh.static_materials):
    name=str(slot.material_slot_name)
    if name.startswith('M_ThornCrown_PBR'):mesh.set_material(index,material)
    elif name.startswith('M_HighlandClaymoreSurface'):mesh.set_material(index,source_mat)
    else:raise RuntimeError('Unmapped material slot: '+name)
settings=S.get_lod_build_settings(donor,0)
settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
S.set_lod_build_settings(mesh,0,settings)
mesh.set_editor_property('nanite_settings',donor.get_editor_property('nanite_settings'))
mesh.set_editor_property('lod_group',donor.get_editor_property('lod_group'))
rows=[]
sizes=S.get_lod_screen_sizes(donor)
for index in range(S.get_lod_count(donor)):
    row=u.EditorScriptingMeshReductionSettings()
    row.percent_triangles=S.get_lod_reduction_settings(donor,index).percent_triangles
    row.screen_size=sizes[index];rows.append(row)
if len(rows)>1:
    reductions=u.EditorScriptingMeshReductionOptions()
    reductions.auto_compute_lod_screen_size=False;reductions.reduction_settings=rows
    S.set_lods(mesh,reductions)
L.set_metadata_tag(mesh,'HighlandPart','ThornCrownPommel_V1')
L.set_metadata_tag(mesh,'HighlandInterface','highland_hilt_v1; local socket Z=0; mount Z=-22.7cm')
L.set_metadata_tag(mesh,'AuthorSource',spec['fbx'])
save(mesh,spec['fbx'])
# Nanite may add material usage during mesh build; persist this task's material.
save(material)
icon_path=P/'Icons'/spec['icon']
icon=imported(icon_path,'T_ThornCrown_MenuIcon',D+'/Textures',factory=u.TextureFactory())
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('srgb',True)
save(icon,icon_path)
receipt['complete']=True
receipt['mesh']=mesh.get_path_name()
receipt['material']=material.get_path_name()
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('THORN_CROWN_MODEL_ASSETS_SAVED '+mesh.get_path_name())
