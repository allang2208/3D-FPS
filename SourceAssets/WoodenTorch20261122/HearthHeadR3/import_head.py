"""Save a corrected held mesh and icon under new package names, using the original PBR materials."""
from pathlib import Path
import json,os
import unreal as u
root=Path(os.environ['FPS_PROJECT_ROOT'])
batch=Path(os.environ['TORCH_BATCH'])
family=root/'SourceAssets/WoodenTorch20261122'
src=family/'HearthHeadR3/Export'
base='/Game/Weapons/WoodenTorch20261122'
lib=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
def take(path,dest,name,options=None):
    task=u.AssetImportTask()
    task.filename=str(path);task.destination_name=name;task.destination_path=dest
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    tools.import_asset_tasks([task])
    asset=lib.load_asset(dest+'/'+name)
    if asset is None:raise RuntimeError('Failed to import '+name)
    return asset
def bounds(obj):
    ext=obj.get_bounds().box_extent; org=obj.get_bounds().origin
    return dict(origin_cm=[org.x,org.y,org.z],size_cm=[ext.x*2,ext.y*2,ext.z*2])
previous=lib.load_asset(base+'/SM_WoodenTorch')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI()
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
mesh=take(src/'SM_WoodenTorch.fbx',base+'/HearthHeadR3','SM_HandheldHearth',opt)
slots=[]
for i,slot in enumerate(mesh.static_materials):
    name=str(slot.material_slot_name)
    mat=lib.load_asset(base+'/FabHandheldR2/M_HandheldTorch_'+name)
    if mat is None:raise RuntimeError('Missing surface '+name)
    mesh.set_material(i,mat);slots.append(name)
fit=json.loads((src/'fit.json').read_text())
sockets={'Grip':[0,0,0],'Flame':fit['flame_socket_ue_cm'],**json.loads((family/'FabHandheldR2/Export/hands.json').read_text())['sockets_ue_cm']}
for name,loc in sockets.items():
    sock=mesh.find_socket(name)
    if not sock:
        sock=u.new_object(u.StaticMeshSocket,outer=mesh)
        sock.set_editor_property('socket_name',name);mesh.add_socket(sock)
    sock.set_editor_property('relative_location',u.Vector(*loc))
current=bounds(mesh)
if set(slots)!={'Wood','Rope','Cloth'} or not (60<current['size_cm'][2]<64 and max(current['size_cm'][:2])<10):
    raise RuntimeError('Incorrect assembled head '+str(current)+' '+str(slots))
icon=take(src/'ue_wooden_torch.png','/Game/ColdSteelData/Icons','ue_wooden_torch_r3')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
for obj in [mesh,icon]:
    if not lib.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
(batch/'head-saved.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),icon=icon.get_path_name(),slots=slots,sockets=sockets,before=bounds(previous),after=current),indent=2))
