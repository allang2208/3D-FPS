from pathlib import Path
P=Path(__file__).resolve().parent
for name in ('import_assets.py','import_motion_ui.py'):
    path=P/name
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
print('JI_LEI_ALL_ASSETS_SAVED',flush=True)
