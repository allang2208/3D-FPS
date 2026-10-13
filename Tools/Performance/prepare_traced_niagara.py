"""Compile and save only the two Niagara systems implicated by the 2026-10-12 trace.

Run with the PythonScript commandlet while the editor is closed. This is asset
production, not a gameplay run: no systems are spawned, simulated, or rendered.
Reuse RainAssetEditor's existing VM + GPU compilation wait; never force a graph
recompile or change effect parameters. Output includes original package backups.
"""
import datetime
import hashlib
import json
import shutil
import time
from pathlib import Path

import unreal as u


TARGETS = (
    '/Game/Skills/Lightning/NS_LightningChain',
    '/Game/Skills/ElectricMagic/StormDomainV2/NS_StormDomainCloud',
)

# The production log also exposed a missing SM6 shader map for this dependency.
# Keep this scoped to the observed material; do not force-recompile the project.
MATERIALS = ('/Game/Skills/ElectricMagic/StormDomainV2/M_StormDomainCloud',)


def prepare():
    root = Path(u.Paths.project_dir()).resolve()
    job = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = root / 'Saved' / 'NiagaraCompilePreparation' / job
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'status': 'preparing', 'assets': [], 'materials': [], 'gameplay_tested': False,
               'graph_or_visual_parameters_changed': False}
    report = output / 'receipt.json'

    def persist():
        report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        for path in TARGETS:
            if path in dirty:
                raise RuntimeError('Preserve unsaved package: ' + path)
        for path in TARGETS:
            relative = Path('Content') / (path.removeprefix('/Game/') + '.uasset')
            package = root / relative
            backup = output / 'Originals' / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package, backup)
            row = {'asset': path, 'backup': str(backup),
                   'sha256_before': hashlib.sha256(package.read_bytes()).hexdigest()}
            receipt['assets'].append(row)
            persist()
            start = time.perf_counter()
            system = u.load_asset(path)
            if not isinstance(system, u.NiagaraSystem):
                raise RuntimeError('Niagara system unavailable: ' + path)
            if not u.RainAssetEditor.compile_rain(system):
                raise RuntimeError('Niagara compilation failed: ' + path)
            row['vm_and_gpu_compile_finished'] = True
            row['compilation_seconds'] = time.perf_counter() - start
            if not u.EditorAssetLibrary.save_loaded_asset(system, False):
                raise RuntimeError('Could not save compiled Niagara system: ' + path)
            row['saved'] = True
            row['sha256_after'] = hashlib.sha256(package.read_bytes()).hexdigest()
            persist()
        for path in MATERIALS:
            material = u.load_asset(path)
            if not isinstance(material, u.MaterialInterface):
                raise RuntimeError('Material unavailable: ' + path)
            start = time.perf_counter()
            # UE 5.8 GetStatistics submits missing jobs, then calls the material
            # resource's FinishCompilation. This waits for this material only;
            # it does not alter its graph or force a new shader-map key.
            stats = u.MaterialEditingLibrary.get_statistics(material)
            receipt['materials'].append({
                'asset': path, 'compilation_wait_finished': True,
                'compilation_seconds': time.perf_counter() - start,
                'pixel_shader_instructions': stats.num_pixel_shader_instructions,
                'cache_destination': 'local DDC; current RHI shader platform',
                'material_asset_saved': False,
            })
            persist()
        receipt['status'] = 'saved'
        persist()
        print('TRACED_NIAGARA_PREPARED ' + str(report))
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['error'] = str(error)
        persist()
        raise


prepare()
