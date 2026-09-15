"""Repair DepthFade/velocity conflicts; run with a real RHI for shader compilation."""
import json
import shutil
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/FireballMotionHeat20260914'
backup = root / 'trash/skills-magic-20260915/SourceAssets/FireballMotionHeat20260914/BeforeVelocityConflictFix'
backup.mkdir(parents=True, exist_ok=True)
report = {'issue': 'OutputVelocity conflicts with DepthFade', 'materials': [], 'game_tested': False}
for name in ['M_FireballFluid_A', 'M_FireballFluid_B', 'M_FluidShortFlamesExposure', 'M_FluidThinWispMotion']:
    disk = root / 'Content/Skills/Fireball/FluidBurn20260914' / (name + '.uasset')
    target = backup / disk.name
    if not target.exists():
        shutil.copy2(disk, target)
    material = unreal.load_asset('/Game/Skills/Fireball/FluidBurn20260914/' + name)
    material.set_editor_property('output_translucent_velocity', False)
    errors = unreal.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError(name + ': ' + '; '.join(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + name)
    report['materials'].append({'asset': material.get_path_name(), 'output_velocity': False, 'compiled': True, 'saved': True})
    unreal.log('FIREBALL_MATERIAL_REPAIRED ' + name)
(source / 'velocity-conflict-fix.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('FIREBALL_VELOCITY_DEPTH_CONFLICT_FIXED')
