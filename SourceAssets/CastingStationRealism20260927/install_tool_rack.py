"""Import the supported rack tools while preserving the currently assigned materials."""
from pathlib import Path
import datetime
import json
import unreal as u

root=Path(u.Paths.project_dir())
here=root/'SourceAssets/CastingStationRealism20260927'
manifest=json.loads((here/'Authored/manifest.json').read_text(encoding='utf-8'))
destination='/Game/Props/CastingStation20260926'
names=tuple(name for name in ('SM_CastingStation','SM_CastingStationBareRack',
    'SM_RackTongs','SM_RackHammer','SM_RackFile','SM_RackPoker','SM_BlacksmithTongs','SM_CoolingBarrel')
    if name in manifest['assets'])
E,A=u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop play before reimporting the tool rack; no game was stopped by this script')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection({destination+'/'+name for name in names}):
    raise RuntimeError('Unsaved tool rack target edits; preserving editor work')
station=u.load_asset(destination+'/SM_CastingStation')
materials={str(s.material_slot_name).split('.')[0]:s.material_interface for s in station.static_materials}
saved=[]

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    saved.append(asset.get_path_name())

for name in names:
    path=destination+'/'+name
    before=destination+'/RealismV5/BeforeWindV7/'+name
    previous=u.load_asset(path)
    if previous and not E.does_asset_exist(before):
        backup=E.duplicate_asset(path,before)
        if not backup:
            raise RuntimeError('Could not preserve previous mesh '+path)
        save(backup)
    sockets={}
    socket_source=station if name=='SM_CastingStationBareRack' else previous
    if socket_source:
        socket_reader=u.StaticMeshComponent()
        socket_reader.set_static_mesh(socket_source)
        for label in socket_reader.get_all_socket_names():
            socket=socket_source.find_socket(label)
            if socket:
                sockets[str(socket.socket_name)]=(socket.relative_location,socket.relative_rotation,socket.relative_scale)
        socket_reader.set_static_mesh(None)
    if previous:
        previous_data=previous.get_editor_property('asset_import_data')
        if isinstance(previous_data,u.FbxStaticMeshImportData):
            previous_data.set_editor_property('convert_scene_unit',True)
            previous_data.set_editor_property('import_uniform_scale',1.)
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh=True;options.import_as_skeletal=False
    options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True;data.import_uniform_scale=1
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=manifest['assets'][name]['fbx']
    task.destination_path=destination;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import produced no mesh '+name)
    mesh=u.load_asset(path)
    for index,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name).split('.')[0]
        if key not in materials or not materials[key]:
            raise RuntimeError('No existing station material for '+key)
        mesh.set_material(index,materials[key])
    # Keep the water-bearing assembly on authored triangles (SingleLayerWater).
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=name=='SM_CoolingBarrel'
    mesh.set_editor_property('nanite_settings',settings)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if name in ('SM_CastingStation','SM_CastingStationBareRack'):
        for label,point in manifest['sockets_ue_cm'].items():
            if label in sockets and label not in ('TongGrip','TongPivot'):
                continue
            previous_socket=sockets.get(label,(u.Vector(),u.Rotator(),u.Vector(1,1,1)))
            sockets[label]=(u.Vector(*point),previous_socket[1],previous_socket[2])
    for label,(location,rotation,scale) in sockets.items():
        socket=mesh.find_socket(label)
        if not socket:
            socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',location)
        socket.set_editor_property('relative_rotation',rotation)
        socket.set_editor_property('relative_scale',scale)
    E.set_metadata_tag(mesh,'SourceAuthoring','SourceAssets/CastingStationRealism20260927/author_geometry.py')
    if name.startswith('SM_Rack'):
        E.set_metadata_tag(mesh,'SwingPivot','Inner eye rim on fixed hook underside, UE cm z94.30')
    save(mesh)

receipt={'saved':saved,'tool_rack':manifest['tool_rack'],
         'existing_materials_preserved':{k:v.get_path_name() for k,v in materials.items()},
         'runtime_tested':False,'rendered':False}
(here/('tool-rack-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')).write_text(
    json.dumps(receipt,indent=2),encoding='utf-8')
print('TOOL_RACK_SAVED '+json.dumps(receipt),flush=True)
