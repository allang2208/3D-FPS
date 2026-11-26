"""Freeze the concept-fidelity rebuild without publishing the rejected draft."""
import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR2'
for folder in ['Inputs','Authored','Models','Exports','Textures','Bakes','Logs','Review']:(R/folder).mkdir(parents=True,exist_ok=True)
for name in ['modular_outfits.json','player_body.json','items.json']:shutil.copy2(P/'Content/ColdSteelData'/name,R/'Inputs'/name)
for rig in ['Jason','Kaitlin']:shutil.copy2(S/'CombatShirtR1/Inputs'/f'Body_{rig}.json',R/'Inputs'/f'Body_{rig}.json')
(R/'design-contract.json').write_text(json.dumps(dict(reference=str(S/'Design/TS01_CombatShirt_EarthBrown_R1.png'),garment='Earth-brown ripstop raglan combat shirt with dark stretch torso beneath existing carrier',construction=['continuous shoulder and underarm cloth','native body-specific fit','turned crew neck and cuff/hem facings','low-profile upper-arm pocket with flap and double stitching','articulated elbow reinforcement','compression folds following elbow and wrist, restrained torso folds beneath armor'],production=['separate HIGH and GAME meshes','same-source height/normal/roughness','physical textile scale','native bone frames and actual per-rig weights','transparent inventory image from actual model'],release='No automatic publication of the superseded R1 draft',game_tests_requested=False),indent=2),encoding='utf-8')
print('TS01_COMBAT_R2_PREPARED',flush=True)
