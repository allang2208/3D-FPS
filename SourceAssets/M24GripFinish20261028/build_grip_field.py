from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
row=clips['idle'][0];part=next(p for p in surfaces if p['name']=='M24_base');inv=np.array(rest[part['bone']]@row[part['bone']].inverted());P=points(row)[hm];P=P@inv[:3,:3].T+inv[:3,3]
lo=P.min(0)-.035;hi=P.max(0)+.035;step=.003;shape=np.ceil((hi-lo)/step).astype(int)+1
grid=np.stack(np.meshgrid(*(np.arange(n)*step+l for n,l in zip(shape,lo)),indexing='ij'),axis=-1).reshape((-1,3));values=np.empty(len(grid))
print('FIELD_START',shape.tolist(),len(grid),flush=True)
for start in range(0,len(grid),2048):
 Q=grid[start:start+2048];inside=winding(Q,part['tri'])>.5
 values[start:start+len(Q)]=[part['bvh'].find_nearest(Vector(p))[3]*(-1 if yes else 1) for p,yes in zip(Q,inside)]
 if start%16384==0:print('FIELD',start,len(grid),flush=True)
np.savez_compressed(OUT/'stock_field.npz',lo=lo,step=step,shape=shape,values=values.reshape(shape));print('FIELD_SAVED',flush=True)
