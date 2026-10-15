"""Import three detailed freight tool models and PBR assets; no map, inventory or play changes."""
from pathlib import Path
import json
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
DEST='/Game/Items/PowerCollectibles20261014/V1'
OWNER='PowerCollectibles20261014'
SPEC=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
HOST=Path(u.Paths.project_dir()).resolve()
STAGED=HOST==(ROOT/'UEImportHost').resolve()
if HOST!=PROJECT.resolve() and not STAGED:raise RuntimeError('Wrong project')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world():raise RuntimeError('Preserve active gameplay')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST):raise RuntimeError('Preserve unsaved task asset '+package.get_name())

report=dict(stage='importing',host=str(HOST),staged=STAGED,meshes=[],materials=[],textures=[],material_compile_errors=[],runtime_tested=False,rendered=False)
def record():(ROOT/'Receipts/ue-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def owned(path):
    obj=u.load_asset(path) if E.does_asset_exist(path) else None
    if obj and E.get_metadata_tag(obj,'PowerCollectibles.Owner')!=OWNER:raise RuntimeError('Preserve unowned asset '+path)
    return obj
def save(obj):
    obj.modify();E.set_metadata_tag(obj,'PowerCollectibles.Owner',OWNER)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Failed to save '+obj.get_path_name())
def imp(source,name,folder,options=None):
    path=folder+'/'+name
    if E.does_asset_exist(path):raise RuntimeError('Preserve existing import; use an explicit new revision: '+path)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.replace_existing_settings=False;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    else:task.factory=u.TextureFactory()
    A.import_asset_tasks([task]);obj=u.load_asset(path)
    if not obj:raise RuntimeError('Import failed '+path)
    E.set_metadata_tag(obj,'PowerCollectibles.Owner',OWNER)
    return obj
def wire(node,output,target,pin):
    if not L.connect_material_expressions(node,output,target,pin):raise RuntimeError('Material connection failed: '+pin)
def output(node,socket,prop):
    if not L.connect_material_property(node,socket,prop):raise RuntimeError('Material output failed: '+str(prop))

u.load_module('StaticMeshEditor')
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if not SM:SM=u.new_object(u.StaticMeshEditorSubsystem)
record()
shared_materials={}
for key,spec in SPEC['assets'].items():
    if spec['material'] in shared_materials:
        mat=shared_materials[spec['material']]
    else:
        textures={}
        for kind,source in spec['textures'].items():
            tex=imp(source,'T_FT_'+key+'_'+kind,DEST+'/Textures')
            tex.set_editor_property('srgb',kind=='BaseColor')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_BC7)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WORLD)
            tex.set_editor_property('never_stream',False)
            tex.set_editor_property('max_texture_size',spec['size'])
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
            save(tex);textures[kind]=tex;report['textures'].append(tex.get_path_name());record()
        path=DEST+'/Materials/'+spec['material']
        mat=owned(path) or A.create_asset(spec['material'],DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.modify();E.set_metadata_tag(mat,'PowerCollectibles.Owner',OWNER)
        for node in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,node)
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
        mat.set_editor_property('two_sided',False)
        mat.set_editor_property('used_with_instanced_static_meshes',True)
        mat.set_editor_property('used_with_nanite',True)
        slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
        slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        nodes={}
        for kind in textures:
            sample=L.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.texture=textures[kind]
            sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            nodes[kind]=sample
        for node,socket,prop,pin in ((nodes['BaseColor'],'RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),
            (nodes['ORM'],'G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
            (nodes['ORM'],'B',u.MaterialProperty.MP_METALLIC,'Metallic')):
            wire(node,socket,slab,pin);output(node,socket,prop)
        flat=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);flat.constant=u.LinearColor(0,0,1,1)
        normal=L.create_material_expression(mat,u.MaterialExpressionLinearInterpolate);normal.set_editor_property('const_alpha',1.0)
        wire(flat,'',normal,'A');wire(nodes['Normal'],'RGB',normal,'B')
        wire(normal,'',slab,'Normal');output(normal,'',u.MaterialProperty.MP_NORMAL)
        output(nodes['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        output(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(mat)
        if errors:
            report['material_compile_errors'].append({'material':path,'errors':[str(e) for e in errors]});record()
            raise RuntimeError('Material compilation failed '+path+' '+str(errors))
        L.layout_material_expressions(mat);save(mat);report['materials'].append(mat.get_path_name());record()
        shared_materials[spec['material']]=mat
    options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
    options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
    data.generate_lightmap_u_vs=False;data.convert_scene=True;data.convert_scene_unit=True;data.force_front_x_axis=False
    data.import_uniform_scale=1;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    mesh=imp(spec['fbx'],spec['mesh'],DEST+'/Meshes',options)
    for index in range(len(mesh.static_materials)):mesh.set_material(index,mat)
    settings=SM.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_tangents=True;settings.recompute_normals=False;settings.use_mikk_t_space=True
    SM.set_lod_build_settings(mesh,0,settings)
    nanite=mesh.get_editor_property('nanite_settings')
    nanite.enabled=True;nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED
    nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    nanite.fallback_percent_triangles=1.0;nanite.fallback_relative_error=0.0
    SM.set_nanite_settings(mesh,nanite,True)
    save(mesh)
    bounds=mesh.get_bounds()
    report['meshes'].append(dict(item_id=spec['id'],path=mesh.get_path_name(),material=mat.get_path_name(),
        dimensions_cm=[bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2],
        authored_triangles=spec['triangles_lod0'],collision='Authored compound UCX hulls',collision_hulls=spec['collision_hulls'],nanite_enabled=True,source=spec['source']))
    record();u.log('POWER_TOOL_ASSET_SAVED '+mesh.get_path_name())
report['stage']='staged_assets_saved' if STAGED else 'assets_saved';record()
u.log('POWER_TOOLS_IMPORT_COMPLETE meshes='+str(len(report['meshes'])))
