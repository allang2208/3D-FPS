# Probe v8: name-keyed cache poisoning test.
#  C: REAL name + one extra declared user parameter (content perturbation)
#  E: near-real name NS_FurnaceTapMetal2, identical content to the real author()
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
import author_furnace_tap_metal as t
from build_fireball_assets import API
from build_fireball_flight import user_parameter

E = u.EditorAssetLibrary
phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'


def build(name, extra_param):
    path = t.DEST + '/' + name
    if E.does_asset_exist(path):
        E.delete_asset(path)
    s = u.AssetToolsHelpers.get_asset_tools().create_asset(
        name, t.DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    t.retire_tags(s)
    t.declare(s)
    if extra_param:
        user_parameter(s, extra_param, '/Script/Niagara.NiagaraFloat')
    t.author_flow(s, phase)
    t.author_pool(s, phase)
    t.author_spark(s, phase)
    t.author_glow(s, phase)
    valid = u.RainAssetEditor.compile_rain(s)
    u.log('PROBE8 %s extra=%s valid=%d' % (name, extra_param, int(valid)))
    E.delete_asset(path)
    return valid


build('NS_FurnaceTapMetal', 'PerturbSeed')
build('NS_FurnaceTapMetal2', None)
u.log('PROBE8-DONE')
