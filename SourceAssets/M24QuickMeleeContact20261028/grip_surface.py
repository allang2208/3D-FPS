from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'inspect.py').read_text().split("\nfolder=")[0],'inspect_setup','exec'))
edited={f:[{n:Matrix(m) for n,m in row.items()} for row in rows] for f,rows in json.loads((O/'final_poses.json').read_text()).items()}
tri=np.array([[gun.data.vertices[i].co[:] for i in t.vertices] for t in gun.data.loop_triangles],dtype=float)
def winding(points):
 out=[]
 for start in range(0,len(points),48):
  v=tri[None,:,:,:]-points[start:start+48,None,None,:];a,b,c=v[:,:,0],v[:,:,1],v[:,:,2];la=np.linalg.norm(a,axis=2);lb=np.linalg.norm(b,axis=2);lc=np.linalg.norm(c,axis=2)
  num=np.einsum('bti,bti->bt',a,np.cross(b,c));den=la*lb*lc+np.einsum('bti,bti->bt',a,b)*lc+np.einsum('bti,bti->bt',b,c)*la+np.einsum('bti,bti->bt',c,a)*lb
  out.extend(abs(np.arctan2(num,den).sum(axis=1)*2/(4*math.pi)))
 return np.array(out)
results=[]
for label,t in [('before',.25),('after',.07),('after',.1),('after',.14),('after',.25),('after',.55)]:
 row=pose('quick_melee',t)[0] if label=='before' else edited['base'][round(t*120)]
 r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full();ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();inv=rest['WPN_root']@row['WPN_root'].inverted()
 chosen=[(i,cat) for i,cat in zip(ids,category) if cat in ('fingers','palm','forearm')];points=np.array([inv@me.vertices[i].co for i,cat in chosen]);ob.to_mesh_clear()
 # Only the stock/grip corridor is relevant to this report.
 select=(points[:,1]<.12)&(points[:,1]>-.40)&(points[:,2]>-.10)&(points[:,2]<.16)&(abs(points[:,0])<.09);points=points[select];cats=np.array([cat for i,cat in chosen])[select]
 wn=winding(points);stats={}
 for cat in ('fingers','palm','forearm'):
  ds=[bv.find_nearest(Vector(p))[3]*1000 for p,w,c in zip(points,wn,cats) if c==cat and w>.6];stats[cat]={'inside_vertices':len(ds),'deeper_1mm':sum(d>1 for d in ds),'max_mm':max(ds,default=0)}
 if label=='after' and t==.25:
  bones=np.array([gn[max(skin.data.vertices[i].groups,key=lambda g:g.weight).group] for i,cat in chosen])[select]
  stats['by_bone']={n:int(((bones==n)&(wn>.6)).sum()) for n in sorted(set(bones)) if ((bones==n)&(wn>.6)).any()}
  (O/'club_joints.json').write_text(json.dumps({n:list(inv@m.translation) for n,m in row.items() if under(n,'hand_r')},indent=2))
 results.append({'label':label,'t':t,'winding_threshold':.6,'stock_surface':stats});print('SURFACE',json.dumps(results[-1]),flush=True)
 if label=='after' and t==.25:
  root=row['WPN_root']@rest['WPN_root'].inverted();target=root@Vector((0,-.115,.048))
  for label2,offset in [('bottom',(.08,-.08,-.24)),('left',(-.25,-.05,.02)),('right',(.25,-.05,.02))]:
   cam.location=target+root.to_3x3()@Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.24
   s.render.filepath=str(O/('ClubGrip_'+label2+'.png'));bpy.ops.render.render(write_still=True)
(O/'grip_surface.json').write_text(json.dumps(results,indent=2))
