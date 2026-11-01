from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
setup_render();folder=O/'Before';folder.mkdir(exist_ok=True)
report={}
for role in ('reload','reload_mag10'):
 rows=clips[role];report[role]={}
 for f in (10,16,20,24,30,35,38,40,44,48):
  row=rows[f];local={n:row[parents[n]].inverted()@row[n] for n in names if parents[n]}
  mh=rest['WPN_Magazine']@row['WPN_Magazine'].inverted()
  report[role][f]={'hand_mag_space':list(mh@row['hand_l'].translation),
   'fingers':{n:list((local_rest[n].to_quaternion().inverted()@local[n].to_quaternion()).to_euler()) for n in names if under(n,'hand_l') and n!='hand_l'}}
  if f in (16,24,35,40,44):show(row,folder/f'{role}_{f:03d}.png',extended=role.endswith('mag10'))
(O/'source_contact.json').write_text(json.dumps(report,indent=2))
print('M24_RELOAD_SOURCE_REVIEW_RENDERED',flush=True)
