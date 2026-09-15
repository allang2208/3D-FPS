"""Repair only the fireball emissive/exposure contract; preserve particle motion."""
import json
import shutil
import sys
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/FireballFluidBurn20260914'
sys.path.insert(0, str(root / 'Tools/Skills'))
from build_fireball_fluid_burn import combustion_material, secondary_materials, DEST

backup = root / 'trash/skills-magic-20260915/SourceAssets/FireballFluidBurn20260914/BeforeExposureFix'
backup.mkdir(parents=True, exist_ok=True)
for name in ['M_FireballFluid_A','M_FireballFluid_B','MI_FluidShortFlames']:
    target = backup / (name + '.uasset')
    if not target.exists():
        shutil.copy2(root / 'Content/Skills/Fireball/FluidBurn20260914' / target.name, target)
for label in ['A','B']:
    combustion_material(unreal.load_asset(DEST+'/T_FireballFluid_'+label), label)
secondary_materials()
path = source / 'integration.json'
record = json.loads(path.read_text(encoding='utf-8'))
record['emissive_exposure'] = 'Body and short flames now use EyeAdaptationInverse; alpha and depth fade are unchanged'
record['exposure_fix'] = 'fix_flame_exposure.py; targeted visibility diagnosis recorded separately'
path.write_text(json.dumps(record,indent=2),encoding='utf-8')
unreal.log('FIREBALL_EXPOSURE_FIX_SAVED')
