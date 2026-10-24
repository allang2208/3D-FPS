"""Install the assembled task-owned package tree at its unchanged /Game path."""
import hashlib
import json
import shutil
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023'
receipt = json.loads((WORK / 'assembly_receipt.json').read_text(encoding='utf-8'))
if receipt['status'] != 'native_assembly_saved_in_authoring_host':
    raise RuntimeError('No completed native assembly is available to install.')
relative = Path('Characters/KaitlinPlayer20261023/Native')
source = WORK / 'AuthorHost/Content' / relative
destination = PROJECT / 'Content' / relative
copies = []
for original in source.rglob('*'):
    if not original.is_file():
        continue
    output = destination / original.relative_to(source)
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if output.exists() and hashlib.sha256(output.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Existing destination differs; retain the editor asset: ' + str(output))
    copies.append((original, output, digest))
for original, output, digest in copies:
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, output)
(WORK / 'native_install_receipt.json').write_text(json.dumps({
    'status': 'native_packages_installed', 'runtime_published': False,
    'files': [{'path': str(output.relative_to(PROJECT)), 'sha256': digest} for _, output, digest in copies],
    'skeletal_meshes': receipt['skeletal_meshes'],
    'complete_body': (json.loads((WORK / 'full_body_receipt.json').read_text(encoding='utf-8'))['mesh']
                      if (WORK / 'full_body_receipt.json').exists() else None),
}, indent=2), encoding='utf-8')
print('KAITLIN_NATIVE_PACKAGES_INSTALLED', len(copies))
