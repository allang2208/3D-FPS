from pathlib import Path
exec(compile((Path(__file__).parent/'author_root.py').read_text().split('patch={};report=')[0],'author','exec'))
skin.data.calc_loop_triangles();P=np.array([v.co[:] for v in skin.data.vertices]);T=np.array([t.vertices[:] for t in skin.data.loop_triangles]);UV=np.array([[skin.data.uv_layers[0].data[l].uv[:] for l in t.loops] for t in skin.data.loop_triangles])
S=np.array([[d.co[:] for d in k.data] for k in skin.data.shape_keys.key_blocks])-P
np.savez_compressed(O/'corrective_source.npz',P=P*100,T=T,UV=UV,S=S*100)
def pq(m):
 q=m.to_quaternion();return [[x*100 for x in m.translation],[q.x,q.y,q.z,q.w]]
def poserow(row):return {n:pq(m) for n,m in row.items()}
frames=[]
for role,data in ue['clips'].items():
 family='mag10' if role.endswith('_mag10') else 'base';changed=role in ('fire','cycle','reload_empty','reload_empty_mag10');step=2 if changed else 1
 for i in range((data['keys']-1)*step+1):
  t=i/(data['fps']*step);row=corrected(role,t,family) if changed else component(local_pose(role,t,family))
  frames.append({'role':role,'time':t,'pose':poserow(row)})
for i in range(121):
 for phase in (0,.25,.5,.75):frames.append({'role':'runtime_raise','progress':i/120,'phase':phase,'pose':poserow(runtime(i/120,phase))})
for i in range(121):frames.append({'role':'runtime_loop','progress':1,'phase':i/120,'pose':poserow(runtime(1,i/120))})
jsondata={'bones':{n:{'index':i,'parent':names.index(parents[n]) if parents[n] else -1,'t':pq(rest[n])[0],'q':pq(rest[n])[1]} for i,n in enumerate(names)},'weights':[{skin.vertex_groups[g.group].name:g.weight for g in v.groups} for v in skin.data.vertices],'shapes':[k.name for k in skin.data.shape_keys.key_blocks],'frames':frames}
(O/'corrective_source.json').write_text(json.dumps(jsondata));print('CORRECTIVE_SOURCE',len(P),len(frames),flush=True)
