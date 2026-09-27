from pathlib import Path
for name in ('inspect_existing.py','import_assets.py'):
    path=Path(__file__).parent/name
    exec(compile(path.read_text(encoding='utf8'),str(path),'exec'),{'__file__':str(path)})
