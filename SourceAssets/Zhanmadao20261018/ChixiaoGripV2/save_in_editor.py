import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    # End only the current PIE session before changing its loaded animations;
    # the editor and unrelated assets stay open. Save on the next bridge batch.
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    (P/'editor-save-state.json').write_text(json.dumps({'state':'pie_end_requested'}),encoding='utf-8')
    print('CHIXIAO_PIE_END_REQUESTED; run install_grip.py after the PIE session ends')
else:
    file=P/'install_grip.py'
    exec(compile(file.read_text('utf-8'),str(file),'exec'),{'__file__':str(file)})
    (P/'editor-save-state.json').write_text(json.dumps({'state':'saved'}),encoding='utf-8')
