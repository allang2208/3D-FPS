from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
for name in ('load_scene_inputs.py','import_assets.py','install_scene.py'):
    print('BENCH_POLISH_STAGE '+name)
    runpy.run_path(str(ROOT/'Scripts'/name),run_name='__main__')
