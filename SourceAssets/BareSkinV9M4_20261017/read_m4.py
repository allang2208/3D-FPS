"""Read-only commandlet: M4 viewmodel reference skeleton, skin material settings and sampled poses.

Writes Snapshot/m4_read.json. Nothing is saved or dirtied.
"""
import json
from pathlib import Path
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017'); OUT = R / 'Snapshot'; OUT.mkdir(parents=True, exist_ok=True)
MESH = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416'
CLIPS = ['/Game/Weapons/M4ContactImpactFinal/A_AKM_idle', '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim',
         '/Game/Weapons/M4ContactImpactFinal/A_AKM_fire', '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim_fire',
         '/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload', '/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty',
         '/Game/Weapons/M4WrapGripFinal/A_M4_HK416_equip_charge',
         '/Game/Weapons/M4VerticalGripVRENatural/Vertical/A_M4_Vertical_idle', '/Game/Weapons/M4VerticalGripVRENatural/Vertical/A_M4_Vertical_reload',
         '/Game/Weapons/M4TacticalSprint20260915/Base/A_M4_TacticalSprint_Base_Enter',
         '/Game/Weapons/M4TacticalSprint20260915/Base/A_M4_TacticalSprint_Base_Loop',
         '/Game/Weapons/M4TacticalSprint20260915/Base/A_M4_TacticalSprint_Base_Exit',
         '/Game/Weapons/M4TacticalSprint20260915/Vertical/A_M4_TacticalSprint_Vertical_Loop',
         '/Game/Weapons/M4TacticalSprint20260915/Drum/A_M4_TacticalSprint_Drum_Loop']
L = u.MaterialEditingLibrary; S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)


def xyz(v): return [v.x, v.y, v.z]


def xform(t):
    q = t.rotation
    return dict(t=xyz(t.translation), q=[q.x, q.y, q.z, q.w], s=xyz(t.scale3d))


mesh = u.load_asset(MESH)
out = dict(mesh=MESH, lods=S.get_lod_count(mesh), morph_targets=[m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])])
lod = []
for i in range(out['lods']):
    b = S.get_lod_build_settings(mesh, i)
    lod.append({k: str(b.get_editor_property(k)) for k in ('use_full_precision_u_vs', 'recompute_normals', 'recompute_tangents', 'use_mikk_t_space',
                                                           'compute_weighted_normals', 'use_high_precision_tangent_basis', 'morph_threshold_position')})
out['lod_build'] = lod
options = u.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh = mesh; options.evaluation_type = u.AnimDataEvalType.COMPRESSED
skeleton = mesh.get_editor_property('skeleton')
ref = u.AnimPoseExtensions.get_reference_pose(skeleton)
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
out['bones'] = names
out['ref_component'] = {n: xform(u.AnimPoseExtensions.get_ref_bone_pose(ref, n, u.AnimPoseSpaces.WORLD)) for n in names}
slots = []
for s in mesh.materials:
    mi = s.material_interface; row = dict(slot=str(s.material_slot_name), path=mi.get_path_name() if mi else '')
    base = mi
    while isinstance(base, u.MaterialInstance): base = base.get_editor_property('parent')
    row['base'] = base.get_path_name() if base else ''
    if isinstance(mi, u.MaterialInstance):
        row['scalars'] = {str(n): L.get_material_instance_scalar_parameter_value(mi, n) for n in L.get_scalar_parameter_names(mi)}
        row['textures'] = {str(n): (L.get_material_instance_texture_parameter_value(mi, n).get_path_name() if L.get_material_instance_texture_parameter_value(mi, n) else '')
                           for n in L.get_texture_parameter_names(mi)}
    if base and isinstance(base, u.Material):
        prof = base.get_editor_property('subsurface_profile')
        if prof:
            st = prof.get_editor_property('settings'); props = {}
            for k in ('mean_free_path_distance', 'world_unit_scale', 'surface_albedo', 'mean_free_path_color', 'tint', 'roughness0', 'roughness1', 'lobe_mix',
                      'enable_burley', 'transmission_tint_color', 'extinction_scale', 'normal_scale', 'scattering_distribution', 'ior', 'boundary_color_bleed'):
                try: props[k] = str(st.get_editor_property(k))
                except Exception as e: props[k] = 'n/a'
            row['subsurface_profile'] = dict(path=prof.get_path_name(), settings=props)
        row['shading_model'] = str(base.get_editor_property('shading_model'))
    slots.append(row)
out['slots'] = slots
clips = {}
for path in CLIPS:
    seq = u.load_asset(path)
    if not seq: clips[path] = dict(missing=True); continue
    length = seq.get_editor_property('sequence_length') if hasattr(seq, 'sequence_length') else u.AnimationLibrary.get_sequence_length(seq)
    n = max(2, int(round(length * 30)) + 1); frames = []
    for i in range(n):
        t = min(length, i / 30.0)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(seq, t, options)
        frames.append([xform(u.AnimPoseExtensions.get_bone_pose(pose, b, u.AnimPoseSpaces.WORLD)) for b in names])
    clips[path] = dict(length=length, fps=30, frames=frames)
    print('M4V9_READ_CLIP', path, length, n, flush=True)
out['clips'] = clips
(OUT / 'm4_read.json').write_text(json.dumps(out))
print('M4V9_READ_COMPLETE', len(names), 'bones', len(clips), 'clips', flush=True)
