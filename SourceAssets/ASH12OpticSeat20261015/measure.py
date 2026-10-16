import bpy,numpy as np,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;R=json.loads((O/'capture.json').read_text());W=O/'Working';W.mkdir(exist_ok=True);out={}
bpy.context.preferences.filepaths.save_version=0
with (O/'Input/host.bin').open('rb') as f:
 h=json.loads(f.readline());p=np.fromfile(f,'<f4',h['vertices']*3).reshape(-1,3)*[.01,-.01,.01];t=np.fromfile(f,'<i4',h['triangles']*3).reshape(-1,3);m=np.fromfile(f,'<i4',h['triangles'])
# Current ASH rear sight frame, metres, +X muzzleward, +Z up.
hp=p
np.savez_compressed(W/'host.npz',p=hp,t=t,m=m)
for key,row in R['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['fbx'],use_custom_normals=True)
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];o=obs[0]
 if len(obs)!=1:raise RuntimeError((key,len(obs)))
 matrix=o.matrix_world.copy();nmat=matrix.to_3x3().inverted().transposed();norms=[tuple((nmat@n.vector).normalized()) for n in o.data.corner_normals]
 o.data.transform(matrix);o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.normals_split_custom_set(norms)
 for i,s in enumerate(row['slots']):o.data.materials[i]=bpy.data.materials.new(s['name'])
 o.name=key;p=np.array([v.co[:] for v in o.data.vertices]);o.data.calc_loop_triangles();t=np.array([f.vertices[:] for f in o.data.loop_triangles]);m=np.array([f.material_index for f in o.data.loop_triangles])
 def bounds(v):return [v.min(0).round(6).tolist(),v.max(0).round(6).tolist()]
 parents=np.arange(len(p))
 def find(v):
  while parents[v]!=v:parents[v]=parents[parents[v]];v=parents[v]
  return v
 for a,b,c in t:
  aa=find(a);parents[find(b)]=aa;parents[find(c)]=aa
 groups={}
 for i in range(len(p)):groups.setdefault(find(i),[]).append(i)
 entries=[]
 for ids in groups.values():
  if len(ids)<8:continue
  entries.append({'vertices':len(ids),'bounds':bounds(p[ids]),'materials':sorted(set(m[np.isin(t[:,0],ids)].tolist()))})
 z=p[t][:,:,2];cross=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]);area=np.linalg.norm(cross,axis=1)*.5;n=cross/(2*area[:,None]+1e-15)
 levels={}
 for i in np.flatnonzero((abs(n[:,2])>.96)&(z.mean(1)<.012)):
  k=round(float(z[i].mean()),4);levels[k]=levels.get(k,0)+float(area[i])
 out[key]={'bounds':bounds(p),'materials':{s['name']:bounds(p[np.unique(t[m==i])]) for i,s in enumerate(row['slots']) if np.any(m==i)},'components':sorted(entries,key=lambda a:-a['vertices']),'horizontal_levels_m2':sorted(levels.items(),key=lambda a:-a[1])[:22]}
 np.savez_compressed(W/(key+'.npz'),p=p,t=t,m=m)
 bpy.ops.wm.save_as_mainfile(filepath=str(W/(key+'.blend')))
 print('MEASURED',key,out[key]['materials'],out[key]['horizontal_levels_m2'][:10],flush=True)
(O/'measurements.json').write_text(json.dumps(out,indent=2))
