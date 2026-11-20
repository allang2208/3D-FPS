"""Import authored FBXs inside the dedicated asset-only commandlet host."""
from pathlib import Path
import json
import unreal as ue


SOURCE = Path(__file__).resolve().parent
DEST = '/Game/WorldGeneration/VillageTavern/Furniture'
VILLAGE = '/Game/WorldGeneration/TemperateHills'
SURFACE = VILLAGE + '/VillageCarpenter/Props/Surfaces/M_Carpenter'
MATERIAL_PATHS = {
    'Oak': VILLAGE + '/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'Sawn': SURFACE + 'Sawn', 'Iron': SURFACE + 'Iron', 'Endgrain': SURFACE + 'Cut',
    'Rot': SURFACE + 'Rot',
}
ASSETS = ('Table','Stool','Counter','Backbar','BrokenTable','BrokenStool','BrokenCounter')
MATERIALS = {key: ue.load_asset(path) for key,path in MATERIAL_PATHS.items()}
if not all(MATERIALS.values()):
    raise RuntimeError('Could not load all four source materials: ' + str(MATERIALS))
tools = ue.AssetToolsHelpers.get_asset_tools()
editor = ue.EditorAssetLibrary
subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
host = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
service_only = (host/'counter-service.only').exists()
if service_only:
    ASSETS = ('Counter_Service',)
ue.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST],True)
paths = []
report = {}


def oiled_oak():
    name = 'M_TavernOiledOak'
    path = DEST + '/' + name
    if editor.does_asset_exist(path):
        return ue.load_asset(path)
    mat = tools.create_asset(name,DEST,ue.Material,ue.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    graph = ue.MaterialEditingLibrary
    def node(kind):
        return graph.create_material_expression(mat,getattr(ue,'MaterialExpression'+kind))
    def texture(suffix,sampler):
        tex=node('TextureSample')
        tex.texture=ue.load_asset('/Game/UnrealNormandy/Textures/T_WoodSurface_00A_'+suffix)
        if not tex.texture:
            raise RuntimeError('Missing surface source ' + suffix)
        tex.sampler_type=getattr(ue.MaterialSamplerType,'SAMPLERTYPE_'+sampler)
        return tex
    def wire(src,out,dest,pin):
        if not graph.connect_material_expressions(src,out,dest,pin):
            raise RuntimeError('Material connection failed at ' + pin)
    def output(src,out,key):
        if not graph.connect_material_property(src,out,getattr(ue.MaterialProperty,'MP_'+key)):
            raise RuntimeError('Material output failed at ' + key)
    def color(rgb):
        value=node('Constant3Vector')
        value.constant=ue.LinearColor(*rgb,1)
        return value
    def number(x):
        value=node('Constant')
        value.r=x
        return value
    albedo=texture('BaseColor','COLOR')
    tone=node('Multiply')
    wire(albedo,'RGB',tone,'A')
    wire(color((.88,.77,.59)),'',tone,'B')
    finish=node('Add')
    wire(tone,'',finish,'A')
    wire(color((.022,.012,.007)),'',finish,'B')
    output(finish,'','BASE_COLOR')
    bump=node('LinearInterpolate')
    wire(number(.58),'',bump,'Alpha')
    wire(color((0,0,1)),'',bump,'A')
    wire(texture('Normal','NORMAL'),'RGB',bump,'B')
    output(bump,'','NORMAL')
    packed=texture('RHAOM','MASKS')
    rough=node('Multiply')
    wire(number(.22),'',rough,'B')
    wire(packed,'R',rough,'A')
    wax=node('Add')
    wire(number(.34),'',wax,'B')
    wire(rough,'',wax,'A')
    output(wax,'','ROUGHNESS')
    output(packed,'B','AMBIENT_OCCLUSION')
    graph.recompile_material(mat)
    if not editor.save_loaded_asset(mat,False):
        raise RuntimeError('Could not save '+path)
    paths.append(path)
    return mat


MATERIALS['OiledOak'] = oiled_oak()


def slot_key(slot):
    try:
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        if imported and imported != 'None':
            return imported
    except Exception:
        pass
    return str(slot.material_slot_name)


for label in ASSETS:
    name = 'SM_Tavern'+label
    path = DEST+'/'+name
    previous = ue.load_asset(path) if editor.does_asset_exist(path) else None
    donor = previous
    if service_only and not donor:
        donor = ue.load_asset(DEST+'/SM_TavernCounter')
        if not donor:
            raise RuntimeError('Missing source serving counter')
    previous_slots = {slot_key(s):s.material_interface for s in donor.static_materials} if donor else {}
    if previous and not isinstance(previous,ue.StaticMesh):
        raise RuntimeError('Existing furniture package is not a StaticMesh: '+path)
    task = ue.AssetImportTask()
    task.filename = str(SOURCE / 'Exports' / (name+'.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = previous is not None
    task.replace_existing_settings = False
    opts = ue.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = False
    opts.import_textures = False
    data = opts.static_mesh_import_data
    data.combine_meshes = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True
    data.generate_lightmap_u_vs = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.factory = ue.FbxFactory()
    task.options = opts
    tools.import_asset_tasks([task])
    mesh = ue.load_asset(path)
    if not mesh or not task.imported_object_paths:
        raise RuntimeError('Import failed for '+path+' '+str(task.imported_object_paths))
    for index,slot in enumerate(mesh.static_materials):
        key = slot_key(slot)
        if key in previous_slots:
            material=previous_slots[key]
        elif key in ('OiledOak','Rot') and 'Oak' in previous_slots and previous_slots['Oak'] != MATERIALS['Oak']:
            material=previous_slots['Oak']
        else:
            material=MATERIALS[key]
        mesh.set_material(index,material)
    body = mesh.get_editor_property('body_setup')
    if service_only and not previous:
        body.set_editor_property('collision_trace_flag',donor.get_editor_property('body_setup').get_editor_property('collision_trace_flag'))
        mesh.set_editor_property('nanite_settings',donor.get_editor_property('nanite_settings'))
    elif not previous:
        body.set_editor_property('collision_trace_flag',ue.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    slots = list(mesh.static_materials)
    used = {slot_key(slots[subsystem.get_lod_material_slot(mesh,0,i)]) for i in range(mesh.get_num_sections(0))}
    required = 'Rot' if label.startswith('Broken') else ('OiledOak' if label in ('Table','Stool','Counter','Counter_Service') else 'Oak')
    if required not in used:
        raise RuntimeError('Missing imported section '+required+' on '+name+' '+str(used))
    if not editor.save_loaded_asset(mesh,False):
        raise RuntimeError('Failed to save '+path)
    paths.append(path)
    bounds = mesh.get_bounding_box()
    report[name] = {
        'bounds_cm':[[p.x,p.y,p.z] for p in (bounds.min,bounds.max)],
        'sections':sorted(used), 'simple_convex_hulls':subsystem.get_convex_collision_count(mesh),
        'slots':{slot_key(s):s.material_interface.get_path_name() if s.material_interface else None for s in slots},
    }
    ue.log('TAVERN_FURNITURE_SAVED '+path)
(host/'mesh-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(host/'saved.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
