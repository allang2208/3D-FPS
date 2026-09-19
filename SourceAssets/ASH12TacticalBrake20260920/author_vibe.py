"""Build the reference-inspired ASH game attachment in the current UE editor.

Centimetres; +X forward, +Z up; rear mounting plane at X=0. Source is the
user's screenshot. Hidden faces are an original symmetric reconstruction.
No level actors, PIE, screenshots or acceptance renders are created.
"""
import json
import math
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
D = '/Game/Weapons/ASH12/TacticalBrake20260920'
NAME = 'SM_ASH12_TacticalBrake'
S = u.ModelingService
E = u.EditorAssetLibrary
handles = []
receipt = {'asset': D+'/'+NAME, 'axis': '+X forward / +Z up',
           'pivot': 'rear mounting plane X=0', 'length_cm': 8.4,
           'reference': 'Reference/user_brake.png', 'tested': False,
           'workflow': 'Vibe3D in-editor geometry, existing ASH black metal',
           'operations': []}


def ok(result):
    if not result.success:
        raise RuntimeError(str(result.message))
    receipt['operations'].append(str(result.message))
    return result


def mesh():
    handle = ok(S.create_mesh()).handle
    handles.append(handle)
    return handle


def transform(location=(0, 0, 0), rotation=None, scale=(1, 1, 1)):
    return u.Transform(location=u.Vector(*location),
                       rotation=(rotation or u.Quat(0, 0, 0, 1)).rotator(),
                       scale=u.Vector(*scale))


IDENTITY = transform()
# Rotate the primitive's +Z axis onto the attachment's +X barrel axis.
AXIAL = transform(rotation=u.Quat(0, math.sqrt(.5), 0, math.sqrt(.5)))


def revolve(handle, axial_profile, steps=64, material=0):
    points = [u.Vector2D(radius, x) for x, radius in axial_profile]
    ok(S.append_revolve_polygon(handle, AXIAL, points, radius=0.,
                                steps=steps, revolve_degrees=360., material_id=material))


def chamfered_rectangle(x0, x1, half_height, corner):
    return [u.Vector2D(x0+corner, -half_height), u.Vector2D(x1-corner, -half_height),
            u.Vector2D(x1, -half_height+corner), u.Vector2D(x1, half_height-corner),
            u.Vector2D(x1-corner, half_height), u.Vector2D(x0+corner, half_height),
            u.Vector2D(x0, half_height-corner), u.Vector2D(x0, -half_height+corner)]


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()], False):
        raise RuntimeError('Save failed: '+asset.get_path_name())


def export_fbx(asset):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(O/(NAME+'.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.StaticMeshExporterFBX()
    task.options = u.FbxExportOption()
    task.options.collision = False
    task.options.level_of_detail = False
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('FBX export failed')
    return task.filename


def main():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Stop PIE before creating and building this attachment.')
    # Reuse the actual ASH finish, including its normal/ORM textures. The
    # existing private weather library already maps these two materials.
    material_paths = [
        '/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat',
        '/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_OpticShoe_Coat']
    materials = [u.load_asset(path) for path in material_paths]
    if not all(materials):
        raise RuntimeError('Required ASH black metal materials are missing')

    # Octagonal outer cage, chamfered nose, continuous open axial aperture.
    # The two perpendicular window cuts leave four substantial corner ribs.
    body = mesh()
    revolve(body, [(1.95, 2.10), (2.30, 2.65), (7.82, 2.65),
                   (8.40, 2.16), (8.40, .91), (8.23, .77),
                   (7.70, .77), (7.43, 1.97), (2.30, 1.97), (1.95, 1.43)],
            steps=8)
    side = mesh()
    side_transform = transform((0, -3.25, 0), u.Quat(-math.sqrt(.5), 0, 0, math.sqrt(.5)))
    ok(S.append_extrude_polygon(side, side_transform,
        chamfered_rectangle(3.02, 7.45, 1.30, .43), height=6.5))
    ok(S.boolean(body, side, 'Subtract', IDENTITY, fill_holes=False, simplify_output=True))
    top = mesh()
    ok(S.append_extrude_polygon(top, transform((0, 0, -3.25)),
        chamfered_rectangle(3.28, 7.25, 1.12, .37), height=6.5))
    ok(S.boolean(body, top, 'Subtract', IDENTITY, fill_holes=False, simplify_output=True))
    ok(S.compute_polygroups(body, 'Angle', 25., 1))
    ok(S.bevel_polygroups(body, distance=.065, subdivisions=2, round_weight=1.))

    # ASH interface: same rear seating diameter as its existing dedicated
    # attachment. Narrow grooves are modeled as gaps in the lathed profile.
    collar = mesh()
    revolve(collar, [(0., 1.10), (0., 1.50), (.17, 1.70), (.44, 1.70),
        (.49, 1.61), (.57, 1.61), (.63, 1.70), (.97, 1.70),
        (1.03, 1.85), (1.14, 2.14), (1.28, 2.21), (1.43, 2.21),
        (1.48, 2.10), (1.56, 2.10), (1.62, 2.24), (1.78, 2.24),
        (1.86, 2.10), (2.05, 2.10), (2.19, 1.96), (2.19, 1.10)],
        material=1)
    ok(S.append_mesh(body, collar, IDENTITY))
    # Complete UV sets: UV0 supports tangents/water beads. UV3 is the existing
    # ASH coat's physical 4 cm tiling; UV1/2 remain valid independent layers.
    ok(S.set_num_uv_layers(body, 4))
    ok(S.auto_uv(body, 'XAtlas', 0))
    projector = transform(scale=(4, 4, 4))
    for layer in (1, 2, 3):
        ok(S.project_uv(body, 'Box', projector, layer, ''))
    ok(S.recompute_normals(body, 38.))
    ok(S.set_vertex_color(body, '', u.LinearColor(0, 0, 0, 1)))
    result = ok(S.save_mesh_to_static_mesh(body, D+'/'+NAME,
        replace_existing=True, enable_collision=False, enable_nanite=False, save_asset=False))
    asset = u.load_asset(result.asset_path)
    slots = []
    for index, mat in enumerate(materials):
        slot = u.StaticMaterial()
        slot.material_interface = mat
        slot.material_slot_name = 'ASH_BrakeShell' if index == 0 else 'ASH_BrakeMount'
        slots.append(slot)
    asset.set_editor_property('static_materials', slots)
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(asset)
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    settings = editor.get_lod_build_settings(asset, 0)
    settings.recompute_normals = False
    settings.recompute_tangents = True
    settings.use_mikk_t_space = True
    settings.use_high_precision_tangent_basis = True
    settings.use_full_precision_u_vs = True
    settings.generate_lightmap_u_vs = False
    editor.set_lod_build_settings(asset, 0, settings)
    E.set_metadata_tag(asset, 'ASHExclusiveOption', 'ash12_tactical_brake')
    E.set_metadata_tag(asset, 'AuthoringSource', str(O/'author_vibe.py'))
    E.set_metadata_tag(asset, 'MaterialReference', 'ASH12 existing black metal, no orange tint')
    E.set_metadata_tag(asset, 'MountFrame', '+X forward; X=0 rear contact; ASH MuzzleBackOffset 6.79cm')
    save(asset)
    receipt.update({'fbx': export_fbx(asset), 'triangles': result.triangle_count,
                    'vertices': result.vertex_count, 'materials': material_paths,
                    'weather': 'existing ASH private dry/wet mappings reused',
                    'saved': True, 'exclusive_weapon': 'ue_ash12',
                    'option_id': 'ash12_tactical_brake'})
    (O/'authoring.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('ASH12_TACTICAL_BRAKE_CREATED '+json.dumps(receipt, ensure_ascii=False))


try:
    main()
finally:
    for owned_handle in reversed(handles):
        S.release_mesh(owned_handle)
