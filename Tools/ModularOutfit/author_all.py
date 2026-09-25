"""Create all physical-unit derivatives and production item images in order."""
from pathlib import Path
tools=Path('D:/FPS3D/FPSGAME/Tools/ModularOutfit')
for name in ('author_equipment.py','author_bare_hands.py','author_item_presentation.py'):
    path=tools/name
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__name__':'__main__'})
print('ALL_OUTFIT_AUTHORING_SAVED',flush=True)
