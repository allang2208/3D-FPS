"""Install authored LODs on the two shipping models under their existing package names."""
import json
from pathlib import Path
import unreal as u

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parents[1]
STAGE = PROJECT / 'Saved/WoodworkingCrystalBench/Host'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != STAGE:
    raise RuntimeError('Run the private bench authoring host')
DEST = '/Game/Building/WoodworkingBenchV6Controls20261013'
CONTRACT = json.loads((SOURCE/'export-contract.json').read_text(encoding='utf-8-sig'))
SURFACES = json.loads((SOURCE/'Surfaces/materials.json').read_text(encoding='utf-8-sig'))
EDITOR = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
ASSETS = u.EditorAssetLibrary
NAMES = ('SM_WoodworkingBench', 'SM_WoodworkingBenchBody')
ROLES = {
    'WSBench_BenchWood':'oak', 'WSBench_EndGrain':'endgrain',
    'WSDetail_RackPaint':'iron', 'WSSculpt_Machined':'steel',
    'WSSculpt_RubberGrip':'leather', 'CrystalCore':'crystal', 'CrystalBrass':'brass'
}


def required(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing authored input ' + path)
    return asset


def align_bounds(mesh, template):
    prior, current = template.get_bounds(), mesh.get_bounds()
    low, high = [], []
    for axis in 'xyz':
        previous_mid, previous_half = getattr(prior.origin,axis), getattr(prior.box_extent,axis)
        mesh_mid, mesh_half = getattr(current.origin,axis), getattr(current.box_extent,axis)
        low.append(max(0., (mesh_mid-mesh_half) - (previous_mid-previous_half)))
        high.append(max(0., (previous_mid+previous_half) - (mesh_mid+mesh_half)))
    mesh.set_editor_property('negative_bounds_extension',u.Vector(*low))
    mesh.set_editor_property('positive_bounds_extension',u.Vector(*high))


def create_bench(name):
    template = required('/Game/CrystalBenchBaseline/'+name)
    spec = CONTRACT[name]
    files = [str(SOURCE/file) for file in spec['files']]
    task = u.AssetImportTask()
    task.filename = files[0]
    task.automated = True
    task.destination_name = name
    task.destination_path = DEST
    task.factory = u.FbxFactory()
    opt = u.FbxImportUI()
    opt.import_mesh = True
    opt.import_materials = opt.import_textures = opt.import_as_skeletal = False
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = opt.static_mesh_import_data
    data.combine_meshes = data.convert_scene = data.convert_scene_unit = data.transform_vertex_to_absolute = True
    data.auto_generate_collision = data.generate_lightmap_u_vs = data.remove_degenerates = False
    data.one_convex_hull_per_ucx = True
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options = opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = required(DEST+'/'+name)
    for lod in (1,2):
        if EDITOR.import_lod(mesh,lod,files[lod]) != lod:
            raise RuntimeError('Cannot import '+files[lod])
    imported_names = [str(s.material_slot_name) for s in mesh.static_materials]
    section_names = [[imported_names[EDITOR.get_lod_material_slot(mesh,lod,i)] for i in range(mesh.get_num_sections(lod))] for lod in range(3)]
    slots = list(template.static_materials)
    by_name = {str(slot.material_slot_name):slot for slot in slots}
    for key in spec['material_slots']:
        if key not in by_name:
            slot = u.StaticMaterial()
            slot.set_editor_property('material_slot_name',key)
            by_name[key]=slot
            slots.append(slot)
    for key, role in ROLES.items():
        if key in by_name:
            by_name[key].set_editor_property('material_interface',required(SURFACES[role]))
    mesh.set_editor_property('static_materials',slots)
    indices = {str(slot.material_slot_name):i for i,slot in enumerate(slots)}
    for lod, names in enumerate(section_names):
        for section,key in enumerate(names):
            EDITOR.set_lod_material_slot(mesh,indices[key],lod,section)
        build = EDITOR.get_lod_build_settings(mesh,lod)
        for prop,flag in dict(remove_degenerates=False,recompute_normals=False,recompute_tangents=True,use_mikk_t_space=True,use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,generate_lightmap_u_vs=False).items():
            build.set_editor_property(prop,flag)
        EDITOR.set_lod_build_settings(mesh,lod,build)
    for i,slot in enumerate(slots):
        mesh.set_material(i,slot.material_interface)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    EDITOR.set_nanite_settings(mesh,nanite,True)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    if not EDITOR.get_convex_collision_count(mesh):
        raise RuntimeError('Missing authored UCX for '+name)
    old_socket = template.find_socket('WoodworkingSawPivot')
    socket = u.new_object(u.StaticMeshSocket,outer=mesh)
    for prop in ('socket_name','relative_location','relative_rotation','relative_scale'):
        socket.set_editor_property(prop,old_socket.get_editor_property(prop))
    mesh.add_socket(socket)
    align_bounds(mesh,template)
    ASSETS.set_metadata_tag(mesh,'WoodworkingBenchRevision','CrystalDrive')
    if not EDITOR.set_lod_screen_sizes(mesh,[1.,.45,.18]) or not ASSETS.save_loaded_asset(mesh,False):
        raise RuntimeError('Failed to finish '+name)
    return dict(package=DEST+'/'+name,triangles=[mesh.get_num_triangles(i) for i in range(3)],collision_hulls=EDITOR.get_convex_collision_count(mesh),slots={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots})

result=[create_bench(name) for name in NAMES]
(SOURCE/'mesh-import.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
