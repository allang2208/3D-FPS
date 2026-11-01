from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
exec(compile((OUT/'field_contact.py').read_text(),'field_contact','exec'))
part=next(p for p in surfaces if p['name']=='M24_base');print('BODY_BONE',part['bone'],flush=True)
for label,row in [('old',clips['idle'][0]),('new',{n:Matrix(m) for n,m in json.loads((OUT/'grip_pose.json').read_text()).items()})]:
 P=points(row)[hm][::2]
 a=actual(row,P,False,{'M24_base'})['M24_base'];b=actual(row,P,True,{'M24_base'})['M24_base']
 print(label,float(a.min()),float(b.min()),float(np.mean(abs(a-b))),int((a<-.001).sum()),int((b<-.001).sum()),flush=True)
 print('ROOT',np.array(row['WPN_root']).tolist(),'BONE',np.array(row[part['bone']]).tolist(),flush=True)
