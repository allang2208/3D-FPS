"""Save the authored repair at the existing station paths; do not touch levels or PIE."""
from pathlib import Path
import json,datetime,sys,importlib
import unreal as u
ROOT=Path(u.Paths.project_dir());HERE=ROOT/'SourceAssets/CastingStationRealism20260927'
sys.path.insert(0,str(HERE))
import materials
importlib.reload(materials)
DEST='/Game/Props/CastingStation20260926'
MAN=json.loads((HERE/'Authored/manifest.json').read_text(encoding='utf8'))
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
saved=[]
def save(a):
    if isinstance(a,u.Material):
        errors=L.recompile_material(a)
        if errors:raise RuntimeError('Material compile failed '+a.get_path_name()+': '+str(errors))
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    saved.append(a.get_path_name())

def run(owned_dirty=()):
    commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop play before reimporting the station; no game was stopped by this script')
    targets={DEST+'/'+n for n in MAN['assets']}|{DEST+'/SM_CastingAnvil'}
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if targets.intersection(dirty) or any(p.startswith(materials.DEST+'/') for p in dirty.difference(owned_dirty)):
        raise RuntimeError('Unsaved target content; preserve current edits')
    mats=materials.build()
    for m in mats.values():save(m)
    mats['Masonry']=u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_Masonry')
    mats['PolishedSteel']=mats['FrameSteel']
    for name,record in MAN['assets'].items():
        path=DEST+'/'+name
        archive=materials.DEST+'/Before/'+name
        if E.does_asset_exist(path) and not E.does_asset_exist(archive):
            copy=E.duplicate_asset(path,archive)
            if not copy:raise RuntimeError('Could not preserve previous mesh '+path)
            save(copy)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
        data=opt.static_mesh_import_data
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True;data.import_uniform_scale=1
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        existing=u.load_asset(path)
        if existing:
            previous=existing.get_editor_property('asset_import_data')
            if isinstance(previous,u.FbxStaticMeshImportData):
                previous.set_editor_property('convert_scene_unit',True);previous.set_editor_property('import_uniform_scale',1.)
        task=u.AssetImportTask();task.filename=record['fbx'];task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Import failed '+path)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=str(slot.material_slot_name).split('.')[0]
            if key not in mats:raise RuntimeError('Unknown authored material slot '+key)
            mesh.set_material(i,mats[key])
        # UE's Nanite shading-model gate excludes SingleLayerWater. The assembly includes
        # the water section, so it uses its authored triangles; the separate barrel stays Nanite.
        settings=mesh.get_editor_property('nanite_settings');settings.enabled=name=='SM_CoolingBarrel';mesh.set_editor_property('nanite_settings',settings)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if name in ('SM_CastingStation','SM_CastingStationBareRack'):
            for label,point in MAN['sockets_ue_cm'].items():
                socket=mesh.find_socket(label)
                if not socket:
                    socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
                socket.set_editor_property('relative_location',u.Vector(*point))
        E.set_metadata_tag(mesh,'SourceAuthoring','SourceAssets/CastingStationRealism20260927/author_geometry.py')
        save(mesh)
    anvil=u.load_asset(DEST+'/SM_CastingAnvil')
    for i,slot in enumerate(anvil.static_materials):
        if str(slot.material_slot_name).split('.')[0] in ('AnvilSteel','AnvilForge','AnvilFace','AnvilHorn'):anvil.set_material(i,mats['AnvilSteel'])
    save(anvil)
    receipt={'saved':saved,'source':str(HERE),'barrel':'closed shared-vertex wall; upright Normandy oak',
      'water':'Clearwater ripple normal and UE SingleLayerWater optics; basin-local waves',
      'anvil_geometry_changed':False,'runtime_tested':False,'rendered':False}
    out=HERE/('install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    out.write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('CASTING_REALISM_SAVED '+json.dumps(receipt),flush=True)
if __name__=='__main__':run()
