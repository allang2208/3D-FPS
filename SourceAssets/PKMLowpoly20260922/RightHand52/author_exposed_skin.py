from pathlib import Path
import json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
P=Path(__file__).resolve().parent;bare=json.loads((P/'Authored/BarePalmV7.json').read_text());vertices=[Vector(v) for v in bare['positions']];digits=['thumb','index','middle','ring','pinky']
def label(ws):
 scores=[sum(w for n,w in ws.items() if n.startswith(d+'_') and n.endswith('_r')) for d in digits]
 return digits[max(range(5),key=lambda i:scores[i])] if max(scores)>.35 else 'palm'
labels=[label(ws) for ws in bare['weights']];right=[sum(w for n,w in ws.items() if n.endswith('_r'))>.99 for ws in bare['weights']];trees={}
for kind in digits+['palm']:
 faces=[f for f in bare['triangles'] if all(right[v] for v in f) and sum(labels[v]==kind for v in f)>=2];trees[kind]=(BVHTree.FromPolygons(vertices,faces,all_triangles=True),faces)
for family in ['TailoredSkin']:
 data=json.loads((P/'Inputs'/f'{family}_source.json').read_text());count=0
 for i,old in enumerate(data['weights']):
  if sum(w for n,w in old.items() if n.endswith('_r'))<.99:continue
  tree,faces=trees[label(old)];hit,_,fi,_=tree.find_nearest(Vector(data['positions'][i]));face=faces[fi];bary=barycentric_transform(hit,*[vertices[j] for j in face],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));new={}
  for vi,f in zip(face,bary):
   for n,w in bare['weights'][vi].items():new[n]=new.get(n,0)+max(0,float(f))*w
  total=sum(new.values());data['weights'][i]={n:w/total for n,w in new.items() if w>1e-9};count+=1
 data['right_hand_revision']='RightHand52';data['bare_authored_sha256']=hashlib.sha256((P/'Authored/BarePalmV7.json').read_bytes()).hexdigest();(P/'Authored'/f'{family}.json').write_text(json.dumps(data,separators=(',',':')));print('CURRENT_GLOVE_AUTHORED',family,count)

