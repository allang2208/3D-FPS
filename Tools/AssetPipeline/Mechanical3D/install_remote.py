"""Install candidate node and model files; never load models or submit generation."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import urllib.request

root = Path(sys.argv[1])
stage = Path('D:/Mechanical3DSetup')
os.environ['HF_HOME'] = str(stage / 'huggingface')
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'
os.environ['HF_HUB_ETAG_TIMEOUT'] = '60'

revision = 'f8c676ae94280f164e58a1179ce127efea6f81e1'
node_dir = root / 'custom_nodes/ComfyUI-Trellis2-MultiViewRefiner'
node_dir.mkdir(parents=True, exist_ok=True)
for name in ('__init__.py', 'nodes_multiview_refiner.py', 'LICENSE', 'README.md', 'pyproject.toml'):
    target = node_dir / name
    source = stage / 'refiner_source' / name
    shutil.copy2(source, target)
print('REFINER_FILES_INSTALLED', flush=True)

# This installed wrapper implements projection attention with existing Torch
# modules; its source does not import NATTEN. Keep that working implementation.
# A preliminary NATTEN package build failed before installation; do not force
# a Torch replacement to satisfy an unused dependency.

from huggingface_hub import snapshot_download
for repo, folder, ignores in (
    ('TencentARC/Pixal3D', 'TencentARC/Pixal3D-T', ['*_mv*']),
    ('Ruicheng/moge-2-vitl', 'Ruicheng/moge-2-vitl', None),
):
    print('DOWNLOADING ' + repo, flush=True)
    snapshot_download(repo_id=repo, local_dir=str(root / 'models' / folder),
                      ignore_patterns=ignores, max_workers=3)
    print('DOWNLOADED ' + repo, flush=True)

(stage / 'installation.json').write_text(json.dumps({
    'refiner_revision': revision,
    'attention': 'existing wrapper Torch projection implementation; no NATTEN installation',
    'pixal_repository': 'TencentARC/Pixal3D',
    'pixal_local_alias': 'TencentARC/Pixal3D-T',
    'tested': False,
}, indent=2), encoding='utf-8')
print('INSTALLATION_COMPLETE_NO_TESTS', flush=True)
