from pathlib import Path
script=Path(__file__).with_name('import_assets.py')
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__','RESUME_SAVED':True})
