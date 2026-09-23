from pathlib import Path
ROOM_IDS=['ShoredBreach']
p=Path(__file__).with_name('import_rooms.py')
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'))
