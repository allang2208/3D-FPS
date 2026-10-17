"""Apply only the saved M870 elbow surface correction to editable arm objects."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
O=Path(__file__).parent;patch=json.loads((O/'elbow_surface.json').read_text());tree=KDTree(len(patch['edits']))
for i,e in enumerate(patch['edits']):tree.insert(Vector(e['before']),i)
tree.balance();count=0
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or 'V7' not in ob.name or ob.get('M870LeftElbow20261016'):continue
 inv=ob.matrix_world.inverted()
 for vertex in ob.data.vertices:
  p=ob.matrix_world@vertex.co;_,i,d=tree.find(p)
  if d<.00005:vertex.co=inv@Vector(patch['edits'][i]['after']);count+=1
 ob['M870LeftElbow20261016']=True
print('M870_EDITABLE_ELBOW_SURFACE',count,flush=True)
