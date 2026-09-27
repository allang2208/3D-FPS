from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
exec((P/'Tools/ModularOutfit/install_fingerless_tip_clearance.py').read_text(),dict(CORRECTION_DIRECTORY='SavedFingerRefinement'))
