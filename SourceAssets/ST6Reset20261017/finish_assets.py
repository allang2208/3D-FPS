from pathlib import Path
O=Path(__file__).parent
for name in ('import_pickup_icon.py','publish.py'):
    file=O/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file)})
