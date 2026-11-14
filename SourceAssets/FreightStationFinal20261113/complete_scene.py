from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
def apply(w,req):
    lighting=runpy.run_path(str(R/'lighting.py'))['apply'](w,req)
    walls=runpy.run_path(str(R/'install_walls.py'))['apply'](w,req)
    patina=runpy.run_path(str(R/'install_patina.py'))['apply'](w,req)
    return dict(lighting=lighting,walls=walls,patina=patina)
