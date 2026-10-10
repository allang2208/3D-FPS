"""Save the new rune assets and catalog from a Python commandlet."""
from pathlib import Path
import json

P = Path(__file__).resolve().parent
for name in ['import_assets.py', 'install_catalog.py']:
    script = P / name
    exec(compile(script.read_text(encoding='utf-8-sig'), str(script), 'exec'),
         {'__file__': str(script), '__name__': '__main__'})
(P / 'pending_editor.json').write_text(
    json.dumps({'asset_save_pending': False}, indent=2), encoding='utf-8')
print('HASTE_RUNE_SAVED_AND_INSTALLED')
