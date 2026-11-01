from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
skin.data.calc_loop_triangles()
P=np.array([v.co[:] for v in skin.data.vertices]);T=np.array([t.vertices[:] for t in skin.data.loop_triangles])
UV=np.array([[skin.data.uv_layers[0].data[l].uv[:] for l in t.loops] for t in skin.data.loop_triangles])
S=np.array([[d.co[:] for d in k.data] for k in skin.data.shape_keys.key_blocks])-P
np.savez_compressed(O/'corrective_source.npz',P=P*100,T=T,UV=UV,S=S*100)
def pq(m):
    q=m.to_quaternion();return [[x*100 for x in m.translation],[q.x,q.y,q.z,q.w]]
frames=[{'time':i/100,'pose':{n:pq(m) for n,m in sample_pose(i/100).items()}} for i in range(49)]
data={'bones':{n:{'index':i,'parent':names.index(parents[n]) if parents[n] else -1,'t':pq(rest[n])[0],'q':pq(rest[n])[1]} for i,n in enumerate(names)},
      'weights':[{skin.vertex_groups[g.group].name:g.weight for g in v.groups} for v in skin.data.vertices],
      'shapes':[k.name for k in skin.data.shape_keys.key_blocks],'frames':frames}
(O/'corrective_source.json').write_text(json.dumps(data))
print('BIPOD_ELBOW_SOURCE',len(P),len(frames),flush=True)
