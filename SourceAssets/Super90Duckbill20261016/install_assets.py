"""Import/save the cosmetic duckbill model, smooth WS1 finishes and framed icon."""
import unreal as u,json,re,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/CommonShotgun/Duckbill20261016'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    obj.modify()
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    R['saved'].append(obj.get_path_name());record()
command=u.SystemLibrary.get_command_line().lower()
if '-run=pythonscript' in command:
    if '-allowcommandletrendering' not in command:raise RuntimeError('Mesh build requires RHI commandlet')
elif u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before import')
if any(p.get_name().startswith(D+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Target package has unsaved changes')
master=load('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface')
flat=load('/Game/Weapons/CommonShotgun/Choke20261015/Textures/T_Choke_FlatNormal')
mask=load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral')
grey=load('/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear')
source=json.loads((O/'authoring_receipt.json').read_text());bindings={}
for spec in source['materials']:
    name='MI_'+spec['name'];path=D+'/Materials/'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,master)
    values={'SourceColorWeight':0,'SourceRoughnessWeight':0,'Roughness':spec['roughness'],'Metallic':spec['metallic'],
        'GrainTileCm':2,'GrainRoughness':0,'MottleRoughness':0,'MottleColor':0,'EdgeWear':0,'EdgeBreakup':0,
        'ScratchAmount':0,'HandlingPolish':0,'CavityDarken':0,'CavityRoughness':0,'Stipple':0,'MaskUVChannel':0,'WeaponWetness':0}
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
    L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*spec['base_color_linear']))
    for key,texture in [('SurfaceNormal',flat),('SurfaceMask',mask),('SourceRoughness',grey)]:
        L.set_material_instance_texture_parameter_value(mi,key,texture)
    L.update_material_instance(mi);save(mi);bindings[spec['name']]=mi
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False
    imp.generate_lightmap_u_vs=False;imp.import_mesh_lods=True;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(O/'Exports/SM_ShotgunDuckbill01_Lods.fbx')
    task.destination_path=D+'/Meshes';task.destination_name='SM_ShotgunDuckbill01'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
mesh=load(D+'/Meshes/SM_ShotgunDuckbill01');slots=list(mesh.static_materials)
for i,slot in enumerate(slots):
    key=re.sub(r'(?:\.\d+|_\d+)$','',str(slot.material_slot_name));slot.material_interface=bindings[key];slots[i]=slot
mesh.set_editor_property('static_materials',slots);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for level in range(sms.get_lod_count(mesh)):
    settings=sms.get_lod_build_settings(mesh,level);settings.recompute_normals=False;settings.recompute_tangents=True
    settings.use_mikk_t_space=True;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
    settings.generate_lightmap_u_vs=False;sms.set_lod_build_settings(mesh,level,settings)
for name,x in [('Mount',0),('Muzzle',9.2),('AimGuide',10.2)]:
    socket=mesh.find_socket(name)
    if not socket:
        socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
    socket.set_editor_property('relative_location',u.Vector(x,0,0))
if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Mesh build incomplete')
E.set_metadata_tag(mesh,'ShotgunDuckbillSource',str(O/'authoring_receipt.json'));save(mesh)
R['mesh']={'asset':mesh.get_path_name(),'lods':sms.get_lod_count(mesh),'muzzle_socket_cm':[9.2,0,0],
    'materials':[s.material_interface.get_path_name() for s in slots]};record()
icon_name='muzzle_shotgun_duckbill';icon_file=O/(icon_name+'.png')
shutil.copy2(icon_file,P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(icon_name+'.png'))
for destination,name in [('/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms',icon_name),(D+'/UI','T_ShotgunDuckbill_Icon')]:
    task=u.AssetImportTask();task.filename=str(icon_file);task.destination_path=destination;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
    icon=load(destination+'/'+name);icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.srgb=True;icon.never_stream=True
    E.set_metadata_tag(icon,'Icon.SourceRecipe',str(O/'generation_prompts.json'));save(icon)
R['complete']=True;record();print('SHOTGUN_DUCKBILL_ASSETS_SAVED',flush=True)
