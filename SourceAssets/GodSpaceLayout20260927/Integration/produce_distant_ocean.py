"""One serialized authoring batch; no PIE, captures or runtime tests."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent
for name in ['import_distant_ocean.py','apply_distant_ocean.py']:
    file=ROOT/name
    exec(compile(file.read_text(encoding='utf8'),str(file),'exec'),{'__file__':str(file)})
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
print('GODSPACE_OCEAN_PRODUCTION_COMPLETE')
