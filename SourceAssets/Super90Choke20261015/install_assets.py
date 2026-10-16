"""Import the shared choke mesh, WS1 finishes and production icon; no game run."""
import unreal as u
import json
from pathlib import Path
O=Path(__file__).parent
command=u.SystemLibrary.get_command_line().lower()
if '-run=pythonscript' in command and '-allowcommandletrendering' not in command:
    raise RuntimeError('Use AllowCommandletRendering for final static mesh build data')
D='/Game/Weapons/CommonShotgun/Choke20261015'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    obj.modify()
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    R['saved'].append(obj.get_path_name())
    record()
if '-run=pythonscript' not in command:
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('PIE is active; end the existing play session before importing')
if E.does_asset_exist(D+'/Meshes/SM_ShotgunChoke_Box01'):
    raise RuntimeError('Destination already exists; preserve prior import and resume explicitly')
master=load('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface')
flat_path=D+'/Textures/T_Choke_FlatNormal'
flat=load(flat_path) if E.does_asset_exist(flat_path) else E.duplicate_asset(
    '/Game/Weapons/A762/ADSSurface20261015/Textures/T_A762_FlatNormal',flat_path)
save(flat)
mask=load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral')
grey=load('/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear')
source=json.loads((O/'authoring_receipt.json').read_text())
bindings={}
for spec in source['materials']:
    name='MI_'+spec['name']
    path=D+'/Materials/'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,master)
    values={'SourceColorWeight':0,'SourceRoughnessWeight':0,'Roughness':spec['roughness'],
            'Metallic':spec['metallic'],'GrainTileCm':2,'GrainRoughness':0,'MottleRoughness':0,
            'MottleColor':0,'EdgeWear':0,'EdgeBreakup':0,'ScratchAmount':0,'HandlingPolish':0,
            'CavityDarken':0,'CavityRoughness':0,'Stipple':0,'MaskUVChannel':0,'WeaponWetness':0}
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
    L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*spec['base_color_linear']))
    for key,tex in [('SurfaceNormal',flat),('SurfaceMask',mask),('SourceRoughness',grey)]:
        L.set_material_instance_texture_parameter_value(mi,key,tex)
    L.update_material_instance(mi)
    save(mi)
    bindings[spec['name']]=mi

flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    imp=opt.static_mesh_import_data
    imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
    imp.import_mesh_lo_ds=True
    imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask()
    task.filename=str(O/'Exports/SM_ShotgunChoke_Box01_Lods.fbx')
    task.destination_path=D+'/Meshes';task.destination_name='SM_ShotgunChoke_Box01'
    task.automated=True;task.replace_existing=False;task.save=False
    task.factory=u.FbxFactory();task.options=opt
    A.import_asset_tasks([task])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
mesh=load(D+'/Meshes/SM_ShotgunChoke_Box01')
R['mesh_pending']=mesh.get_path_name();record()
slots=list(mesh.static_materials)
for i,slot in enumerate(slots):
    # FBX LOD re-import adds numeric suffixes to repeated material names.
    name=str(slot.material_slot_name)
    key=next((key for key in bindings if name==key or name.startswith(key+'.')),None)
    if key is None:raise RuntimeError('Unexpected material slot '+name)
    slot.material_interface=bindings[key];slots[i]=slot
mesh.set_editor_property('static_materials',slots)
u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for index in range(sms.get_lod_count(mesh)):
    settings=sms.get_lod_build_settings(mesh,index)
    settings.recompute_normals=False;settings.recompute_tangents=True
    settings.use_mikk_t_space=True;settings.use_high_precision_tangent_basis=True
    settings.use_full_precision_u_vs=True;settings.generate_lightmap_u_vs=False
    sms.set_lod_build_settings(mesh,index,settings)
for name,x in [('Mount',0),('Muzzle',24.8),('AimGuide',25.8)]:
    socket=u.new_object(u.StaticMeshSocket,outer=mesh)
    socket.set_editor_property('socket_name',name)
    socket.set_editor_property('relative_location',u.Vector(x,0,0))
    mesh.add_socket(socket)
if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):
    raise RuntimeError('Static mesh compilation did not finish')
E.set_metadata_tag(mesh,'ShotgunChokeSource','Super90Choke20261015; shared exterior; authored LODGroup; native SUPER90 upper-barrel seat')
save(mesh)
box=mesh.get_bounding_box()
R['mesh']={'path':mesh.get_path_name(),'lods':sms.get_lod_count(mesh),
           'materials':[slot.material_interface.get_path_name() for slot in mesh.static_materials],
           'bounds_cm':[[box.min.x,box.min.y,box.min.z],[box.max.x,box.max.y,box.max.z]],
           'full_build_complete':True,'muzzle_socket_cm':[24.8,0,0]}
icon_file=O/'muzzle_shotgun_choke.png'
icon_task=u.AssetImportTask();icon_task.filename=str(icon_file)
icon_task.destination_path=D+'/UI';icon_task.destination_name='T_ShotgunChoke_Icon'
icon_task.automated=True;icon_task.replace_existing=False;icon_task.save=False
A.import_asset_tasks([icon_task])
icon=load(D+'/UI/T_ShotgunChoke_Icon')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
save(icon)
R['complete']=True;record()
print('SHOTGUN_CHOKE_ASSETS_SAVED',json.dumps(R),flush=True)
