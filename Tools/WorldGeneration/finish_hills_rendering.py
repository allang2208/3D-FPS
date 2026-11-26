"""Finish the local hills foliage mip settings and inventory the authored surface graphs."""
import json
import runpy
from pathlib import Path

import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
task = root / 'SourceAssets/HillsEcologyUpgrade20261114'
backup = runpy.run_path(str(root / 'Tools/WorldGeneration/temperate_render_budget.py'))['backup']
base = '/Game/WorldGeneration/TemperateHills'
forest = base + '/ForestSpecies20261110'
lib = u.MaterialEditingLibrary
assets = u.EditorAssetLibrary
dirty = {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report = {'alpha_mips': [], 'nanite_parts': [], 'surfaces': {}, 'runtime_capture': False}
changes = []
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()


def asset(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing ' + path)
    return obj


def save_change(obj, update):
    changes.append((obj, update))


def publish_changes():
    if changes and not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        report['pending_saves'] = [obj.get_path_name() for obj, _ in changes]
        (task / 'render-finish-pending.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise RuntimeError('HILLS_WAIT_FOR_PIE_EXIT')
    for obj, update in changes:
        save_one(obj, update)


def save_one(obj, update):
    if obj.get_path_name().split('.')[0] in dirty:
        raise RuntimeError('Target has unsaved edits: ' + obj.get_path_name())
    backup(obj)
    update()
    if not assets.save_loaded_asset(obj, False):
        raise RuntimeError('Save failed: ' + obj.get_path_name())


def parent_and_clip(mat):
    clip = None
    blend = None
    while isinstance(mat, u.MaterialInstanceConstant):
        overrides = mat.get_editor_property('base_property_overrides')
        if clip is None and overrides.get_editor_property('override_opacity_mask_clip_value'):
            clip = overrides.get_editor_property('opacity_mask_clip_value')
        if blend is None and overrides.get_editor_property('override_blend_mode'):
            blend = overrides.get_editor_property('blend_mode')
        mat = mat.get_editor_property('parent')
    return (mat, float(mat.get_editor_property('opacity_mask_clip_value') if clip is None else clip),
            mat.get_editor_property('blend_mode') if blend is None else blend)


def preserve_mips(texture, mat, opacity_atlas=False):
    parent, clip, mode = parent_and_clip(mat)
    threshold = texture.get_editor_property('alpha_coverage_thresholds')
    mip_enabled = texture.get_editor_property('do_scale_mips_for_alpha_coverage')
    # HasAlphaChannel describes the GPU format and is unavailable under NullRHI.
    # The native solid leaf meshes use dithered coverage independently of their color maps.
    info = dict(texture=texture.get_path_name(), parent=parent.get_name(), clip=clip,
                blend=str(mode), opacity_atlas=opacity_atlas, alpha_mip_enabled=mip_enabled,
                mip_alpha_threshold=threshold.w)
    if mode != u.BlendMode.BLEND_MASKED or not opacity_atlas:
        report['alpha_mips'].append(dict(info, changed=False, action='preserve original geometry or alpha-free atlas'))
        return
    already = mip_enabled and abs(threshold.w - clip) < .0001 and not texture.get_editor_property('compression_no_alpha')
    def apply():
        texture.set_editor_property('alpha_coverage_thresholds', u.Vector4(threshold.x, threshold.y, threshold.z, clip))
        texture.set_editor_property('do_scale_mips_for_alpha_coverage', True)
        texture.set_editor_property('compression_no_alpha', False)
    if not already:
        save_change(texture, apply)
    info.update(alpha_mip_enabled=True, mip_alpha_threshold=clip)
    report['alpha_mips'].append(dict(info, changed=not already, action='preserve masked mip coverage'))


def surface(path):
    mat = asset(path)
    props = ('FRONT_MATERIAL', 'MATERIAL_ATTRIBUTES', 'BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'OPACITY_MASK')
    roots = {key: lib.get_material_property_input_node(mat, getattr(u.MaterialProperty, 'MP_' + key))
             for key in props}
    expressions = list(lib.get_material_expressions(mat))
    functions = set()
    # Include function graphs so that operators behind a material function are listed as well.
    nodes = []
    while expressions:
        node = expressions.pop()
        nodes.append(node)
        if not isinstance(node, u.MaterialExpressionMaterialFunctionCall):
            continue
        func = node.get_editor_property('material_function')
        while isinstance(func, u.MaterialFunctionInstance):
            func = func.get_editor_property('parent')
        if isinstance(func, u.MaterialFunction) and func not in functions:
            functions.add(func)
            expressions.extend(lib.get_material_function_expressions(func))
    substrate = sorted({node.get_class().get_name() for node in nodes
                        if any(key in node.get_class().get_name() for key in ('Substrate', 'Strata'))})
    report['surfaces'][path] = dict(inputs={key: value.get_class().get_name() for key, value in roots.items() if value},
                                   substrate_node_classes=substrate, nested_functions=len(functions))


def donor(path):
    mesh = asset(path)
    settings = mesh.get_editor_property('nanite_settings')
    shape = settings.get_editor_property('shape_preservation')
    slots = [slot.get_editor_property('material_interface') for slot in mesh.get_editor_property('static_materials')]
    leaf_only = bool(slots) and all(mat and 'Foliage' in mat.get_name() for mat in slots)
    enabled = settings.get_editor_property('enabled')
    change = enabled and leaf_only and shape == u.NaniteShapePreservation.NONE
    if change:
        def apply():
            settings.set_editor_property('shape_preservation', u.NaniteShapePreservation.PRESERVE_AREA)
            mesh.set_editor_property('nanite_settings', settings)
        save_change(mesh, apply)
    report['nanite_parts'].append(dict(mesh=mesh.get_name(), enabled=enabled, materials=[m.get_name() if m else None for m in slots],
                                      before=str(shape), after=str(u.NaniteShapePreservation.PRESERVE_AREA if change else shape)))


for name in ('European_Beech_Foliage_01', 'Common_Hazel_Foliage_01', 'Bracken_Fern_01'):
    tex = asset(forest + '/Textures/T_' + name + '_CA')
    mat = asset(forest + '/Materials/MI_' + name)
    bindings = [lib.get_material_instance_texture_parameter_value(mat, key) for key in lib.get_texture_parameter_names(mat)]
    if tex not in bindings:
        raise RuntimeError('Leaf atlas is not bound on ' + mat.get_path_name())
    preserve_mips(tex, mat)
preserve_mips(asset(base + '/WetForest/Textures/T_WildTuft_ColorOpacity'), asset(base + '/WetForest/ScannedGrass/M_SoftWildGrass'), True)
for file in sorted((root / 'Content/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes').glob('SM_Part_*.uasset')):
    donor(forest + '/Meshes/' + file.stem)
for path in [base + '/M_TemperateGround', base + '/PebbleShore/M_PebbleShoreGround',
             forest + '/Materials/M_ForestPCG', base + '/WetForest/ScannedGrass/M_SoftWildGrass']:
    surface(path)
for group in ('FacilitySurfaceUpgrade20261108', 'FacilityRoomFinish20261108'):
    for file in sorted((root / 'Content/Dungeons' / group / 'Materials').glob('M_*.uasset')):
        surface('/Game/Dungeons/' + group + '/Materials/' + file.stem)
publish_changes()
(task / 'render-finish-saved.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HILLS_RENDER_FINISH', len(report['alpha_mips']), len(report['nanite_parts']), len(report['surfaces']))
