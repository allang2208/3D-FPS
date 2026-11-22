"""Serialized game-thread installation when the project's interactive editor is open."""
import json
import runpy
from pathlib import Path
import unreal as u
batch=Path(__file__).resolve().parent
project=Path(json.loads((batch/'locations.json').read_text('utf8'))['project'])
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=project.resolve():
    raise RuntimeError('Attached to a different project')
registry=u.AssetRegistryHelpers.get_asset_registry()
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
dirty_targets=[]
loaded_targets=[]
for receipt in ('authored-head.json','authored-icons.json'):
    for path in json.loads((batch/receipt).read_text('utf8')):
        record=registry.get_asset_by_object_path(path)
        if path.split('.')[0] in dirty:
            dirty_targets.append(path)
        if record.is_valid() and record.is_asset_loaded():
            loaded_targets.append(path)
(batch/'editor-state.json').write_text(json.dumps(dict(dirty=dirty_targets,loaded=loaded_targets),indent=2))
if dirty_targets or loaded_targets:
    raise RuntimeError('Publication needs live handling: consult editor-state.json')
runpy.run_path(str(batch/'install.py'),run_name='__main__')
