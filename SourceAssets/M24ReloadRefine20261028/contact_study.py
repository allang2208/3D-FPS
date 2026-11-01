from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
setup_render();folder=O/'Study';folder.mkdir(exist_ok=True)
row=clips['reload'][24];M=rest['WPN_Magazine']@row['WPN_Magazine'].inverted()
data={'objects':{},'hand':{},'rest_hand':{}}
for key in ('M24_clip','M24_Magazine10'):
 ob=bpy.data.objects.get(key)
 if ob:data['objects'][key]={'min':[min(v.co[i] for v in ob.data.vertices) for i in range(3)],'max':[max(v.co[i] for v in ob.data.vertices) for i in range(3)]}
for n in names:
 if under(n,'hand_l'):
  local=row[parents[n]].inverted()@row[n];delta=local_rest[n].inverted()@local
  data['hand'][n]={'position':list(M@row[n].translation),'rotation_degrees':[math.degrees(v) for v in delta.to_euler()]}
  data['rest_hand'][n]=[list(v) for v in local_rest[n]]
for f in (16,24,38,40):
 for view in ('right','bottom'):show(clips['reload'][f],folder/f'before_{f}_{view}.png',view)
(O/'contact_study.json').write_text(json.dumps(data,indent=2))
print('M24_RELOAD_STUDY_SAVED',flush=True)
