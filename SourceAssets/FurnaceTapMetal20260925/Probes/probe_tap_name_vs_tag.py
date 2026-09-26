# Probe v7: bisect name vs metadata-tag. Two independent systems in one process:
#  A: REAL name NS_FurnaceTapMetal + short tag
#  B: probe name NS_ProbeTap7B + the REAL big author() tag
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
import author_furnace_tap_metal as t
from build_fireball_assets import API

E = u.EditorAssetLibrary
phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'


def build(name, tag_text):
    path = t.DEST + '/' + name
    if E.does_asset_exist(path):
        E.delete_asset(path)
    s = u.AssetToolsHelpers.get_asset_tools().create_asset(
        name, t.DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    t.retire_tags(s)
    t.declare(s)
    t.author_flow(s, phase)
    t.author_pool(s, phase)
    t.author_spark(s, phase)
    t.author_glow(s, phase)
    E.set_metadata_tag(s, t.TAG, tag_text)
    valid = u.RainAssetEditor.compile_rain(s)
    u.log('PROBE7 %s valid=%d' % (name, int(valid)))
    E.delete_asset(path)
    return valid


big = ('Molten tap stream + pool + sparks + ingot afterglow for the blast furnace ('
       'Docs/Fluids/furnace-tap-metal-20260925.md). L0 FurnaceTapMetalFlow: analytic parabola '
       'from the mesh-local tap arch (17.5,0,69.4) / channel (17.5,0,63.5) / shaft exit '
       '(24.7,0,63.5) to the casting bed (32.9,0,20), g0 %.0f cm/s2, flight %.2fs, life %s, '
       '%d/s while User.Flow=1, live cap %d; white-hot core -> gold -> orange rim (a<1.2s) then '
       'cooling. L1 FurnaceTapPool: one card on the bed, expand %.2fs -> cool %.2fs -> contract, '
       'alpha and colour analytic in age. L3 FurnaceTapSpark: instantaneous SpawnBurst <=%d gated '
       'by User.SparkGate (<35m and quality>=medium, written in C++). L2 FurnaceTapIngotGlow: '
       '%.0fs linear-decay card at the mould arc (45,0,20) gated by User.IngotGlow. Material '
       '%s is fully procedural (unlit additive, value-noise + hex cells); no new bitmap. '
       'C++ owns the pool, the ingot mesh and the 85m/35m gates.' % (
           t.GRAVITY, t.FLIGHT, t.FLOW_LIFE, t.FLOW_COUNT, t.LIVE_CAP, t.POOL_GROW, t.POOL_COOL,
           t.SPARK_COUNT, t.GLOW_LIFE, t.MAT))

build('NS_FurnaceTapMetal', 'short tag A')
build('NS_ProbeTap7B', big)
u.log('PROBE7-DONE')
