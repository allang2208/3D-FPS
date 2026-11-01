from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
ix=np.where(dominant==names.index('ring_03_r'))[0][::3];out={}
for f in (23,28):
 src=final['fire'][f];out[str(f)]={}
 for deg in (-10,0,10,20,30,45):
  row={n:m.copy() for n,m in src.items()};n='ring_03_r';loc=row[parents[n]].inverted()@row[n]
  q=local_rest[n].to_quaternion()@Quaternion((0,0,1),math.radians(deg))
  row[n]=row[parents[n]]@Matrix.LocRotScale(loc.translation,q,loc.to_scale())
  ds=actual(row,points(row)[ix],True)
  out[str(f)][str(deg)]={p:round(float(d.min())*1000,3) for p,d in ds.items() if d.min()<.004}
(OUT/'ring_flex_probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
