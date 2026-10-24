"""Use the existing UCX/normal/Nanite importer on the selected V5 meshes only."""
from pathlib import Path
import runpy,json
ROOT=Path(__file__).resolve().parent
source=(ROOT.parent/'RefinementV4/import_meshes.py').read_text('utf8')
source=source.replace('from surface_specs import *',"import runpy\n_specs=runpy.run_path(str(Path(__file__).resolve().parent.parent/'RefinementV4/surface_specs.py'))\nSPECS=_specs['SPECS'];ALIASES=_specs['ALIASES']\nROOT=Path(__file__).resolve().parent\nBASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV5'")
start=source.index('def mat(role):');end=source.index('\ntry:',start)
source=source[:start]+'''def mat(role):
 role=role.removeprefix('AP_');role=ALIASES.get(role,role)
 if role in ('WindowGlass','ShowerGlass','Mirror','BathTile','BathWall'):return load(BASE+'/Materials/M_AP5_'+role)
 if role in SPECS:return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV4/Materials/MI_AP4_'+role)
 return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3/Materials/M_AP_'+role)
'''+source[end:]
exec(compile(source,str(ROOT/'import_selected.py'),'exec'),{'__file__':str(ROOT/'import_selected.py'),'__name__':'__main__'})
