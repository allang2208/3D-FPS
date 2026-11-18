"""Repair the Alpha-compressed earth height samples, preserving authored graphs.

Run with a rendering-enabled Python commandlet so RecompileMaterial reports
actual shader compilation errors. This does not launch a gameplay world.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/HillsGroundSamplerRepair20261114'
BASE = '/Game/WorldGeneration/TemperateHills'
HEIGHT = BASE + '/OldChapel/Textures/Surfaces/T_ChapelEarth_H'
REQUIRED = [BASE + '/M_TemperateGround', BASE + '/PebbleShore/M_PebbleShoreGround',
            BASE + '/AbandonedVillage/M_VillageMudRoad']
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'texture': HEIGHT, 'materials': [], 'saved': [], 'game_run': False}
    def receipt():
        (OUT / 'repair.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    texture = u.load_asset(HEIGHT)
    if not texture or texture.compression_settings != u.TextureCompressionSettings.TC_ALPHA:
        raise RuntimeError('Expected the reported TC_ALPHA height texture')
    if texture.virtual_texture_streaming:
        raise RuntimeError('Height texture changed to virtual; re-evaluate sampler')
    registry = u.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([BASE], True)
    options = u.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                              include_hard_package_references=True)
    references = {str(p) for p in registry.get_referencers(HEIGHT, options)}
    report['direct_referencers'] = sorted(references)
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for path in sorted(references | set(REQUIRED)):
        data = registry.get_asset_by_object_path(path + '.' + path.rsplit('/', 1)[-1])
        if str(data.asset_class_path.asset_name) != 'Material':
            continue
        mat = u.load_asset(path)
        nodes = []
        for expr in LIB.get_material_expressions(mat):
            if not isinstance(expr, (u.MaterialExpressionTextureSample, u.MaterialExpressionTextureObject)):
                continue
            if expr.get_editor_property('texture') == texture:
                nodes.append(expr)
        mismatches = [n for n in nodes if n.sampler_type != u.MaterialSamplerType.SAMPLERTYPE_ALPHA]
        row = {'material': path, 'height_samples': len(nodes),
               'before': [str(n.sampler_type) for n in nodes], 'changed': len(mismatches)}
        report['materials'].append(row)
        receipt()
        if mismatches:
            if not path.startswith(BASE + '/') or path in dirty:
                raise RuntimeError('Target is outside owned hills or has unsaved edits: ' + path)
            relative = path.removeprefix('/Game/') + '.uasset'
            original = PROJECT / 'Content' / relative
            row['before_sha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
            for suffix in ('.uasset', '.uexp', '.ubulk'):
                source = original.with_suffix(suffix)
                dest = OUT / 'Before/Content' / Path(relative).with_suffix(suffix)
                if source.exists() and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
            for node in mismatches:
                node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_ALPHA)
        # Required surfaces also compile when already correct, including graph
        # paths outside this texture. An empty error list is UE's compile result.
        row['compile_errors'] = list(LIB.recompile_material(mat))
        receipt()
        if row['compile_errors']:
            raise RuntimeError('Material compilation failed: ' + path + ': ' + str(row['compile_errors']))
        # GetStatistics explicitly submits missing jobs and FinishCompilation in
        # UE 5.8; a mere async recompile request is not completion evidence.
        stats = LIB.get_statistics(mat)
        row['pixel_shader_instructions'] = stats.num_pixel_shader_instructions
        row['vertex_shader_instructions'] = stats.num_vertex_shader_instructions
        receipt()
        if not row['pixel_shader_instructions'] or not row['vertex_shader_instructions']:
            raise RuntimeError('Compiled shader statistics unavailable: ' + path)
        if mismatches:
            if hashlib.sha256(original.read_bytes()).hexdigest() != row['before_sha256']:
                raise RuntimeError('Asset changed on disk during repair: ' + path)
            if not EAL.save_loaded_asset(mat, False):
                raise RuntimeError('Save failed: ' + path)
            row['after_sha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
            report['saved'].append(path)
        row['after'] = [str(n.sampler_type) for n in nodes]
        receipt()
    if not set(REQUIRED).issubset({row['material'] for row in report['materials']}):
        raise RuntimeError('Required ground material missing')
    report['completed'] = True
    receipt()
    u.log('HILLS_HEIGHT_SAMPLER_REPAIRED materials=%d saved=%d compile_errors=0' %
          (len(report['materials']), len(report['saved'])))


if __name__ == '__main__':
    main()
