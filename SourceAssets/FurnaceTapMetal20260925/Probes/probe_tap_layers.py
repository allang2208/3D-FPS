# Probe v3: import the REAL author script's functions and compile layer by layer
# to isolate which emitter/step makes the system invalid. Probe NS deleted, never saved.
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
import author_furnace_tap_metal as t
from build_fireball_assets import API

E = u.EditorAssetLibrary
DEST = t.DEST
NAME = 'NS_ProbeTap3'
path = DEST + '/' + NAME
if E.does_asset_exist(path):
    E.delete_asset(path)

s = u.AssetToolsHelpers.get_asset_tools().create_asset(
    NAME, DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
u.log('PROBE3 created=%s' % bool(s))

t.retire_tags(s)
t.declare(s)
vars_dump = str(API.call_method('GetUserVariables', (s,)).export_text())
u.log('PROBE3 vars=%s' % vars_dump.replace('\n', ' ')[:600])

phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
steps = [('flow', lambda: t.author_flow(s, phase)),
         ('pool', lambda: t.author_pool(s, phase)),
         ('spark', lambda: t.author_spark(s, phase)),
         ('glow', lambda: t.author_glow(s, phase))]
for name, fn in steps:
    try:
        fn()
        u.log('PROBE3 step %s OK' % name)
    except Exception as ex:
        u.log('PROBE3 step %s EXCEPTION %s' % (name, ex))
        break
    valid = u.RainAssetEditor.compile_rain(s)
    u.log('PROBE3 after %s valid=%d' % (name, int(valid)))
    if not valid:
        u.log('PROBE3 CULPRIT=%s' % name)
        break

E.delete_asset(path)
u.log('PROBE3-DONE')
