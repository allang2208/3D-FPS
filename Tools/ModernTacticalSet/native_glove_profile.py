"""The two fitted equipment families share an authoring process and atlas."""
import os
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
SET = P / 'SourceAssets/ModernTacticalSet20261113'
BASE = SET / 'NativeGloveR1'
RIG = os.environ.get('TS01_NATIVE_GLOVE_RIG','Super90')
if RIG not in ('Super90','M16'):
    raise ValueError(RIG)
R = BASE if RIG=='Super90' else BASE/'M16'
GUNS = ('M870','Super90') if RIG=='Super90' else ('M16',)
MODEL_NAME = 'SK_TS01_NativeShotgunGloves' if RIG=='Super90' else 'SK_TS01_NativeM16Gloves'
SOURCE_FILE = R/('ShotgunGloves.json' if RIG=='Super90' else 'M16Gloves.json')
