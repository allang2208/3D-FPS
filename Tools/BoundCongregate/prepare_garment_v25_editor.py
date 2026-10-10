from pathlib import Path
BC_V18_IMPORT_STAGE='prepare'
script=Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/import_garment_v25.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),globals())
