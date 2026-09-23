from pathlib import Path
p=Path(__file__).with_name('import_animations.py')
exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'FAMILY':'vertical'})
