"""Rebuild the registered V3 steel, native rune-sword finishes and whirlwind variants.

Run as an Unreal PythonScript commandlet on a host containing the native materials
and their dependencies. For old temporal packages, leave the nine temporal_sources
destinations out of the staging Content copy so they can be cloned from their
newly finished normal material. Already upgraded destinations can be reused.
The input scripts may reside in another project's SourceAssets.
"""
import json
import runpy
from pathlib import Path

import unreal as u

P = Path(__file__).resolve().parent
REGISTRY = json.loads((P / 'damascus-v3-surfaces.json').read_text(encoding='utf-8'))
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary


def load_material(package):
    material = u.load_asset(package)
    if not isinstance(material, u.Material):
        raise RuntimeError('Expected a native material at ' + package)
    return material


def save(material):
    errors = list(L.recompile_material(material) or [])
    if errors:
        raise RuntimeError(f'{material.get_path_name()}: {errors}')
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + material.get_path_name())


def rebuild():
    damascus = runpy.run_path(str(P / 'damascus_v3.py'))
    common = runpy.run_path(str(P / 'common_finish_graph.py'))
    restore_reference = runpy.run_path(str(P.parent / 'ZhanmadaoDamascus20261111' / 'temporal_finishes.py'))['restore']
    atlas = u.load_asset('/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101/T_MeteoricCrystalFieldV2')
    if not atlas:
        raise RuntimeError('Missing meteor crystal atlas')
    temporal = REGISTRY['temporal_sources']
    targets = set(REGISTRY['surfaces']) | set(REGISTRY['zhanmadao_temporal'])
    dirty = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_path_name() in targets]
    if dirty:
        raise RuntimeError(f'Targets with unsaved changes: {dirty}')
    for package in temporal:
        if E.does_asset_exist(package):
            material = load_material(package)
            if E.get_metadata_tag(material, 'SharedDamascusRevision') != damascus['REV']:
                raise RuntimeError(f'Omit {package} from the staging copy so its paired normal surface can be cloned.')

    for package in REGISTRY['surfaces']:
        if package in temporal:
            continue
        material = load_material(package)
        new_base = not damascus['field_nodes'](material)
        if new_base:
            common['install'](material, atlas)
            E.set_metadata_tag(material, 'SharedTwoHandFinishRevision', common['REV'])
        changed = damascus['apply_registered'](material)
        if new_base or changed:
            save(material)

    for package, source in temporal.items():
        created = not E.does_asset_exist(package)
        material = E.duplicate_asset(source, package) if created else load_material(package)
        if not material:
            raise RuntimeError(f'Could not duplicate {source} to {package}')
        has_temporal = any(isinstance(n, u.MaterialExpressionTemporalResponsivenessOutput)
                           for n in L.get_material_expressions(material))
        if not has_temporal:
            response = L.create_material_expression(material, u.MaterialExpressionTemporalResponsivenessOutput)
            one = L.create_material_expression(material, u.MaterialExpressionConstant)
            one.set_editor_property('r', 1.0)
            if not L.connect_material_expressions(one, '', response, ''):
                raise RuntimeError('Unconnected temporal response on ' + package)
        if created:
            E.set_metadata_tag(material, 'Whirlwind.TemporalSource', load_material(source).get_path_name())
        changed = damascus['apply_registered'](material) if not created else False
        if created or not has_temporal or changed:
            # A duplicated material inherits its expressions. Copy the revision
            # explicitly because package metadata is independent of the graph.
            normal = load_material(source)
            E.set_metadata_tag(material, 'SharedDamascusRevision', damascus['REV'])
            E.set_metadata_tag(material, 'SharedDamascusField', E.get_metadata_tag(normal, 'SharedDamascusField'))
            save(material)

    for package in REGISTRY['zhanmadao_temporal']:
        material = load_material(package)
        if restore_reference(material):
            save(material)


rebuild()
