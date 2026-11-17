"""Match visible flame coverage to the intended impact footprint, in place."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import assignments, LIB
from build_fireball_flames import VEC2, FLOAT

DEST = '/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7'
OUT = ROOT / 'SourceAssets/MeteorVisualReview20261114'
A = 'Particles.Age'
H = 'clamp(sqrt(User.ImpactRadius/652.5),.85,1.25)'


def run():
    editor = u.EditorAssetLibrary
    author = u.DragonBreathAuthorLibrary if hasattr(u, 'DragonBreathAuthorLibrary') else u.RainAssetEditor
    u.RainAssetEditor = author
    names = ['NS_MeteorPressureV7','M_PressureCombustionV7','M_PressureAfterSmokeV7','M_PressureRaysV7','M_GroundPressureV7']
    targets = {DEST.rsplit('/',1)[0]+'/'+name for name in names}
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if targets.intersection(dirty):
        raise RuntimeError('Meteor targets have unsaved edits: '+str(sorted(targets.intersection(dirty))))
    before = OUT / 'BeforeAssets'
    before.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = ROOT / 'Content/Skills/FireMagic20260921/MeteorImpactReferenceV7' / (name+'.uasset')
        backup = before / source.name
        if not backup.exists():
            shutil.copy2(source, backup)
    sizes = {
        'RefContactImpulse': f'float2(340,210)*{H}*(.78+.22*(1-exp(-{A}*90)))',
        'RefRadialPressureFan': f'float2(1120,620)*{H}*(.65+.35*(1-exp(-{A}*42)))',
        'RefWhiteHotCore': f'float2(480,340)*{H}*(.78+.25*(1-exp(-{A}*30)))',
        'RefPressureFireCrown': f'float2(min(User.ImpactRadius*1.75,1500),560*{H})*(.86+.14*(1-exp(-{A}*22)))',
    }
    system = u.load_asset(DEST)
    for emitter, expression in sizes.items():
        for stage in ['ParticleSpawnScript', 'ParticleUpdateScript']:
            assignments(system, emitter, stage, {'Particles.SpriteSize': (VEC2, expression)})
    assignments(system,'RefRadialPressureFan','ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'.20')})
    SEED='frac(float(Particles.UniqueID)*.61803398875+.173)'
    for stage in ['ParticleSpawnScript','ParticleUpdateScript']:
        assignments(system,'RefCooledRollingSmoke',stage,{'Particles.SpriteSize':(VEC2,f'float2(280,260)*(.76+.3*{SEED})*(.65+.50*Particles.NormalizedAge)')})
    vec4='/Script/CoreUObject.Vector4f'
    n='Particles.NormalizedAge'
    contract=json.loads((ROOT/'SourceAssets/MeteorImpactReferenceV7_20261114/Blast/atlas-manifest.json').read_text(encoding='utf8'))
    first,last=contract['playback_windows']['fire'];denom=contract['frames']-1
    fire_age=f'(({first}+.35+({last-first}-.35)*pow({n},.72))/{denom})'
    core_age=f'(({first}+.35+({last-first}*.55)*{n})/{denom})'
    dynamics={
        'RefRadialPressureFan':f'float4({n},.27,8*pow(saturate(1-{n}),1.35)+.35,0)',
        'RefWhiteHotCore':f'float4({core_age},0,3.8*pow(1-{n},2)+.2,0)',
        'RefPressureFireCrown':f'float4({fire_age},0,.95-.55*{n},0)',
        'RefGroundShockFront':f'float4({n},.37,1.3*(1-{n})+.10,0)',
    }
    for emitter,expression in dynamics.items():
        for stage in ['ParticleSpawnScript','ParticleUpdateScript']:
            assignments(system,emitter,stage,{'Particles.DynamicMaterialParameter':(vec4,expression)})
    materials=[]
    for name in names[1:]:
        material=u.load_asset(DEST.rsplit('/',1)[0]+'/'+name)
        smoke=name=='M_PressureAfterSmokeV7'
        for node in LIB.get_material_expressions(material):
            if isinstance(node,u.MaterialExpressionCustom):
                tag=node.get_editor_property('description')
                if tag=='MeteorV6.Sample':
                    node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_reference_v7_sample.hlsl').read_text(encoding='utf8'))
                elif tag=='MeteorV6.Thermal':
                    node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_reference_v7_thermal.hlsl').read_text(encoding='utf8'))
                elif tag=='MeteorV6.Opacity':
                    node.set_editor_property('code','return (1-exp(-pow(max(0,Fields.b-.008),.85)*4.8))*Alpha;' if smoke else 'return (1-exp(-max(0,Fields.r-.003)*4.2))*Alpha;')
                elif tag=='MeteorV7.Shape':
                    kind='rays' if name=='M_PressureRaysV7' else 'pressure'
                    node.set_editor_property('code',(ROOT/f'Tools/Skills/meteor_reference_v7_{kind}.hlsl').read_text(encoding='utf8'))
            elif isinstance(node,u.MaterialExpressionDepthFade) and name in names[1:3]:
                node.set_editor_property('fade_distance_default',24.0 if smoke else 18.0)
        materials.append(material)
    material_compiler = author if hasattr(author, 'compile_material_assets') else u.PoisonMaggotMonster
    if not material_compiler.compile_material_assets(materials):
        raise RuntimeError('Meteor material compilation failed')
    editor.set_metadata_tag(system, 'Meteor.VisibleFootprint', '20261114: compensate 60-64 percent flame coverage; preserve budget and radius')
    if not author.compile_rain(system, True):
        raise RuntimeError('Meteor compile failed')
    for asset in materials+[system]:
        if not editor.save_loaded_asset(asset, False):
            raise RuntimeError('Meteor save failed '+asset.get_path_name())
    receipt = dict(revision=3,pressure_fan_seconds=.20,saved_assets=[a.get_path_name() for a in materials+[system]],content_root=u.Paths.project_content_dir(),sizes=sizes, particle_count_changed=False,
                   lights_changed=False, gameplay_changed=False, source_fire_peak_width_fraction=160/247,
                   previous_peak_visible_width_cm=652.5*1.08*160/247,
                   new_peak_visible_width_cm=652.5*1.75*160/247)
    (OUT / 'scale-repair.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('METEOR_VISIBLE_SCALE_SAVED ' + system.get_path_name(), flush=True)


if __name__ == '__main__':
    run()
