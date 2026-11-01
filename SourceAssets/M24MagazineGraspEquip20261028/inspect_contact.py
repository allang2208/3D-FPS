from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'lib','exec'))
setup_render()
def smooth(a,b,x):
 w=max(0,min(1,(x-a)/(b-a)));return w*w*(3-2*w)
node=next(n for n in ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full')
exec(compile(ast.unparse(node),'morphs','exec'));morphs=morphs_full
folder=O/'Before';folder.mkdir(exist_ok=True)
report={'magazines':{},'contact':{}}
for name in ('M24_clip','M24_Magazine10'):
 ob=bpy.data.objects[name];p=np.array([list(v.co) for v in ob.data.vertices]);report['magazines'][name]={'min':p.min(0).tolist(),'max':p.max(0).tolist(),'matrix':[list(v) for v in ob.matrix_world],'modifiers':[(x.type,x.name) for x in ob.modifiers]}
for role in ('reload','reload_mag10'):
 report['contact'][role]={}
 for f in (16,21,24,32,38,40,44):
  row=clips[role][f];inv=rest['WPN_Magazine']@row['WPN_Magazine'].inverted()
  report['contact'][role][f]={n:list(inv@row[n].translation) for n in ('hand_l','index_01_l','index_03_l','thumb_01_l','thumb_03_l','pinky_01_l','pinky_03_l')}
  if role=='reload' and f in (24,38):
   for v in ('left','right','bottom'):show(row,folder/f'{role}_{f}_{v}.png',v)
report['rest']={n:[list(v) for v in m] for n,m in rest.items() if n.endswith('_l') or n.startswith('WPN')}
(O/'contact_before.json').write_text(json.dumps(report,indent=2))
print('CONTACT_INSPECTED',flush=True)
