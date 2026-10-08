import unreal as u
from pathlib import Path
import json
OUT=Path(__file__).resolve().parent
print('SLATE_CLASSES '+str([n for n in dir(u) if 'SlateInspector' in n]))
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('WORLD '+str(w)+' PAUSED '+str(u.GameplayStatics.is_game_paused(w) if w else None))
if w:
    pc=u.GameplayStatics.get_player_controller(w,0)
    print('PC_METHODS '+str([n for n in dir(pc) if any(k in n for k in ['mode','game','menu','profile','start'])]))
    a=u.GameplayStatics.get_player_character(w,0)
    print('SWORD '+str([str(c) for c in a.get_components_by_class(u.ActorComponent) if 'RuneSword' in c.get_class().get_name()]))
