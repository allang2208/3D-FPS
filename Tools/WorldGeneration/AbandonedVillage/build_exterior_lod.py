"""Bake distant village exteriors from the placed modules and their current material overrides."""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import unreal as u

VILLAGE = "/Game/WorldGeneration/TemperateHills/AbandonedVillage"
OUTPUT = VILLAGE + "/ExteriorLOD"
SHOP = re.compile(r"Village_(02_Tavern|05_Windmill|06_Bakery|09_Gunshop|(Blacksmith|Carpenter|Herbalist)_(Common|Repaired|Ruined))$")
FIXED = re.compile(r"Roof|Chimney|OldWall|WallCorner|WindowWall|Wall4x4|ArcadeFrame|Gable|StonePier|StoneJamb|InnFacade|InnTimberFrame", re.I)
EXCLUDED = re.compile(r"Glass|Shutter|Rotor|Blade|DoorLeaf|Animated|Flame|GlassPane", re.I)
ED = u.EditorAssetLibrary
ASSET = u.GeometryScript_AssetUtils
EDIT = u.GeometryScript_MeshEdits
MATS = u.GeometryScript_Materials


def placement(transform):
    t, q, s = transform.translation, transform.rotation, transform.scale3d
    return [round(v, 6) for v in (t.x,t.y,t.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z)]


def source_parts(actor):
    groups = defaultdict(list)
    anchor = actor.get_actor_transform()
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = comp.static_mesh
        if not mesh or not FIXED.search(mesh.get_name()) or EXCLUDED.search(mesh.get_name()):
            continue
        instanced = isinstance(comp, u.InstancedStaticMeshComponent)
        if instanced and comp.get_editor_property("num_custom_data_floats"):
            continue
        tags = sorted(str(t) for t in comp.component_tags)
        if "VillageTavern.NativeRoomWall" in tags:
            continue
        poses = ([comp.get_instance_transform(i, world_space=True) for i in range(comp.get_instance_count())]
                 if instanced else [comp.get_world_transform()])
        materials = [comp.get_material(i) for i in range(comp.get_num_materials())]
        if not poses or not materials or not all(materials):
            continue
        relative = [u.MathLibrary.make_relative_transform(t, anchor) for t in poses]
        groups[tuple(tags)].append((comp, mesh, materials, relative, instanced))
    return groups


def bake(actor, parts, name):
    dm, palette, metadata = u.DynamicMesh(), [], []
    source_tris = 0
    for comp, mesh, materials, poses, instanced in parts:
        lod = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=1)
        part, outcome = ASSET.copy_mesh_from_static_mesh_v2(mesh, u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(), lod, use_section_materials=False)
        if outcome != u.GeometryScriptOutcomePins.SUCCESS or part.get_triangle_count() == 0:
            part,outcome=ASSET.copy_mesh_from_static_mesh_v2(mesh,u.DynamicMesh(),
                u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(),use_section_materials=False)
        if outcome != u.GeometryScriptOutcomePins.SUCCESS or part.get_triangle_count() == 0:
            raise RuntimeError("Cannot read " + mesh.get_path_name())
        source_tris += part.get_triangle_count() * len(poses)
        if part.get_triangle_count() > 500:
            # Half a centimetre of world-space error is subpixel at the switch distance.
            max_scale = max(max(abs(t.scale3d.x), abs(t.scale3d.y), abs(t.scale3d.z)) for t in poses)
            options = u.GeometryScriptSimplifyMeshOptions(allow_seam_smoothing=False)
            u.GeometryScript_MeshSimplification.apply_simplify_to_tolerance(part, .5 / max(1., max_scale), options)
        for i in range(len(materials)):
            MATS.remap_material_i_ds(part, i, 1024 + i)
        for i, material in enumerate(materials):
            if material not in palette:
                palette.append(material)
            MATS.remap_material_i_ds(part, 1024 + i, palette.index(material))
        for transform in poses:
            EDIT.append_mesh(dm, part, transform)
        metadata.append(dict(component=comp.get_name(), mesh=mesh.get_path_name(),
            materials=[m.get_path_name() for m in materials], instanced=instanced,
            poses=[placement(t) for t in poses]))
    target = OUTPUT + "/" + name
    asset = (ED.load_asset(target) if ED.does_asset_exist(target)
             else ED.duplicate_asset("/Engine/BasicShapes/Cube", target))
    opts = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True, new_materials=palette,
        new_material_slot_names=[u.Name("Exterior_" + str(i)) for i in range(len(palette))],
        enable_recompute_normals=False, enable_recompute_tangents=True)
    settings = asset.get_editor_property("nanite_settings")
    settings.enabled = dm.get_triangle_count() > 5000
    opts.set_editor_property("apply_nanite_settings", True)
    opts.set_editor_property("new_nanite_settings", settings)
    _, outcome = ASSET.copy_mesh_to_static_mesh(dm, asset, opts, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS or not ED.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Could not save " + target)
    return dict(actor=actor.get_name(), label=actor.get_actor_label(), proxy=asset.get_path_name(), parts=metadata,
                donor_triangles=source_tris, proxy_triangles=dm.get_triangle_count())


def main():
    if not u.EditorLoadingAndSavingUtils.load_map(VILLAGE + "/L_AbandonedVillage"):
        raise RuntimeError("Village level unavailable")
    groups = []
    selected = os.environ.get("VILLAGE_EXTERIOR_LABEL")
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    for actor in sorted(actors, key=lambda item: item.get_name()):
        label = actor.get_actor_label()
        if not SHOP.fullmatch(label) or (selected and label != selected):
            continue
        for index, (_, parts) in enumerate(sorted(source_parts(actor).items())):
            if len(parts) < 2:
                continue
            suffix = "_Inn" if label == "Village_02_Tavern" and "VillageTavern.ThreeStoreyInn" in map(str,actor.tags) else ""
            if "VillageTavern.StoneCourt" in map(str,actor.tags):suffix="_StoneCourt"
            if "VillageTavern.HallRoadR3" in map(str,actor.tags):suffix="_HallRoadR3"
            if "VillageTavern.JoineryR4" in map(str,actor.tags):suffix="_JoineryR4"
            if "VillageTavern.NativeDiningWallsR5" in map(str,actor.tags):suffix="_NativeDiningWallsR5"
            groups.append(bake(actor, parts, f"SM_Exterior_{label}{suffix}_{index:02d}"))
    if not groups:
        raise RuntimeError("No village exteriors authored")
    path = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())) / "WorldGeneration/TemperateHills/FixedLayout/village-exterior-lod.json"
    if selected:
        other=[group for group in json.loads(path.read_text(encoding='utf8')) if group['label']!=selected]
        groups=other+groups
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(groups, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(pending, path)
    u.log("Village exterior proxy groups saved: " + str(len(groups)))


main()
