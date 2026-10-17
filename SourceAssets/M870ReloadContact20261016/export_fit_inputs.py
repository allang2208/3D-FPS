import bpy,json,gzip,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
code=(O/'author_reload_contact.py').read_text().split('tree=ast.parse')[0]
exec(compile(code,str(O/'author_reload_contact.py'),'exec'))
d=json.loads(gzip.decompress((O.parent/'M870SurfaceFit20261016/native_arms.json.gz').read_bytes()))
shell=bpy.data.objects['M870_ReloadShell'];inverse=r.pose.bones['WPN_Shell'].matrix.inverted()
points={n:[] for n in ('thumb','index','middle','ring','all')}
for v,w in zip(d['vertices'],d['weights']):
 if sum(value for n,value in w.items() if n in template)<.999:continue
 vertex=Vector((v[0]/100,-v[1]/100,v[2]/100))
 p=inverse@sum((template[n]@rest[n].inverted()@vertex*value for n,value in w.items() if n in template),Vector())
 points['all'].append(list(p))
 for digit in ('thumb','index','middle','ring'):
  if sum(value for n,value in w.items() if n in (digit+'_02_r',digit+'_03_r'))>.75:points[digit].append(list(p))
points={k:np.array(v) for k,v in points.items()}
points['shell']=np.array([list(rest['WPN_Shell'].inverted()@shell.matrix_world@v.co) for v in shell.data.vertices])
points['triangles']=np.array([list(p.vertices) for p in shell.data.polygons])
np.savez_compressed(O/'fit_inputs.npz',**points)
print('M870_RIGID_CONTACT_INPUTS',{k:len(v) for k,v in points.items()})
