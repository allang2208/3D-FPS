"""Build an editable HK416 source from current native poses and authored tracks.

Preserves the original V7 arms, native bind, geometry, materials and weights.
This is source production only: no UE import, preview, rendering or tests.
"""
import gzip
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


OUT = Path(__file__).resolve().parent
INPUTS = OUT / "Inputs"
SOURCE = OUT.parent / "HK416Reworked20260930/HK416_Gameplay_Editable.blend"
DEST = OUT / "HK416_ReloadGrip_Editable.blend"
C = Matrix.Diagonal((100.0, -100.0, 100.0, 1.0))
CI = C.inverted()


def read_gzip(path):
    with gzip.open(path, "rt", encoding="utf8") as stream:
        return json.load(stream)


def transform(row):
    # Unreal rows are cm translation, XYZW quaternion and XYZ scale.
    q = Quaternion((row[6], row[3], row[4], row[5]))
    q.normalize()
    return Matrix.LocRotScale(Vector(row[:3]), q, Vector(row[7:10]))


index = json.loads((OUT / "inputs.json").read_text(encoding="utf8"))
bind = json.loads((INPUTS / "bind.json").read_text(encoding="utf8"))
authored = {}
for filename in ("standard_tracks.json.gz", "drum_tracks.json.gz"):
    authored.update(read_gzip(OUT / filename)["clips"])
names = bind["names"]
parents = bind["parents"]
native_index = {name: i for i, name in enumerate(names)}
native_rest = [transform(row) for row in bind["rest"]]
native_rest_inv = [m.inverted() for m in native_rest]

# Read all source input files before touching the Blender scene. The complete
# native poses retain the current release-paddle, bolt and recovery clocks.
complete = {}
for asset, spec in index["clips"].items():
    full = INPUTS / (spec["family"] + "__" + spec["kind"] + "__full.json.gz")
    full_data = read_gzip(full)
    if full_data["asset"] != asset or full_data["bones"] != names:
        raise RuntimeError("Mismatched full source: " + str(full))
    fix = authored[asset]
    if fix["source_sha256"] != spec["sha256"]:
        raise RuntimeError("Mismatched authored source: " + asset)
    count = len(full_data["times"])
    if count != spec["keys"] or any(len(rows) != count for rows in fix["tracks"].values()):
        raise RuntimeError("Mismatched authored key count: " + asset)
    complete[asset] = full_data

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects.get("SK_M4_Infima")
if rig is None:
    rig = next(o for o in scene.objects if o.type == "ARMATURE" and "WPN_root" in o.data.bones)
rig_world = rig.matrix_world.copy()
rig_world_inv = rig_world.inverted()
blender_rest = {b.name: rig_world @ b.matrix_local for b in rig.data.bones}
blender_rest_local_inv = {
    b.name: (b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).inverted()
    for b in rig.data.bones
}
bone_names = [name for name in names if name in blender_rest]
missing = [b.name for b in rig.data.bones if b.name not in native_index]
if missing:
    raise RuntimeError("Native source does not cover Blender bones: " + ", ".join(missing))
if rig.animation_data is None:
    rig.animation_data_create()
rig.animation_data.use_nla = False
scene.render.fps = 60
scene.render.fps_base = 1.0

report = {
    "source_blend": str(SOURCE),
    "editable_blend": str(DEST),
    "native_mesh": index["mesh"],
    "basis_conversion": "inv(C) @ native_pose_world @ inv(native_rest_world) @ C @ Blender_rest_world",
    "geometry_material_weights_rest_preserved": True,
    "fps": 60,
    "preview_rendered": False,
    "runtime_tested": False,
    "clips": {},
}
default_action = None
default_end = 126

for asset, spec in index["clips"].items():
    data = complete.pop(asset)
    times = data["times"]
    fixes = authored[asset]["tracks"]
    samples = {name: [] for name in bone_names}
    previous = {}
    # Cache the complete pose first, reconstruct its native locals, then apply
    # authored locals and run FK. No child ever reads a partially modified parent.
    for frame_index, raw_world in enumerate(data["world"]):
        world = [transform(row) for row in raw_world]
        local = [world[p].inverted() @ world[i] if p >= 0 else world[i].copy()
                 for i, p in enumerate(parents)]
        for name, rows in fixes.items():
            local[native_index[name]] = transform(rows[frame_index])
        for i, p in enumerate(parents):
            world[i] = world[p] @ local[i] if p >= 0 else local[i]
        converted = {
            name: rig_world_inv @ CI @ world[native_index[name]] @ native_rest_inv[native_index[name]] @ C @ blender_rest[name]
            for name in bone_names
        }
        for name in bone_names:
            parent = rig.data.bones[name].parent
            pose_local = converted[parent.name].inverted() @ converted[name] if parent else converted[name]
            basis = blender_rest_local_inv[name] @ pose_local
            location, rotation, scale = basis.decompose()
            if name in previous and rotation.dot(previous[name]) < 0.0:
                rotation.negate()
            previous[name] = rotation.copy()
            samples[name].append((tuple(location), tuple(rotation), tuple(scale)))

    action_name = "HK416_Grip20261001_" + spec["family"] + "_" + spec["kind"]
    action = bpy.data.actions.new(action_name)
    action.use_fake_user = True
    rig.animation_data.action = action
    # Key once to construct Blender 5.1 slots/channelbags; dense keys are bulk
    # written below rather than inserted one pose at a time.
    for name in bone_names:
        bone = rig.pose.bones[name]
        bone.rotation_mode = "QUATERNION"
        for prop in ("location", "rotation_quaternion", "scale"):
            bone.keyframe_insert(prop, frame=0.0)
    curves = {
        (curve.data_path, curve.array_index): curve
        for layer in action.layers
        for strip in layer.strips
        for bag in strip.channelbags
        for curve in bag.fcurves
    }
    for name, rows in samples.items():
        for prop, field, dimensions in (("location", 0, 3), ("rotation_quaternion", 1, 4), ("scale", 2, 3)):
            for axis in range(dimensions):
                curve = curves[(f'pose.bones["{name}"].{prop}', axis)]
                curve.keyframe_points.clear()
                curve.keyframe_points.add(len(rows))
                curve.keyframe_points.foreach_set(
                    "co", [value for i, row in enumerate(rows) for value in (times[i] * 60.0, row[field][axis])]
                )
                for key in curve.keyframe_points:
                    key.interpolation = "LINEAR"
                curve.update()
    end = int(round(times[-1] * 60.0))
    action.use_frame_range = True
    action.frame_start = 0.0
    action.frame_end = float(end)
    action["native_source_asset"] = asset
    action["native_source_sha256"] = spec["sha256"]
    action["authored_track_count"] = len(fixes)
    report["clips"][asset] = {
        "action": action.name,
        "family": spec["family"],
        "kind": spec["kind"],
        "source_sha256": spec["sha256"],
        "keys": len(times),
        "frames": [0, end],
        "seconds": times[-1],
        "bone_count": len(bone_names),
        "authored_tracks": list(fixes),
    }
    if spec["family"] == "base" and spec["kind"] == "reload":
        default_action = action
        default_end = end
    print("HK416_EDITABLE_ACTION", action.name, "keys", len(times), flush=True)

rig.animation_data.action = default_action
scene.frame_start = 0
scene.frame_end = default_end
scene.frame_set(76)
bpy.ops.object.select_all(action="DESELECT")
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
scene["HK416ReloadGripSource"] = str(OUT)
scene["HK416ReloadGripRuntimeTested"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
report["saved"] = True
report["default_action"] = default_action.name
report["default_frame"] = 76
(OUT / "editable_source.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
print("HK416_EDITABLE_SAVED", str(DEST), flush=True)
