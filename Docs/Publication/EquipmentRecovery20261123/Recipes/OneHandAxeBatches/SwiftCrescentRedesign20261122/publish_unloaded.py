"""Serialized game-thread installation when the project's interactive editor is open."""
import json
import runpy
from pathlib import Path
import unreal as u
batch=Path(__file__).resolve().parent
registry=u.AssetRegistryHelpers.get_asset_registry()
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for receipt in ('authored-head.json','authored-icons.json'):
    for path in json.loads((batch/receipt).read_text('utf8')):
        record=registry.get_asset_by_object_path(path)
        if path.split('.')[0] in dirty or (record.is_valid() and record.is_asset_loaded()):
            raise RuntimeError('Package open in editor '+path)
runpy.run_path(str(batch/'install.py'),run_name='__main__')
