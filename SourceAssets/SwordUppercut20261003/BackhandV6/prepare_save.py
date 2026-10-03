"""Read editor save availability before writing any animation package."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state = dict(playing=bool(world),world=world.get_name() if world else None)
(P/'save_availability.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('BACKHAND_SAVE_AVAILABILITY '+json.dumps(state))
