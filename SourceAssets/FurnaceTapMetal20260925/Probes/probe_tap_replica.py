# Probe v5: replicate author() EXACTLY (material pre-call, real order, single final
# compile) under a different asset name; also check for a registry ghost of the real NS.
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
import author_furnace_tap_metal as t
from build_fireball_assets import API

E = u.EditorAssetLibrary
u.log('PROBE5 ghost_real_ns=%s ghost_probe3=%s ghost_probe2=%s' % (
    E.does_asset_exist(t.DEST + '/' + t.NAME),
    E.does_asset_exist(t.DEST + '/NS_ProbeTap3'),
    E.does_asset_exist(t.DEST + '/NS_ProbeTap2')))

t.material()   # same pre-call order as author()

NAME = 'NS_ProbeTap5'
path = t.DEST + '/' + NAME
if E.does_asset_exist(path):
    E.delete_asset(path)
s = u.AssetToolsHelpers.get_asset_tools().create_asset(
    NAME, t.DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
t.retire_tags(s)
t.declare(s)
phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
t.author_flow(s, phase)
t.author_pool(s, phase)
t.author_spark(s, phase)
t.author_glow(s, phase)
E.set_metadata_tag(s, t.TAG, 'probe v5 replica of author() metadata tag')
u.log('PROBE5 authored all layers, single final compile:')
valid = u.RainAssetEditor.compile_rain(s)
u.log('PROBE5 RESULT valid=%d' % int(valid))

# second compile without the metadata tag difference: compile again as-is
valid2 = u.RainAssetEditor.compile_rain(s)
u.log('PROBE5 RECOMPILE valid=%d' % int(valid2))
E.delete_asset(path)
u.log('PROBE5-DONE')
