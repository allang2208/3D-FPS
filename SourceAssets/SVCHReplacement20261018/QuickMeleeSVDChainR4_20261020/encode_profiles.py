"""Encode the existing elbow-support result without regenerating its input."""
from pathlib import Path
import json,numpy as np
import author
O=Path(__file__).resolve().parent
poses=np.load(O/'poses.npz')
for family in ('base','angled','vertical','canted','prism'):
    source=json.loads((author.R3/'SavedReadback'/f'{family}.json').read_text())
    author.write_profile(source,poses[family],family)
print('SVCH_R4_FINAL_PROFILES_ENCODED',flush=True)
