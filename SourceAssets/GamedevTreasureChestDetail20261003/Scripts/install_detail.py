"""Import + compile + save the detailed shared treasure. No tests or renders.

Fresh revision imports bypass stale FBX settings. GeometryScript then updates
the existing formal objects in place, keeping all saved map/Blueprint refs.
Neither the formal skeleton nor the animation packages are reimported.
"""
import json, re, shutil, traceback
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[1]
FORMAL='/Game/Props/GamedevTreasureChest20260922'
REVISION='/Game/Props/GamedevTreasureChestDetail20261003'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
G=u.GeometryScript_AssetUtils
saved=[];report=dict(stage='started',saved=saved,tested=False,rendered=False,
                    gui_editor_started=False,asset_paths_preserved=True)
receipt=HERE/'Receipts/install.json'
def record():receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(a):
    a.modify()
    if not E.save_loaded_asset(a,False):
        if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outer()],False):
            raise RuntimeError('Asset save failed: '+a.get_path_name())
    saved.append(a.get_path_name());record()
def asset(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required asset missing: '+path)
    return a
def link(a,out,b,port):
    if not L.connect_material_expressions(a,out,b,port):raise RuntimeError('Material connection: '+port)
def output(a,out,prop):
    if not L.connect_material_property(a,out,prop):raise RuntimeError('Material output: '+str(prop))
def texture(name,kind):
    path=REVISION+'/Textures/'+name
    t=u.load_asset(path)
    if not t:
        task=u.AssetImportTask();task.filename=str(HERE/'Textures'/(name+'.png'))
        task.destination_path=REVISION+'/Textures';task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=False
        task.set_editor_property('async_',False)
        AT.import_asset_tasks([task]);t=u.load_asset(path)
        if not t:raise RuntimeError('Texture import failed: '+name)
    t.modify();t.set_editor_property('srgb',kind=='BaseColor')
    t.set_editor_property('compression_settings',{'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,
        'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[kind])
    # Source normals are DirectX, keep the green channel as authored.
    if kind=='Normal':t.set_editor_property('flip_green_channel',False)
    save(t);return t
def sample(mat,t,x,y,uv):
    n=L.create_material_expression(mat,u.MaterialExpressionTextureSample,x,y)
    n.set_editor_property('texture',t)
    comp=t.get_editor_property('compression_settings')
    sampler=(u.MaterialSamplerType.SAMPLERTYPE_NORMAL if comp==u.TextureCompressionSettings.TC_NORMALMAP
             else u.MaterialSamplerType.SAMPLERTYPE_MASKS if comp==u.TextureCompressionSettings.TC_MASKS
             else u.MaterialSamplerType.SAMPLERTYPE_COLOR if t.get_editor_property('srgb')
             else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n.set_editor_property('sampler_type',sampler);link(uv,'',n,'UVs');return n
def newmaterial(name):
    m=u.load_asset(REVISION+'/Materials/'+name)
    if m and E.get_metadata_tag(m,'TreasureDetailRevision')=='Detailed20261003':return m,False
    # Own incomplete graph has no consumers yet; retain it and use a fresh name.
    suffix=2
    while m:
        candidate=name+'_R'+str(suffix)
        m=u.load_asset(REVISION+'/Materials/'+candidate)
        if m and E.get_metadata_tag(m,'TreasureDetailRevision')=='Detailed20261003':return m,False
        if not m:name=candidate;break
        suffix+=1
    m=AT.create_asset(name,REVISION+'/Materials',u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Material create failed '+name)
    return m,True
def finishmaterial(m):
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    result=L.recompile_material(m)
    if isinstance(result,(list,tuple)) and result:raise RuntimeError('Material compile failed '+str(result))
    E.set_metadata_tag(m,'TreasureDetailRevision','Detailed20261003')
    E.set_metadata_tag(m,'Source','Local treasure geometry/PBR; licensed Normandy wood interior')
    save(m)
def metalmaterial(family,textures):
    # The failed Iron base graph was archived; retain the adopted R2 identity
    # on rerun instead of recreating the retired graph path.
    m,create=newmaterial('M_TreasureDetail_'+family+('_R2' if family=='Iron' else ''))
    if not create:return m
    def node(cls,x,y):return L.create_material_expression(m,cls,x,y)
    uv=node(u.MaterialExpressionTextureCoordinate,-900,-150)
    uv.set_editor_property('coordinate_index',0)
    bc=sample(m,textures['BaseColor'],-680,-300,uv)
    orm=sample(m,textures['ORM'],-680,100,uv)
    norm=sample(m,textures['Normal'],-680,450,uv)
    wearuv=node(u.MaterialExpressionTextureCoordinate,-900,700)
    wearuv.set_editor_property('coordinate_index',1)
    vertex=node(u.MaterialExpressionVertexColor,-900,900)
    wear=node(u.MaterialExpressionCustom,-420,700)
    inputs=[]
    for name in ('WearUV','Vertex','Detail'):
        inp=u.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
    wear.set_editor_property('inputs',inputs)
    wear.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    wear.set_editor_property('code','float2 edge=min(WearUV,1-WearUV)*max(Vertex.gb*200,0.01); float seam=saturate(1-min(edge.x,edge.y)/0.34); return saturate(max(Vertex.r*0.8,seam*0.5)*(0.35+Detail*0.6));')
    link(wearuv,'',wear,'WearUV');link(vertex,'',wear,'Vertex');link(orm,'G',wear,'Detail')
    bright=node(u.MaterialExpressionConstant3Vector,-350,-420)
    bright.set_editor_property('constant',u.LinearColor(*((.36,.40,.43) if family=='Iron' else (.63,.42,.14)),1))
    blend=node(u.MaterialExpressionLinearInterpolate,-80,-230)
    link(bc,'RGB',blend,'A');link(bright,'',blend,'B');link(wear,'',blend,'Alpha')
    output(blend,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=node(u.MaterialExpressionLinearInterpolate,-80,100);rough.set_editor_property('const_b',.27 if family=='Iron' else .23)
    link(orm,'G',rough,'A');link(wear,'',rough,'Alpha');output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    metallic=node(u.MaterialExpressionLinearInterpolate,-80,240);metallic.set_editor_property('const_b',.95)
    link(orm,'B',metallic,'A');link(wear,'',metallic,'Alpha');output(metallic,'',u.MaterialProperty.MP_METALLIC)
    output(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(norm,'RGB',u.MaterialProperty.MP_NORMAL)
    finishmaterial(m);return m
def interior():
    m,create=newmaterial('M_TreasureDetail_Interior')
    if not create:return m
    uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate,-800,0)
    base=sample(m,asset('/Game/UnrealNormandy/Textures/T_WoodSurface_00A_BaseColor'),-600,-240,uv)
    packed=sample(m,asset('/Game/UnrealNormandy/Textures/T_WoodSurface_00A_RHAOM'),-600,100,uv)
    normal=sample(m,asset('/Game/UnrealNormandy/Textures/T_WoodSurface_00A_Normal'),-600,380,uv)
    tint=L.create_material_expression(m,u.MaterialExpressionConstant3Vector,-380,-400)
    tint.set_editor_property('constant',u.LinearColor(.40,.31,.24,1))
    mul=L.create_material_expression(m,u.MaterialExpressionMultiply,-100,-220)
    link(base,'RGB',mul,'A');link(tint,'',mul,'B');output(mul,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=L.create_material_expression(m,u.MaterialExpressionLinearInterpolate,-100,100)
    rough.set_editor_property('const_b',.82);rough.set_editor_property('const_alpha',.48)
    link(packed,'R',rough,'A');output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    output(packed,'B',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(normal,'RGB',u.MaterialProperty.MP_NORMAL)
    metallic=L.create_material_expression(m,u.MaterialExpressionConstant,-100,300)
    metallic.set_editor_property('r',0);output(metallic,'',u.MaterialProperty.MP_METALLIC)
    finishmaterial(m);return m
def importmesh(name,skeletal,skeleton,mats):
    path=REVISION+'/Meshes/'+name
    mesh=u.load_asset(path)
    if mesh:return mesh
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.import_mesh=True;opts.import_as_skeletal=skeletal;opts.import_animations=False
    opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    if skeletal:opts.skeleton=skeleton
    data=opts.skeletal_mesh_import_data if skeletal else opts.static_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    if skeletal:
        data.set_editor_property('update_skeleton_reference_pose',False)
        data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    else:
        data.combine_meshes=True;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=False
        data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task=u.AssetImportTask();task.filename=str(HERE/'Authored'/(name+'.fbx'))
    task.destination_path=REVISION+'/Meshes';task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    task.set_editor_property('async_',False);task.factory=u.FbxFactory();task.options=opts
    AT.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
    for i,slot in enumerate(slots):
        n=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        slot.set_editor_property('material_interface',mats[n]);slots[i]=slot
    mesh.set_editor_property('materials' if skeletal else 'static_materials',slots)
    E.set_metadata_tag(mesh,'TreasureDetailRevision','Detailed20261003')
    save(mesh);return mesh
def promote(source,target,skeletal,name):
    # Preserve the target UObject, reference skeleton and all actor references.
    readopts=u.GeometryScriptCopyMeshFromAssetOptions(use_build_scale=False)
    if skeletal:
        dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),readopts,u.GeometryScriptMeshReadLOD())
    else:
        dm,status=G.copy_mesh_from_static_mesh_v2(source,u.DynamicMesh(),readopts,u.GeometryScriptMeshReadLOD(),False)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy imported '+name)
    slots=list(source.get_editor_property('materials' if skeletal else 'static_materials'))
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.get_editor_property('material_interface') for s in slots],
        new_material_slot_names=[s.get_editor_property('material_slot_name') for s in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        use_build_scale=False,generate_lightmap_u_vs=u.GeometryScriptGenerateLightmapUVOptions.DO_NOT_GENERATE_LIGHTMAP_U_VS,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    if skeletal:_,status=G.copy_mesh_to_skeletal_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD())
    else:_,status=G.copy_mesh_to_static_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD(),False)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot update formal '+name)
    # Avoid carrying an old reimport filename/settings into future asset authoring.
    imp=target.get_editor_property('asset_import_data')
    if imp:
        imp.scripted_add_filename(str(HERE/'Authored'/(name+'.fbx')),0,'Detailed20261003')
        imp.set_editor_property('import_uniform_scale',1.)
        imp.set_editor_property('convert_scene',True);imp.set_editor_property('convert_scene_unit',True)
    if skeletal:
        sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
        build=sub.get_lod_build_settings(target,0)
        build.recompute_normals=False;build.recompute_tangents=True
        build.use_mikk_t_space=True;build.use_full_precision_u_vs=True
        sub.set_lod_build_settings(target,0,build)
    else:
        sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        build=sub.get_lod_build_settings(target,0)
        build.recompute_normals=False;build.recompute_tangents=True
        build.use_mikk_t_space=True;build.use_full_precision_u_vs=True
        build.use_high_precision_tangent_basis=True
        sub.set_lod_build_settings(target,0,build)
    E.set_metadata_tag(target,'TreasureModelRevision','Detailed20261003')
    E.set_metadata_tag(target,'TreasureAuthoring',str(HERE/'Scripts/author_chest.py'))
    save(target)
    return dict(asset=target.get_path_name(),revision_source=source.get_path_name())

record()
try:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve running game; cannot replace chest during play.')
    # Reversible, scoped backups; no scene loading, deletion or regeneration.
    for name in ('SK_GamedevTreasureChest','SM_TreasureChest_Closed','SM_TreasureChest_Open'):
        old=PROJECT/'Content/Props/GamedevTreasureChest20260922'/(name+'.uasset')
        backup=HERE/'BeforeRepair'/(name+'.uasset')
        if old.exists() and not backup.exists():backup.parent.mkdir(exist_ok=True);shutil.copy2(old,backup)
    report['stage']='materials'
    textures={f:{k:texture('T_TreasureDetail_'+f+'_'+k,k) for k in ('BaseColor','Normal','ORM')} for f in ('Iron','Gold')}
    mats={'Treasure_BlackIron':metalmaterial('Iron',textures['Iron']),
          'Treasure_AntiqueGold':metalmaterial('Gold',textures['Gold']),
          'Treasure_Interior':interior()}
    skeleton=asset(FORMAL+'/SK_GamedevTreasureChest_Skeleton')
    report['stage']='mesh_import';record()
    flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag)
    try:
        u.SystemLibrary.execute_console_command(None,flag+' 0')
        imported={n:importmesh(n,n.startswith('SK_'),skeleton,mats) for n in ('SK_GamedevTreasureChest','SM_TreasureChest_Closed','SM_TreasureChest_Open')}
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
    report['stage']='formal_mesh_write';record()
    report['meshes']={name:promote(src,asset(FORMAL+'/'+name),name.startswith('SK_'),name) for name,src in imported.items()}
    report.update(stage='assets_saved',skeleton_and_animations='Original packages reused without reimport',
                  materials={k:v.get_path_name() for k,v in mats.items()},
                  binding='Same formal UObjects updated in place from fresh revision mesh sources',
                  existing_maps='No reload or regeneration required; hard references keep the shared formal mesh')
    record()
    (HERE/'Receipts/published.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
except Exception as error:
    report.update(stage='failed',error=str(error),traceback=traceback.format_exc());record();raise
