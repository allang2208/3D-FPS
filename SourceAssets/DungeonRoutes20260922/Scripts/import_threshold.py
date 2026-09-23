from pathlib import Path
ROOM_IDS={'Threshold'}
source=Path(__file__).with_name('import_modules.py')
exec(compile(source.read_text(),str(source),'exec'),globals())
