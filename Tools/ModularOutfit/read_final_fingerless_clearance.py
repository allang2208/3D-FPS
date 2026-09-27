from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
exec((P/'Tools/ModularOutfit/read_fingerless_clearance.py').read_text(),dict(REVIEW_DIRECTORY='ClearanceAfter',READ_COMPANIONS=True))
