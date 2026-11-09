from pathlib import Path
import pickle,json
r=Path(__file__).resolve().parent;post=pickle.load(open(r/'post_world.pkl','rb'));report={}
for family in ['base','vertical','canted','prism','angled']:
    rows=json.loads((r/('post_contacts_'+family+'.json')).read_text())
    if len(rows)!=2 or any(v['max_depth_cm']>.18 for v in rows.values()):raise RuntimeError('Contact refinement incomplete: '+family)
    post.update(pickle.load(open(r/('post_contacts_'+family+'.pkl'),'rb')))
    report[family]=rows
pickle.dump(post,open(r/'post_world.pkl','wb'))
(r/'settled_contacts.json').write_text(json.dumps(report,indent=2))
print('CONTACT25_SETTLE_MERGED',len(post),flush=True)
