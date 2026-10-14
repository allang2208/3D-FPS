"""Scoped V3 import. Run only through the repository's serialized editor bridge."""
import unreal as u
import json,hashlib,traceback,re
from pathlib import Path
WORK=Path(r'C:/Users/allan/Documents/Codex/2026-10-04/task-2/chest_v3_import')
SOURCE=Path('D:/FPS3D/FPSGAME/SourceAssets/GamedevTreasureChestV3_20261004')
FORMAL='/Game/Props/GamedevTreasureChest20260922'
REV='/Game/Props/GamedevTreasureChestV3_20261004'
TAG='CloudV3_158044_20261004'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils
AT=u.AssetToolsHelpers.get_asset_tools()
report={'stage':'preflight','saved':[],'formal_paths_preserved':True,'geometry':'Cloud V3 only',
        'authoritative_blend_version':'5.2.2; original file retained unchanged',
        'portable_texture_names':'T_TreasureV2_* names are intentional V3 bundle payloads',
        'normal_policy':'Delivered OpenGL Y+ normal maps; flip green once in UE, strength 1',
        'material_policy':'Portable tinted/AO-baked PBR plus UV1/vertex-color selective edge polish reconstructed from source nodes'}
def record():
    (WORK/'install_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    receipts=SOURCE/'Receipts'
    if receipts.exists():(receipts/'install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing asset: '+path)
    return obj
def save(obj):
    obj.modify()
    if not E.save_loaded_asset(obj,False):
        if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outer()],False):
            raise RuntimeError('Save failed: '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def connect(a,out,b,port):
    if not L.connect_material_expressions(a,out,b,port):raise RuntimeError('Cannot connect '+port)
def output(a,out,prop):
    if not L.connect_material_property(a,out,prop):raise RuntimeError('Cannot connect output '+str(prop))
def texture(family,kind):
    name='T_TreasureV2_'+family+'_'+kind
    path=REV+'/Textures/'+name
    tex=u.load_asset(path)
    if tex:
        if E.get_metadata_tag(tex,'TreasureV3Revision')!=TAG:raise RuntimeError('Existing unowned texture '+path)
        return tex
    task=u.AssetImportTask();task.filename=str(SOURCE/'exports/Textures'/(name+'.png'))
    task.destination_path=REV+'/Textures';task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False;task.set_editor_property('async_',False)
    AT.import_asset_tasks([task]);tex=load(path)
    tex.set_editor_property('srgb',kind=='BaseColor')
    compression={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'ORM':u.TextureCompressionSettings.TC_MASKS,'NormalGL':u.TextureCompressionSettings.TC_NORMALMAP}
    tex.set_editor_property('compression_settings',compression[kind])
    if kind=='NormalGL':tex.set_editor_property('flip_green_channel',True)
    E.set_metadata_tag(tex,'TreasureV3Revision',TAG);save(tex);return tex
def material(family,textures):
    path=REV+'/Materials/M_TreasureV3_'+family
    existing=u.load_asset(path)
    if existing:
        if E.get_metadata_tag(existing,'TreasureV3Revision')==TAG:return existing
        raise RuntimeError('Existing incomplete material; do not rebuild referenced graph: '+path)
    mat=AT.create_asset('M_TreasureV3_'+family,REV+'/Materials',u.Material,u.MaterialFactoryNew())
    def node(cls,x,y):return L.create_material_expression(mat,cls,x,y)
    uv=node(u.MaterialExpressionTextureCoordinate,-1000,-200);uv.set_editor_property('coordinate_index',0)
    samples={}
    for i,kind in enumerate(('BaseColor','ORM','NormalGL')):
        n=node(u.MaterialExpressionTextureSample,-750,-350+i*350)
        n.set_editor_property('texture',textures[kind])
        n.set_editor_property('sampler_type',{'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'NormalGL':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[kind])
        connect(uv,'',n,'UVs');samples[kind]=n
    base,orm,normal=[samples[k] for k in ('BaseColor','ORM','NormalGL')]
    if family in ('Iron','Gold'):
        wearuv=node(u.MaterialExpressionTextureCoordinate,-1000,800);wearuv.set_editor_property('coordinate_index',1)
        vertex=node(u.MaterialExpressionVertexColor,-1000,1050)
        wear=node(u.MaterialExpressionCustom,-700,850)
        inputs=[]
        for name in ('WearUV','Vertex','Rough'):
            item=u.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
        wear.set_editor_property('inputs',inputs);wear.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
        rough_scale=.20 if family=='Iron' else .22
        bevel=.40 if family=='Iron' else .34
        code=('float2 edge=min(WearUV,1-WearUV)*(Vertex.gb*200.0); '
              'float valid=min(Vertex.g,Vertex.b)>0.00001?1.0:0.0; '
              'float rim=saturate(1.0-min(edge.x,edge.y)/0.16)*valid*0.18; '
              f'float detail=saturate((Rough-0.34)/{rough_scale}); '
              f'return max(rim,Vertex.r*{bevel})*(0.7+0.3*detail);')
        wear.set_editor_property('code',code)
        connect(wearuv,'',wear,'WearUV');connect(vertex,'',wear,'Vertex');connect(orm,'G',wear,'Rough')
        bright=node(u.MaterialExpressionConstant3Vector,-500,-500)
        rgb=(.135,.150,.165) if family=='Iron' else (.55,.34,.116)
        bright.set_editor_property('constant',u.LinearColor(*rgb,1))
        blend=node(u.MaterialExpressionLinearInterpolate,-200,-300)
        connect(base,'RGB',blend,'A');connect(bright,'',blend,'B');connect(wear,'',blend,'Alpha')
        output(blend,'',u.MaterialProperty.MP_BASE_COLOR)
        rough=node(u.MaterialExpressionLinearInterpolate,-200,50);rough.set_editor_property('const_b',.24 if family=='Iron' else .27)
        connect(orm,'G',rough,'A');connect(wear,'',rough,'Alpha');output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    else:
        output(base,'RGB',u.MaterialProperty.MP_BASE_COLOR);output(orm,'G',u.MaterialProperty.MP_ROUGHNESS)
    output(orm,'B',u.MaterialProperty.MP_METALLIC)
    output(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(normal,'RGB',u.MaterialProperty.MP_NORMAL)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    result=L.recompile_material(mat)
    if isinstance(result,(list,tuple)) and result:raise RuntimeError('Material compile: '+str(result))
    E.set_metadata_tag(mat,'TreasureV3Revision',TAG);save(mat);return mat
def import_mesh(name,skeletal,skeleton,materials):
    path=REV+'/Meshes/'+name
    existing=u.load_asset(path)
    if existing:
        if E.get_metadata_tag(existing,'TreasureV3Revision')==TAG:return existing
        raise RuntimeError('Existing incomplete mesh: '+path)
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.import_mesh=True;opts.import_as_skeletal=skeletal;opts.import_animations=False
    opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    if skeletal:opts.skeleton=skeleton
    data=opts.skeletal_mesh_import_data if skeletal else opts.static_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.0
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    if skeletal:data.set_editor_property('update_skeleton_reference_pose',False)
    else:
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    task=u.AssetImportTask()
    task.filename=str(SOURCE/('exports/TreasureChest_v3.fbx' if skeletal else 'Derived/'+name+'.fbx'))
    task.destination_path=REV+'/Meshes';task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    task.set_editor_property('async_',False);task.factory=u.FbxFactory();task.options=opts
    AT.import_asset_tasks([task]);mesh=load(path)
    slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
    report.setdefault('imported_slots',{})[name]=[str(s.material_slot_name) for s in slots]
    if len(slots)!=3:raise RuntimeError('Expected 3 material slots')
    for i,slot in enumerate(slots):
        slotname=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        slot.material_interface=materials[slotname];slots[i]=slot
    mesh.set_editor_property('materials' if skeletal else 'static_materials',slots)
    E.set_metadata_tag(mesh,'TreasureV3Revision',TAG);save(mesh);return mesh
def dynamic(mesh,skeletal):
    opts=u.GeometryScriptCopyMeshFromAssetOptions(use_build_scale=False)
    if skeletal:dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),opts,u.GeometryScriptMeshReadLOD())
    else:dm,status=G.copy_mesh_from_static_mesh_v2(mesh,u.DynamicMesh(),opts,u.GeometryScriptMeshReadLOD(),False)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+mesh.get_path_name())
    if dm.get_triangle_count()!=158044:raise RuntimeError('Unexpected triangle count '+str(dm.get_triangle_count()))
    return dm
def promote(src,target,skeletal,name):
    dm=dynamic(src,skeletal)
    slots=list(src.get_editor_property('materials' if skeletal else 'static_materials'))
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,use_build_scale=False,
        generate_lightmap_u_vs=u.GeometryScriptGenerateLightmapUVOptions.DO_NOT_GENERATE_LIGHTMAP_U_VS,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    if skeletal:_,status=G.copy_mesh_to_skeletal_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD())
    else:_,status=G.copy_mesh_to_static_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD(),False)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot promote '+name)
    imp=target.get_editor_property('asset_import_data')
    if imp:
        filename=SOURCE/('exports/TreasureChest_v3.fbx' if skeletal else 'Derived/'+name+'.fbx')
        imp.scripted_add_filename(str(filename),0,TAG)
        imp.set_editor_property('import_uniform_scale',1.0)
        imp.set_editor_property('convert_scene',True);imp.set_editor_property('convert_scene_unit',True)
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem if skeletal else u.StaticMeshEditorSubsystem)
    build=sub.get_lod_build_settings(target,0)
    build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True;build.use_full_precision_u_vs=True
    if not skeletal:build.use_high_precision_tangent_basis=True
    sub.set_lod_build_settings(target,0,build)
    E.set_metadata_tag(target,'TreasureModelRevision',TAG)
    E.set_metadata_tag(target,'TreasureAuthoring',str(SOURCE/'TreasureChest_v3.blend'))
    E.set_metadata_tag(target,'TreasureV3Revision',TAG)
    save(target)
    return {'path':target.get_path_name(),'source':src.get_path_name(),'triangles':dynamic(target,skeletal).get_triangle_count()}
record()
try:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Running game detected; no asset replacement during play')
    if Path(u.Paths.get_project_file_path()).name!='FPSGAME.uproject':raise RuntimeError('Wrong editor project')
    dirty=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['preexisting_dirty_content']=dirty
    report['preexisting_dirty_maps']=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    conflicts=[p for p in dirty if p.startswith(FORMAL) or p.startswith(REV)]
    if conflicts:raise RuntimeError('Unsubmitted treasure edits exist: '+str(conflicts))
    backup=json.loads((WORK/'backup_receipt.json').read_text(encoding='utf-8'))
    protected=[]
    for row in backup['files']:
        if row['relative'].startswith('Content/Props/GamedevTreasureChest20260922/'):
            current=hashlib.file_digest(Path(row['original']).open('rb'),'sha256').hexdigest()
            if current!=row['sha256']:raise RuntimeError('Formal asset changed since backup: '+row['relative'])
            if Path(row['relative']).stem.startswith('A_') or Path(row['relative']).stem.endswith('_Skeleton'):protected.append(row)
    names=('SK_GamedevTreasureChest','SM_TreasureChest_Closed','SM_TreasureChest_Open')
    targets={name:load(FORMAL+'/'+name) for name in names}
    skeleton=load(FORMAL+'/SK_GamedevTreasureChest_Skeleton')
    report['stage']='materials';record()
    tex={f:{k:texture(f,k) for k in ('BaseColor','ORM','NormalGL')} for f in ('Iron','Gold','Wood')}
    materials={'Treasure_BlackIron':material('Iron',tex['Iron']),
               'Treasure_AntiqueGold':material('Gold',tex['Gold']),
               'Treasure_Interior':material('Wood',tex['Wood'])}
    report['stage']='revision_import';record()
    flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag)
    try:
        u.SystemLibrary.execute_console_command(None,flag+' 0')
        imported={name:import_mesh(name,name.startswith('SK_'),skeleton,materials) for name in names}
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
    report['revision_triangles']={name:dynamic(mesh,name.startswith('SK_')).get_triangle_count() for name,mesh in imported.items()}
    dm=dynamic(imported['SK_GamedevTreasureChest'],True)
    box=u.GeometryScript_MeshQueries.get_mesh_bounding_box(dm)
    dims=[box.max.x-box.min.x,box.max.y-box.min.y,box.max.z-box.min.z]
    report['closed_dimensions_cm']=dims
    if any(abs(a-b)>.2 for a,b in zip(dims,[104.5525,138.255,104.195])):raise RuntimeError('Imported dimensions differ: '+str(dims))
    if u.GeometryScript_MeshQueries.get_num_uv_sets(dm)<2:raise RuntimeError('Missing UV1')
    if not u.GeometryScript_MeshQueries.get_has_vertex_colors(dm):raise RuntimeError('Missing wear vertex colors')
    report['stage']='formal_promotion';record()
    report['meshes']={name:promote(imported[name],targets[name],name.startswith('SK_'),name) for name in names}
    report['unchanged_skeleton_and_clips']=[]
    for row in protected:
        if hashlib.file_digest(Path(row['original']).open('rb'),'sha256').hexdigest()!=row['sha256']:
            raise RuntimeError('Protected original package unexpectedly changed '+row['relative'])
        report['unchanged_skeleton_and_clips'].append(row['relative'])
    report['materials']={k:v.get_path_name() for k,v in materials.items()}
    report['stage']='saved';record()
    print(json.dumps(report,ensure_ascii=False))
except Exception as e:
    report.update(stage='failed',error=str(e),traceback=traceback.format_exc());record();raise
