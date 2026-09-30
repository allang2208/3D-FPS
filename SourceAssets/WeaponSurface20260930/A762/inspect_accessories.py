"""Read-only: material slots of the A762 accessories (item 2). Run through ../run_ue.ps1.

Writes A762/Bake/accessory_materials.json: per mesh, per slot the material, its base
material, blend mode, two-sided flag, the textures it uses (with compression and sRGB, to
tell normal / colour / mask maps apart) and scalar/vector parameters. UV layout facts come
from the ACC_* geometry dumps.
"""
import json
from pathlib import Path
import unreal as u

HERE = Path(u.Paths.project_dir()).resolve() / 'SourceAssets' / 'WeaponSurface20260930' / 'A762'
ROOT = '/Game/Weapons/A762/Accessories05/Meshes'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
SKIP = {'SM_A762_RearSight', 'SM_A762_FrontSight'}


def base_of(m):
    chain = []
    while isinstance(m, u.MaterialInstance):
        chain.append(m.get_path_name())
        m = m.get_editor_property('parent')
    if m:
        chain.append(m.get_path_name())
    return chain


def describe(mat):
    if mat is None:
        return None
    chain = base_of(mat)
    base = u.load_asset(chain[-1]) if chain else None
    info = {'path': mat.get_path_name(), 'class': mat.get_class().get_name(), 'chain': chain,
            'blend': str(base.get_editor_property('blend_mode')) if base else None,
            'two_sided': bool(base.get_editor_property('two_sided')) if base else None,
            'textures': [], 'scalars': {}, 'vectors': {}}
    used = list(L.get_used_textures(base) or []) if isinstance(base, u.Material) else []
    if isinstance(mat, u.MaterialInstance):
        used += [p.parameter_value for p in mat.get_editor_property('texture_parameter_values') if p.parameter_value]
    for t in {t.get_path_name(): t for t in used if isinstance(t, u.Texture)}.values():
        info['textures'].append({'path': t.get_path_name(), 'srgb': bool(t.get_editor_property('srgb')),
                                 'compression': str(t.get_editor_property('compression_settings'))})
    if isinstance(mat, u.MaterialInstance):
        for p in mat.get_editor_property('scalar_parameter_values'):
            info['scalars'][str(p.parameter_info.name)] = p.parameter_value
        for p in mat.get_editor_property('vector_parameter_values'):
            c = p.parameter_value
            info['vectors'][str(p.parameter_info.name)] = [c.r, c.g, c.b]
    else:
        for name in L.get_scalar_parameter_names(mat) or []:
            info['scalars'][str(name)] = L.get_material_default_scalar_parameter_value(mat, name)
        for name in L.get_vector_parameter_names(mat) or []:
            c = L.get_material_default_vector_parameter_value(mat, name)
            info['vectors'][str(name)] = [c.r, c.g, c.b]
    return info


out = {}
for path in sorted(E.list_assets(ROOT, recursive=False, include_folder=False)):
    mesh = u.load_asset(path)
    if not isinstance(mesh, u.StaticMesh) or mesh.get_name() in SKIP:
        continue
    slots = []
    for s in mesh.get_editor_property('static_materials'):
        slots.append({'slot': str(s.material_slot_name), 'material': describe(s.material_interface)})
    out[mesh.get_name()] = {'path': mesh.get_path_name(), 'slots': slots}
(HERE / 'Bake' / 'accessory_materials.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('A762_ACCESSORIES_INSPECTED', len(out), sum(len(v['slots']) for v in out.values()), flush=True)
