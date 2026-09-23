from pathlib import Path
ROOM_IDS=['Distribution']
p=Path(__file__).with_name('import_visual_upgrade.py')
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'))
