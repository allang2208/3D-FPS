import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
d=json.loads((O/'ports_before.json').read_text())
for key,row in d['weapons'].items():
    mesh=u.load_asset(row['mesh'])
    modifier=u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):raise RuntimeError('Cannot read mesh reference '+key)
    values={}
    for name in row['reference']:
        t=modifier.get_bone_transform(name,True)
        p,q,s=t.translation,t.rotation,t.scale3d
        values[name]={'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
    row['mesh_reference']=values
    print('CASING_MESH_REFERENCE',key,values['WPN_root']['p'],flush=True)
(O/'ports_before.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
