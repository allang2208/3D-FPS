"""Background import and material repair, keeping all existing runtime asset paths."""
import json, re, shutil
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent;PROJECT=HERE.parents[1]
ROOT='/Game/Props/GamedevTreasureChest20260922'
CONTENT=PROJECT/'Content/Props/GamedevTreasureChest20260922'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Asset import needs editor mode; preserve the running game.')
saved=[]
# Keep the exact pre-repair packages locally; do not clean up or replace unrelated assets.
for relative in ['SK_GamedevTreasureChest','SK_GamedevTreasureChest_Skeleton',
                 'SM_TreasureChest_Closed','SM_TreasureChest_Open',
                 'Materials/M_Treasure_BlackIron','Materials/M_Treasure_AntiqueGold','Materials/M_Treasure_Interior']:
    source=CONTENT/(relative+'.uasset');backup=HERE/'BeforeRepair'/(relative+'.uasset')
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)

def save(asset):
    path=asset.get_path_name().split('.')[0]
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)],False):
        raise RuntimeError('Cannot save '+path)
    saved.append(asset.get_path_name())

def import_texture(name,normal=False):
    task=u.AssetImportTask();task.filename=str(HERE/'Textures'/(name+'.png'))
    task.destination_path=ROOT+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.set_editor_property('async_',False)
    AT.import_asset_tasks([task])
    texture=next((a for a in task.get_objects() if isinstance(a,u.Texture2D)),None)
    if texture is None:raise RuntimeError('Texture import failed '+name)
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS)
    save(texture);return texture

textures={}
for family in ('Iron','Gold'):
    textures[family]=(import_texture('T_Treasure_'+family+'_Surface'),import_texture('T_Treasure_'+family+'_Normal',True))

def connect(a,out,b,port):
    if not L.connect_material_expressions(a,out,b,port):raise RuntimeError('Material connection failed '+port)
def output(node,prop):
    if not L.connect_material_property(node,'',prop):raise RuntimeError('Material output connection failed '+str(prop))

recipes={
    'Treasure_BlackIron':('Iron',(.018,.020,.023),(.055,.058,.060),.85,.34,.56,4),
    'Treasure_AntiqueGold':('Gold',(.24,.125,.035),(.62,.39,.13),.90,.28,.45,5),
    'Treasure_Interior':('Iron',(.009,.008,.007),(.022,.019,.014),.10,.76,.92,3),
}
materials={}
for name,(family,dark,bright,metal,rmin,rmax,tiling) in recipes.items():
    mat=u.load_asset(ROOT+'/Materials/M_'+name)
    if mat is None:mat=AT.create_asset('M_'+name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    def node(cls,x,y):return L.create_material_expression(mat,cls,x,y)
    uv=node(u.MaterialExpressionTextureCoordinate,-700,0)
    uv.set_editor_property('u_tiling',float(tiling));uv.set_editor_property('v_tiling',float(tiling))
    surface=node(u.MaterialExpressionTextureSample,-470,0);surface.set_editor_property('texture',textures[family][0])
    surface.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    connect(uv,'',surface,'UVs')
    lo=node(u.MaterialExpressionConstant3Vector,-450,-320);lo.set_editor_property('constant',u.LinearColor(*dark,1))
    hi=node(u.MaterialExpressionConstant3Vector,-450,-180);hi.set_editor_property('constant',u.LinearColor(*bright,1))
    color=node(u.MaterialExpressionLinearInterpolate,-170,-230)
    connect(lo,'',color,'A');connect(hi,'',color,'B');connect(surface,'R',color,'Alpha');output(color,u.MaterialProperty.MP_BASE_COLOR)
    metallic=node(u.MaterialExpressionConstant,-150,-20);metallic.set_editor_property('r',metal);output(metallic,u.MaterialProperty.MP_METALLIC)
    rough=node(u.MaterialExpressionLinearInterpolate,-150,150);rough.set_editor_property('const_a',rmin);rough.set_editor_property('const_b',rmax)
    connect(surface,'B',rough,'Alpha');output(rough,u.MaterialProperty.MP_ROUGHNESS)
    normal=node(u.MaterialExpressionTextureSample,-460,340);normal.set_editor_property('texture',textures[family][1])
    normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    connect(uv,'',normal,'UVs');output(normal,u.MaterialProperty.MP_NORMAL)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    compile_result=L.recompile_material(mat)
    if isinstance(compile_result,(list,tuple)) and compile_result:
        raise RuntimeError('Material compile failed '+name+': '+str(compile_result))
    E.set_metadata_tag(mat,'TreasureMaterialVersion','2')
    E.set_metadata_tag(mat,'Source','Authored seamless micro-surface data; hollow treasure repair 2026-09-23')
    save(mat);materials[name]=mat

skeleton=u.load_asset(ROOT+'/SK_GamedevTreasureChest_Skeleton')
if not skeleton:raise RuntimeError('Existing hinge skeleton is missing')

def import_mesh(name,skeletal):
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.create_physics_asset=False;options.import_mesh=True;options.import_as_skeletal=skeletal
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    if skeletal:options.skeleton=skeleton
    data=options.skeletal_mesh_import_data if skeletal else options.static_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    if skeletal:data.set_editor_property('update_skeleton_reference_pose',False)
    else:
        data.combine_meshes=True;data.auto_generate_collision=True;data.generate_lightmap_u_vs=True
    task=u.AssetImportTask();task.filename=str(HERE/'Authored'/(name+'.fbx'))
    task.destination_path=ROOT;task.destination_name=name;task.automated=True
    task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    task.set_editor_property('async_',False);task.factory=u.FbxFactory();task.options=options
    AT.import_asset_tasks([task]);results=task.get_objects()
    mesh=next((a for a in results if a.get_path_name()==ROOT+'/'+name+'.'+name),None)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    assigned=[]
    if skeletal:
        # Unreal's native Array exposes value copies, so build a new list of edited structs.
        for slot in mesh.get_editor_property('materials'):
            slot_name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
            slot.set_editor_property('material_interface',materials[slot_name])
            assigned.append(slot)
        mesh.set_editor_property('materials',assigned)
    else:
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            slot_name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
            mesh.set_material(index,materials[slot_name])
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        build=subsystem.get_lod_build_settings(mesh,0)
        build.recompute_tangents=True
        build.use_mikk_t_space=True
        build.use_high_precision_tangent_basis=True
        build.use_full_precision_u_vs=True
        subsystem.set_lod_build_settings(mesh,0,build)
        nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite)
    E.set_metadata_tag(mesh,'TreasureModelRevision','HollowFinished20260923')
    save(mesh)
    return mesh

flag='Interchange.FeatureFlags.Import.FBX'
previous_flag=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    mesh=import_mesh('SK_GamedevTreasureChest',True)
    import_mesh('SM_TreasureChest_Closed',False)
    import_mesh('SM_TreasureChest_Open',False)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous_flag))
# The existing skeleton/reference pose and animation assets are deliberately unchanged.
receipt=dict(saved=saved,mesh=mesh.get_path_name(),asset_paths_preserved=True,
             existing_skeleton_and_animation_preserved=True,material_binding='Explicit edited struct list written to mesh',
             gui_editor_started=False,tested=False,rendered=False)
(HERE/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TREASURE_FINISHED_SAVED '+json.dumps(receipt))
