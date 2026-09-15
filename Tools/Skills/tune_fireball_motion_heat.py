"""Install fireball motion-vector correction and hover heat refraction; authoring only."""
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_fluid_burn import (
    DEST, CORE, TRAIL, LIB, API, ref, emitters, setdata, save,
    moving_translucency, secondary_materials, heat_halo_layer,
)

source = ROOT / 'SourceAssets/FireballMotionHeat20260914'
source.mkdir(exist_ok=True)
backup = ROOT / 'trash/skills-magic-20260915/SourceAssets/FireballMotionHeat20260914/Before'
for asset_path in [CORE, TRAIL] + [DEST + '/' + name for name in [
    'M_FireballFluid_A', 'M_FireballFluid_B', 'M_FluidShortFlamesExposure',
    'MI_FluidShortFlames', 'MI_FluidThinWisp', 'M_FluidHoverHeatHalo', 'M_FluidThinWispMotion']]:
    relative = Path(asset_path.removeprefix('/Game/') + '.uasset')
    original, target = ROOT / 'Content' / relative, backup / relative
    if original.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

for label in ['A', 'B']:
    material = unreal.load_asset(DEST + '/M_FireballFluid_' + label)
    moving_translucency(material)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Fireball motion material compile failed: ' + '; '.join(errors))
    save(material)
_, halo, _ = secondary_materials()
core = unreal.load_asset(CORE)
source_emitter = 'FireballFluidBodyA'
lifecycle = {key: unreal.RainAssetEditor.read_input(core, source_emitter, 'EmitterUpdateScript', 'EmitterState', key)
             for key in ['Life Cycle Mode', 'Loop Behavior']}
if 'FireballFluidHeatHaze' in emitters(core):
    API.call_method('RemoveEmitter', (ref(core, 'FireballFluidHeatHaze'),))
heat_halo_layer(core, halo, lifecycle)
for system in [core, unreal.load_asset(TRAIL)]:
    for name in emitters(system):
        setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(system, name, renderer=0),
                {'MotionVectorSetting': 'Precise'})
    save(system)

record = {
    'runtime_core': CORE, 'runtime_trail': TRAIL,
    'motion': 'AfterDOF and TAA ResponsiveAA; precise Niagara vectors retained, material velocity output disabled for DepthFade compatibility',
    'occlusion': 'Keep depth test and depth fade; no AfterMotionBlur depth bypass',
    'halo': halo.get_path_name(), 'size_cm': [60, 68], 'ior_strength': .035,
    'spawn_per_second': 1.25, 'lifetime_seconds': 1.6, 'launch_fade_seconds': [.04, .22],
    'reference': '/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift',
    'owned_noise': '/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A',
    'status': 'Materials and Niagara systems compiled/saved; no game run, render, or automated testing',
}
(source / 'installation.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
integration_path = ROOT / 'SourceAssets/FireballFluidBurn20260914/integration.json'
integration = json.loads(integration_path.read_text(encoding='utf-8'))
integration['motion_heat_revision'] = 'SourceAssets/FireballMotionHeat20260914/installation.json'
integration['motion'] = record['motion']
integration['secondary'] = 'Sparse thin smoke and hover-only annular sword-rift heat refraction; fades out by 220 ms after launch'
noise_source = 'Realistic Starter VFX Pack Vol2 T_NoiseNormal_A, as used by RuneSword WristRiftV3'
if noise_source not in integration['dependencies']:
    integration['dependencies'].append(noise_source)
integration['status'] = record['status']
integration_path.write_text(json.dumps(integration, indent=2), encoding='utf-8')
unreal.log('FIREBALL_MOTION_HEAT_INSTALLED')
