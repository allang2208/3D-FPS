from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
results={}
for role,frames in [('fire',[0,7,10,12,16,24,29,35,40,43,46,49,52,55]),('cycle',[0,11,16,47,50,53,56,62]),('reload_empty',[59,64,95,98,101,104,110]),('reload_empty_mag10',[104,110]),('aim',[0])]:
 results[role]={}
 for f in frames:
  row=final[role][f];P=points(row)[::3];d=actual(row,P,True,{'M24_base','M24_cheekrest','M24_bolt','M24_boltrear','M24_MainScope_Lowpoly'})
  results[role][str(f)]={n:{'penetration_mm':float(max(0,-v.min())*1000),'points_over_1mm':int((v<-.001).sum()),'bones_over_3mm':sorted({names[b] for b in dominant[::3][v<-.003]})} for n,v in d.items() if v.min()<-.001}
  print('CONTACT',role,f,results[role][str(f)],flush=True)
motion={}
for role,rows in final.items():
 metrics={}
 for n in ('hand_r','lowerarm_r'):
  local=[(row['WPN_root'].inverted()@row[n]).translation for row in rows];steps=[(b-a).length*1000 for a,b in zip(local,local[1:])]
  metrics[n]={'max_step_mm':max(steps,default=0),'frame':1+int(np.argmax(steps)) if steps else 0}
 motion[role]=metrics
(OUT/'contact_record.json').write_text(json.dumps(results,indent=2));(OUT/'motion_record.json').write_text(json.dumps(motion,indent=2));print('SOURCE_CONTACT_RECORDED',flush=True)
