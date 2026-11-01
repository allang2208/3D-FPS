from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
for label,row in [('old',clips['idle'][0]),('new',{n:Matrix(m) for n,m in json.loads((OUT/'grip_pose.json').read_text()).items()})]:
 P=points(row);d=actual(row,P,True,{'M24_base'})['M24_base']
 for prefix in ('hand','thumb','index','middle','ring','pinky'):
  mask=(dominant==ids['hand_r']) if prefix=='hand' else digit_masks[prefix]
  a=d[mask]*1000;print(label,prefix,np.percentile(a,[0,5,25,50,75]).tolist(),int((a<-1).sum()),flush=True)
