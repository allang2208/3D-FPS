"""Produce only the four ocean material assets; preserve cloud, mesh and map."""
from pathlib import Path
import unreal as u
root=Path(__file__).parent
file=root/'import_distant_ocean.py'
scope={'__file__':str(file),'REBUILD_CLOUDS':False,'MATERIALS_ONLY':True}
exec(compile(file.read_text(encoding='utf8'),str(file),'exec'),scope)
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
(root/'Receipts/ocean-natural-materials.json').write_text((root/'Receipts/ocean-import.json').read_text(encoding='utf8'),encoding='utf8')
print('GODSPACE_OCEAN_NATURAL_MATERIALS_SAVED')
