"""Author only the blade paint and cutting-guide materials in the isolated host."""
from pathlib import Path
import json
import runpy
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'Saved/WoodworkingSawHighlight20261013'
HOST=TASK/'MaterialHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():
    raise RuntimeError('Use the isolated woodworking material host')
module=runpy.run_path(str(Path(__file__).with_name('paint_material.py')))
paint=module['build']('/Game/Building/WoodworkingBenchV6Controls20261013')
guide=module['build_guide']()
receipt={'assets':[paint['blade'].get_path_name(),paint['merged'].get_path_name(),guide.get_path_name()],
         'paint_inner_radius_cm':13.2,'paint_full_radius_cm':13.4,'blade_radius_cm':16.2,
         'paint_emission':1.5,'exposure_compensated':True,'guide':'opaque unlit vertex colour',
         'game_or_pie_started':False,'tests_run':False}
(TASK/'material-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WOODWORKING_SAW_MATERIALS_SAVED '+json.dumps(receipt))
