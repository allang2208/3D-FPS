exec(compile((__import__('pathlib').Path(__file__).parent/'inspect_grip.py').read_text(),__file__,'exec'))
results=[]
def check(shift,subset):
 maximum=0;count=0
 for original in subset:
  p=original+shift
  if not(result['mag_bounds'][1][0]<=p.y<=result['mag_bounds'][1][1] and result['mag_bounds'][2][0]<=p.z<=result['mag_bounds'][2][1]):continue
  left=tree.ray_cast(Vector((-.1,p.y,p.z)),Vector((1,0,0)),.2)[0];right=tree.ray_cast(Vector((.1,p.y,p.z)),Vector((-1,0,0)),.2)[0]
  if left is not None and right is not None and left.x<p.x<right.x:
   depth=min(p.x-left.x,right.x-p.x);maximum=max(maximum,depth)
   if depth>.0003:count+=1
 return maximum,count
for dx in [-.004,0,.004]:
 for dy in [-.004,0,.004]:
  for dz in [0,-.004,-.008,-.012,-.016,-.020,-.024]:
   shift=Vector((dx,dy,dz));deep,count=check(shift,points[::3]);results.append({'shift':list(shift),'depth_mm':deep*1000,'count':count,'cost':deep*1000*10+count*.05+shift.length*1000*.1})
results.sort(key=lambda x:x['cost']);best=results[0];best['full_depth_mm'],best['full_count']=check(Vector(best['shift']),points);best['full_depth_mm']*=1000
(O/'grip_fit.json').write_text(json.dumps({'best':best,'candidates':results[:5]},indent=2));print('GRIP_FIT',best)
