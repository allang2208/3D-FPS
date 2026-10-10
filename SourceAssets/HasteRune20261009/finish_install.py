"""Finish only this rune's saved assets when the current play session is idle."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
playing=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
if playing:
    (P/'pending_editor.json').write_text(json.dumps({'asset_save_pending':True,'reason':'Current PIE session is active; preserved without stopping it.'},indent=2),encoding='utf-8')
    print('HASTE_RUNE_PENDING_CURRENT_PLAY')
else:
    for name in ['import_assets.py','install_catalog.py']:
        file=P/name
        exec(compile(file.read_text(encoding='utf-8-sig'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
    (P/'pending_editor.json').write_text(json.dumps({'asset_save_pending':False},indent=2),encoding='utf-8')
    print('HASTE_RUNE_SAVED_AND_INSTALLED')
