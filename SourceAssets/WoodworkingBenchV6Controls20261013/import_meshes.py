import unreal as u,json,re
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
SOURCE=ROOT/'SourceAssets/WoodworkingBenchV6Controls20261013'
HOST=ROOT/'Saved/WoodworkingControls20261013/ImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use isolated import host')
DEST='/Game/Building/WoodworkingBenchV6Controls20261013'
manifest=json.loads((SOURCE/'layout_manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
canon=lambda name:re.sub('[^a-z0-9]','',str(name).lower())
import runpy
paint=runpy.run_path(str(SOURCE/'paint_material.py'))['build'](DEST)
records=[]
for entry in manifest['meshes']:
    name=entry['name'];old=u.load_asset('/Game/Building/WoodworkingBenchV4/'+name)
    if not old:raise RuntimeError('Source materials unavailable')
    mats={canon(s.material_slot_name):s.material_interface for s in old.static_materials}
    is_blade=name.endswith('SawBlade');mats[canon('WW_SawEdgePaint')]=paint['blade' if is_blade else 'merged']
    if E.does_asset_exist(DEST+'/'+name) and not E.delete_asset(DEST+'/'+name):raise RuntimeError('Could not replace isolated candidate '+name)
    task=u.AssetImportTask();task.filename=str(SOURCE/'GameReady'/f'{name}_LOD0.fbx');task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
    data.generate_lightmap_u_vs=False;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True;data.remove_degenerates=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Import failed '+name)
    for lod in (1,2):
        if sub.import_lod(mesh,lod,str(SOURCE/'GameReady'/f'{name}_LOD{lod}.fbx'))!=lod:raise RuntimeError('LOD save failed')
    unique=list(old.static_materials)
    edge_slot=u.StaticMaterial();edge_slot.set_editor_property('material_slot_name','WW_SawEdgePaint');edge_slot.set_editor_property('material_interface',mats[canon('WW_SawEdgePaint')]);unique.append(edge_slot)
    indices={canon(slot.material_slot_name):i for i,slot in enumerate(unique)};remap={}
    for i,slot in enumerate(mesh.static_materials):
        key=canon(slot.material_slot_name)
        if key not in indices:raise RuntimeError('Unknown source surface '+key)
        remap[i]=indices[key]
    section_slots=[[sub.get_lod_material_slot(mesh,lod,j) for j in range(mesh.get_num_sections(lod))] for lod in range(3)]
    mesh.set_editor_property('static_materials',unique)
    for lod in range(3):
        for section,old_slot in enumerate(section_slots[lod]):
            sub.set_lod_material_slot(mesh,remap[old_slot],lod,section)
        settings=sub.get_lod_build_settings(mesh,lod)
        for key,value in dict(remove_degenerates=False,recompute_normals=False,recompute_tangents=True,use_mikk_t_space=True,use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,generate_lightmap_u_vs=False).items():settings.set_editor_property(key,value)
        sub.set_lod_build_settings(mesh,lod,settings)
    for i,slot in enumerate(unique):mesh.set_material(i,mats[canon(slot.material_slot_name)])
    nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;sub.set_nanite_settings(mesh,nan,True)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    if not is_blade:
        existing=mesh.find_socket('WoodworkingSawPivot')
        if existing:mesh.remove_socket(existing)
        socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name','WoodworkingSawPivot');socket.set_editor_property('relative_location',u.Vector(86.5,0,88.8));mesh.add_socket(socket)
    # Preserve the old placement envelope although the protruding vise moved under the table.
    original=old.get_bounds();actual=mesh.get_bounds()
    omin=[getattr(original.origin,c)-getattr(original.box_extent,c) for c in 'xyz'];omax=[getattr(original.origin,c)+getattr(original.box_extent,c) for c in 'xyz']
    nmin=[getattr(actual.origin,c)-getattr(actual.box_extent,c) for c in 'xyz'];nmax=[getattr(actual.origin,c)+getattr(actual.box_extent,c) for c in 'xyz']
    mesh.set_editor_property('negative_bounds_extension',u.Vector(*[max(0,nmin[i]-omin[i]) for i in range(3)]))
    mesh.set_editor_property('positive_bounds_extension',u.Vector(*[max(0,omax[i]-nmax[i]) for i in range(3)]))
    triangles=[mesh.get_num_triangles(i) for i in range(3)]
    E.set_metadata_tag(mesh,'WoodworkingBenchRevision','V6Controls20261013')
    import hashlib
    E.set_metadata_tag(mesh,'WoodworkingBenchSourceManifestSHA256',hashlib.sha256((SOURCE/'layout_manifest.json').read_bytes()).hexdigest())
    sub.set_lod_screen_sizes(mesh,[1,.45,.18])
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Could not save '+name)
    records.append(dict(mesh=mesh.get_path_name(),triangles=triangles,collision_count=sub.get_convex_collision_count(mesh),materials=[s.material_interface.get_path_name() for s in mesh.static_materials]))
(SOURCE/'import_receipt.json').write_text(json.dumps(dict(meshes=records,source=str(SOURCE/'layout_manifest.json'),gameplay_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('WOODWORKING_CLEAN_ASSETS_SAVED',json.dumps(records))
