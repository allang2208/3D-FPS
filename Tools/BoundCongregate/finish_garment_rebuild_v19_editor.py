from pathlib import Path
BC_V18_IMPORT_STAGE='finish'
script=Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/import_garment_rebuild_v19.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),globals())
