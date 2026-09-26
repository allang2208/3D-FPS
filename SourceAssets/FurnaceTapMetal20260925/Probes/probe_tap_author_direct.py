# Probe v6: call the REAL t.author() verbatim (real name, real tag, real save path).
# If it compiles now, the asset lands; if it raises, the culprit is inside author().
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
import author_furnace_tap_metal as t

try:
    obj = t.author()
    u.log('PROBE6 AUTHOR-OK ' + obj.get_path_name())
except Exception as ex:
    u.log('PROBE6 AUTHOR-FAIL %r' % ex)
u.log('PROBE6-DONE')
