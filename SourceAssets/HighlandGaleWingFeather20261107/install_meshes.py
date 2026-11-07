"""Install only this revision; do not touch an active play world or unsaved packages."""
import json, ast
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME/SourceAssets/HighlandGaleWingFeather20261107')
ROOT=P.parents[1];spec=json.loads((P/'model.json').read_text());D=spec['ue_folder']
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world() is not None:raise RuntimeError('Preserving active PIE')
if any(p.get_path_name().startswith(D+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved target package in '+D)
REV='GaleFeatherSolid20261107R2';SHARED='SharedTwoHandFinish20261101V1 '
receipt={'revision':REV,'saved':[],'meshes':{},'runtime_tested':False,'complete':False}
def owned(package):
    if not E.does_asset_exist(package):return None
    obj=u.load_asset(package)
    if E.get_metadata_tag(obj,'GaleFeatherRevision')!=REV:raise RuntimeError('Unexpected existing package '+package)
    return obj
def save(obj):
    E.set_metadata_tag(obj,'GaleFeatherRevision',REV)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('UE package save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());return obj
def imported(name,file,group,factory,options=None):
    dest=D+'/'+group;package=dest+'/'+name
    prev=owned(package)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=prev is not None;t.replace_existing_settings=True;t.save=False;t.factory=factory
    if options:t.options=options
    A.import_asset_tasks([t])
    if not t.imported_object_paths:raise RuntimeError('UE import failed '+name)
    return u.load_asset(package)
textures={}
for ch in ('BaseColor','ORM','NormalGL'):
    name='T_GaleFeather_'+ch;tex=imported(name,P/'Textures'/(name+'.png'),'Textures',u.TextureFactory())
    tex.set_editor_properties(dict(srgb=ch=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if ch=='NormalGL' else u.TextureCompressionSettings.TC_MASKS if ch=='ORM' else u.TextureCompressionSettings.TC_DEFAULT))
    if ch=='NormalGL':tex.set_editor_property('flip_green_channel',True)
    textures[ch]=save(tex)
source=ROOT/'SourceAssets/HighlandBroadbladeGuardFinish20261106/install.py'
helpers={'node','wire','custom','root','input_of','output','add_finishes'}
tree=ast.parse(source.read_text(encoding='utf-8'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),str(source),'exec'))
donor=u.load_asset('/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface')
recipes={str(n.get_editor_property('desc'))[len(SHARED):]:str(n.get_editor_property('code')) for n in L.get_material_expressions(donor) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc')).startswith(SHARED)}
mats={}
for name in ('M_GaleFeather_Atelier','M_GaleFeather_BladeSeat'):
    m=owned(D+'/Materials/'+name)
    if m:L.delete_all_material_expressions(m)
    else:m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    for ch in textures:
        smp=node(m,u.MaterialExpressionTextureSample,texture=textures[ch],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        links=[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')] if ch=='ORM' else [('RGB','BASE_COLOR' if ch=='BaseColor' else 'NORMAL')]
        for chan,key in links:
            if not L.connect_material_property(smp,chan,getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Missing surface pin '+key)
    if name.endswith('BladeSeat'):add_finishes(m)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for key,pin in [('BASE_COLOR','BaseColor'),('ROUGHNESS','Roughness'),('METALLIC','Metallic'),('NORMAL','Normal'),('ANISOTROPY','Anisotropy'),('TANGENT','Tangent')]:
        e,chan=root(m,key)
        if e:wire(e,slab,pin,chan)
    output(slab,'FRONT_MATERIAL');L.layout_material_expressions(m);L.recompile_material(m);mats[name]=save(m)
cat=json.loads((ROOT/'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
factory=u.load_asset(cat['slots']['guard']['factory']['mesh'])
for row in spec['variants']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    cfg=opt.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.import_uniform_scale=1.;cfg.convert_scene=True;cfg.convert_scene_unit=True;cfg.force_front_x_axis=False
    obj=imported(row['mesh'],P/row['fbx'],'Meshes',u.FbxFactory(),opt)
    slots=set()
    for i,slot in enumerate(obj.static_materials):
        name=str(slot.material_slot_name);obj.set_material(i,mats[name]);slots.add(name)
    expected={'M_GaleFeather_Atelier'}|({'M_GaleFeather_BladeSeat'} if row['key']=='Broadblade' else set())
    if slots!=expected:raise RuntimeError('Unassigned material for '+row['key'])
    cfg=S.get_lod_build_settings(factory,0);cfg.recompute_normals=False;cfg.recompute_tangents=True;cfg.use_mikk_t_space=True;cfg.use_full_precision_u_vs=True;cfg.use_high_precision_tangent_basis=True
    S.set_lod_build_settings(obj,0,cfg);obj.set_editor_property('nanite_settings',factory.get_editor_property('nanite_settings'));obj.set_editor_property('lod_group',factory.get_editor_property('lod_group'))
    n=S.get_lod_count(factory)
    if n>1:
        sizes=S.get_lod_screen_sizes(factory);reductions=[]
        for i in range(n):
            red=u.EditorScriptingMeshReductionSettings();red.percent_triangles=S.get_lod_reduction_settings(factory,i).percent_triangles;red.screen_size=sizes[i];reductions.append(red)
        red=u.EditorScriptingMeshReductionOptions();red.auto_compute_lod_screen_size=False;red.reduction_settings=reductions;S.set_lods(obj,red)
    E.set_metadata_tag(obj,'HighlandInterface','highland_hilt_v1 | '+row['key'])
    save(obj);receipt['meshes'][row['key']]=obj.get_path_name()
receipt['complete']=True
(P/'saved-assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FEATHER_MESHES_SAVED '+str(receipt['meshes']))
