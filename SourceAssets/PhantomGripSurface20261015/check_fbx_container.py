import sys,types,importlib.util,numpy as np
from pathlib import Path
folder=Path('E:/Program Files/Blender Foundation/Blender 5.1/5.1/scripts/addons_core/io_scene_fbx');pkg=types.ModuleType('fbxcheck');pkg.__path__=[str(folder)];sys.modules['fbxcheck']=pkg
spec=importlib.util.spec_from_file_location('fbxcheck.parse_fbx',folder/'parse_fbx.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
O=Path(__file__).parent
for key in ['M4','AKM','QBZ191','M16','HK416','A762','PKM','Super90','LMG201']:
 root,version=m.parse(str(O/'Exports'/(key+'.fbx')));bad=[]
 def visit(n):
  for p in n.props:
   if hasattr(p,'typecode') and p.typecode in 'fd' and not np.isfinite(p).all():bad.append((n.id,int((~np.isfinite(p)).sum())))
  for ch in n.elems:visit(ch)
 visit(root);print('FBX_VALID_CONTAINER',key,version,'nonfinite',bad,flush=True)
