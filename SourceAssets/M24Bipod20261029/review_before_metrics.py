from pathlib import Path
m24_review_code=(Path(__file__).parent/'review_pose.py').read_text()
exec(compile(m24_review_code.split('metrics=[];')[0],'setup','exec'))
with gzip.open(O/'Review/Before/authored.json.gz','rt') as f:data=json.load(f)
rate=data['rate']
exec(compile('metrics=[];'+m24_review_code.split('metrics=[];')[1].split('s.render.resolution_x=720')[0],'metrics','exec'))
(O/'Review/Before/anatomy.json').write_text(json.dumps(metrics,indent=2))
print('ORIGINAL_WRIST',max(x['wrist_axis_degrees'] for x in metrics),flush=True)
