"""Extend the saved contact repair with the original 715 five-round loader."""
from pathlib import Path
import sys
O=Path(__file__).parent;sys.path.insert(0,str(O))
from loader_geometry import build as build_loader,emit as emit_loader
from loader_motion import LoaderContact
code=(O/'author_base.py').read_text()
code=code.replace("raw=json.loads", "D['clips'].update(json.loads((O/('speed_'+SIDE+'.json')).read_text())['clips'])\nraw=json.loads",1)
code=code.replace("mat=bpy.data.materials.new('M_RSH12_SourcePBR')", "points['WPN_Loader']=Vector()\nloader_geometry_transform=build_loader(globals())\nmat=bpy.data.materials.new('M_RSH12_SourcePBR')",1)
code=code.replace('def matrix(v):', 'emit_loader(globals(),loader_geometry_transform)\n\ndef matrix(v):',1)
code=code.replace('def smooth(x):', 'loader_solver=LoaderContact(globals())\ndef smooth(x):',1)
code=code.replace('if contact_solver:contact_solver.begin()', 'if contact_solver:contact_solver.begin()\n loader_solver.begin()',1)
code=code.replace('  for n in list(tracks):', "  for n in loader_solver.apply(kind,t,old,world,local):\n   if n not in tracks:tracks[n]=[]\n  for n in list(tracks):",1)
code=code.replace("print('RSH12_CONTACT_REPAIR_GEOMETRY_SAVED'", "(OUT/'loader_recipe.json').write_text(json.dumps(loader_recipe,indent=2))\nprint('RSH12_SPEEDLOADER_GEOMETRY_SAVED'",1)
exec(compile(code,str(O/'author_base.py'),'exec'),globals())
