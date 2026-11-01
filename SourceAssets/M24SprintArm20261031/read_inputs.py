from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O.parent/'M24IdleArm20261030/read_inputs.py').read_text(),'read_current_M24','exec'))
exec(compile((O.parent/'M24IdleArm20261030/read_roles.py').read_text(),'read_current_roles','exec'))
# Read the existing authoring frame inputs without taking ownership of outfits.
context=O.parent/'M24GripOutfit20261030/game_context.json'
if context.exists():(O/'game_context.json').write_bytes(context.read_bytes())
print('M24_RELOAD_INPUTS_READY',flush=True)
