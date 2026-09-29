"""Save the new mail-shirt assets, then publish only its equipment recipe."""

if __name__ == "__main__":
    raise RuntimeError("Historical garment publication retired. Use garment_pipeline.py candidates and gate; do not overwrite current rig-specific repairs.")

import hashlib
import json
import shutil
import sys
from pathlib import Path

import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P/'SourceAssets/ChainmailShirt20260928'
DEST = '/Game/Characters/ModularOutfit20260924/ChainmailShirt20260928'
GREY = '/Game/Characters/ModularOutfit20260924/SteelGauntletV1/FullMetal20260928/M_GreyMetalLiner'
ITEM = 'ue_chainmail_shirt'
ICON = 'Icons/ChainmailShirt20260928/ue_chainmail_shirt.png'
sys.path.insert(0, str(P/'Tools/ModularOutfit'))
from import_tailored_fingerless_candidate import load, save

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def material():
    folder = DEST+'/Materials'
    E.make_directory(folder)
    instance = u.load_asset(folder+'/MI_ChainmailShirt_GreySteel')
    if not instance:
        instance = A.create_asset('MI_ChainmailShirt_GreySteel', folder,
            u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    # Inherit the user's accepted grey surface; never rebuild the shared parent.
    u.MaterialEditingLibrary.set_material_instance_parent(instance, load(GREY))
    E.set_metadata_tag(instance, 'EquipmentDefinition', ITEM)
    save(instance)
    return instance


def build_mesh(data, mat):
    name = data['profile']
    source = load(data['binding_source'])
    native, status = G.copy_mesh_from_skeletal_mesh(source, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read native mail binding: '+name)
    _, bones = B.get_all_bones_info(native)
    bone_ids = {str(b.name): b.index for b in bones}
    vertices, normals, uv0, weights, triangles = [], [], [], [], []
    lookup = {}
    for fi, face in enumerate(data['triangles']):
        row = []
        for corner, vi in enumerate(face):
            uv = data['uv'][fi][corner]
            normal = data['normals'][fi][corner]
            key = (vi, *[round(v, 7) for v in (*uv, *normal)])
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*normal))
                uv0.append(u.Vector2D(*uv))
                weights.append(data['weights'][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,
        u.GeometryScriptSimpleMeshBuffers(vertices=vertices, normals=normals, uv0=uv0, triangles=triangles), 0, True)
    _, assembled, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    if len(u.GeometryScript_List.convert_triangle_list_to_array(assembled)) != len(triangles):
        raise RuntimeError('Native shirt assembly rejected triangles: '+name)
    B.copy_bones_from_mesh(native, dm)
    B.mesh_create_bone_weights(dm)
    for vi, bindings in enumerate(weights):
        B.set_vertex_bone_weights(dm, vi, [u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w)
                                        for n, w in bindings.items()])
    # Separate coincident caps are intentional in the fitted source. No welding.
    folder = DEST+'/'+name
    mesh_name = 'SK_'+name+'_ChainmailShirt'
    mesh = u.load_asset(folder+'/'+mesh_name)
    if not mesh:
        mesh = A.duplicate_asset(mesh_name, folder, source)
    options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[mat], new_material_slot_names=['GreySteelMail'],
        enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot build native mail mesh: '+name)
    mesh.set_editor_property('physics_asset', None)
    build = S.get_lod_build_settings(mesh, 0)
    build.set_editor_property('use_full_precision_u_vs', True)
    S.set_lod_build_settings(mesh, 0, build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):
        raise RuntimeError('Cannot configure mail LODs: '+name)
    if not S.regenerate_lod(mesh, 3, True, False):
        raise RuntimeError('Cannot generate mail LODs: '+name)
    E.set_metadata_tag(mesh, 'EquipmentDefinition', ITEM)
    E.set_metadata_tag(mesh, 'NativeSource', data['binding_source'])
    E.set_metadata_tag(mesh, 'SourceContract', data['contract'])
    save(mesh)
    return mesh


def pickup(mat):
    folder = DEST+'/Pickups'
    name = 'SM_ChainmailShirt_Pickup'
    E.make_directory(folder)
    task = u.AssetImportTask()
    task.filename = str(R/(name+'.fbx'))
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    opts = u.FbxImportUI()
    opts.import_as_skeletal = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opts.automated_import_should_detect_type = False
    opts.import_materials = False
    opts.import_textures = False
    opts.static_mesh_import_data.combine_meshes = True
    opts.static_mesh_import_data.auto_generate_collision = True
    task.options = opts
    A.import_asset_tasks([task])
    mesh = load(folder+'/'+name)
    for i in range(len(mesh.get_editor_property('static_materials'))):
        mesh.set_material(i, mat)
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    options = u.StaticMeshReductionOptions()
    options.auto_compute_lod_screen_size = False
    options.reduction_settings = [u.StaticMeshReductionSettings(percent_triangles=percent, screen_size=screen)
                                  for percent, screen in ((1., 1.), (.5, .18), (.25, .075))]
    subsystem.set_lods(mesh, options)
    E.set_metadata_tag(mesh, 'EquipmentDefinition', ITEM)
    save(mesh)
    return mesh


def publish(profiles, mat, world_mesh):
    config_path = P/'Content/ColdSteelData/modular_outfits.json'
    item_path = P/'Content/ColdSteelData/items.json'
    config, items = read(config_path), read(item_path)
    before = R/'before-publication.json'
    if not before.exists():
        write(before, dict(item=items.get(ITEM), recipe=config['items'].get(ITEM)))
    recipe = dict(slot=7, part='shirt', material=mat.get_path_name(),
        appearance_family='ChainmailShirt20260928',
        rig_meshes={name: value['mesh'] for name, value in profiles.items()})
    # Retain the current shirt category, size and inventory/save contracts.
    item = dict(items.get(ITEM, items['ue_field_sweater']))
    item.update(id=ITEM, name='灰钢锁子甲', icon_fallback='甲', ue_icon=ICON,
        desc='灰钢细密环纹覆盖双臂与躯干，沿用贴身长袖版型和收口袖缘，可与钢甲护手独立搭配。',
        world_mesh=world_mesh.get_path_name(), world_material=mat.get_path_name())
    icon = P/'Content/ColdSteelData'/ICON
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(R/(ITEM+'.png'), icon)
    config['items'][ITEM] = recipe
    items[ITEM] = item
    write(config_path, config)
    write(item_path, items)
    write(R/'published.json', dict(item=ITEM, item_definition=item, recipe=recipe,
        profiles=profiles, material=mat.get_path_name(), pickup=world_mesh.get_path_name(),
        icon=str(icon), source_material=GREY, new_animations=0, runtime_tested=False,
        refresh='next game session; data and content only; no native build required'))
    print('CHAINMAIL_SHIRT_PUBLISHED', ITEM, len(profiles), flush=True)


def main():
    current = read(P/'Content/ColdSteelData/modular_outfits.json')['items'].get(ITEM, {})
    if current.get('appearance_family') in ('ChainmailCloth20260929','ChainmailSharedSway20260929'):
        raise RuntimeError('Use import_chainmail_shared_sway.py; the legacy importer would remove current cuff motion.')
    if current.get('appearance_family') in ('ChainmailRelief20260929', 'ChainmailInterlace20260929'):
        entry = 'import_chainmail_interlace.py' if current.get('appearance_family') == 'ChainmailInterlace20260929' else 'import_chainmail_relief.py'
        raise RuntimeError('The active shirt uses '+current['appearance_family']+'. Use '+entry+'; the legacy importer would replace its current surface.')
    subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():
        raise RuntimeError('Finish the current PIE session before importing the mail shirt; authoring APIs reject play mode')
    read(R/'artwork.json')
    mat = material()
    profiles = {}
    for row in read(R/'manifest.json'):
        name = row['profile']
        raw = Path(row['authored']).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        record = R/'Saved'/(name+'.json')
        old = read(record) if record.exists() else None
        if old and old.get('authored_sha256') == sha and E.does_asset_exist(old['mesh']):
            profiles[name] = old
            continue
        print('CHAINMAIL_IMPORT_BEGIN', name, flush=True)
        data = json.loads(raw)
        mesh = build_mesh(data, mat)
        receipt = dict(mesh=mesh.get_path_name(), authored_sha256=sha,
                       skeleton=data['skeleton'], source=data['binding_source'],
                       lod0_triangles=len(data['triangles']), lods=3, new_animations=0)
        write(record, receipt)
        profiles[name] = receipt
        print('CHAINMAIL_MESH_SAVED', name, flush=True)
    world_mesh = pickup(mat)
    publish(profiles, mat, world_mesh)


if __name__ == '__main__':
    main()
