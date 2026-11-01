from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'inspect.py').read_text().split('\nfolder=')[0],'setup','exec'))
row={n:Matrix(m) for n,m in json.loads((O/'final_poses.json').read_text())['base'][30].items()};r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full();ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();inv=rest['WPN_root']@row['WPN_root'].inverted()
points=[];labels=[]
for j,(i,cat) in enumerate(zip(ids,category)):
 if cat not in ('palm','fingers') or j%7:continue
 points.append(inv@me.vertices[i].co);labels.append(gn[max(skin.data.vertices[i].groups,key=lambda g:g.weight).group])
ob.to_mesh_clear();rays=[Vector((1,.073,.047)).normalized(),Vector((.031,1,.051)).normalized(),Vector((.047,.061,1)).normalized()]
def evaluate(delta,detail=False):
 distances=[]
 for p in points:
  v=p+Vector(delta);point,normal,_,dist=bv.find_nearest(v);inside=0
  if dist<.045:
   for direction in rays:
    hit,n,_,_=bv.ray_cast(v,direction)
    inside+=hit is not None and n.dot(direction)>0
  distances.append(dist*1000*(-1 if inside>=2 else 1))
 ds=np.array(distances);pen=np.maximum(-ds-.3,0);gaps={}
 for digit in ('index','middle','ring','pinky','thumb'):
  chosen=np.array([n.startswith(digit) and ('_02_' in n or '_03_' in n) for n in labels]);near=np.sort(abs(ds[chosen]))[:5];gaps[digit]=float(near.mean()) if len(near) else 0
 score=float(30*np.mean(pen**2)+8*pen.max()**2+.15*sum((g-1.2)**2 for g in gaps.values())+.003*(Vector(delta).length*1000)**2)
 return {'cost':score,'offset_m':list(delta),'max_pen_mm':float(pen.max()),'gaps_mm':gaps} if detail else score
best=(0,0,0);value=evaluate(best)
for x in (-.02,-.01,0,.01,.02):
 for y in (-.02,-.01,0,.01,.02):
  for z in (-.05,-.04,-.03,-.02,-.01,0):
   d=(x,y,z);c=evaluate(d)
   if c<value:best=d;value=c
for step in (.005,.002,.001):
 for repeat in range(2):
  for axis in range(3):
   for sign in (-1,1):
    d=list(best);d[axis]+=step*sign
    if abs(d[0])>.035 or abs(d[1])>.035 or not -.065<d[2]<.01:continue
    c=evaluate(d)
    if c<value:best=d;value=c
result=evaluate(best,True);(O/'grip_position_fit.json').write_text(json.dumps(result,indent=2));print('GRIP_POSITION',json.dumps(result),flush=True)
