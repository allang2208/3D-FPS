"""Overlay saved variants on the current catalog without resetting later edits."""
import copy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def vec(p):return [p[0]*100,-p[1]*100,(p[2] if len(p)>2 else 0)*100]
def port(room,o):
    a=room['footprint'][o['edge']];b=room['footprint'][(o['edge']+1)%len(room['footprint'])]
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    return dict(id=o['id'],position=vec([a[0]+dx/length*o['center'],a[1]+dy/length*o['center'],0]),
        normal=[dy/length,dx/length,0],width=o['width']*100,height=o['height']*100)
def extend(catalog):
    receipt=read(ROOT/'Receipts/import.json')
    if receipt['stage']!='meshes_saved':raise RuntimeError('Variant imports must complete before registration')
    catalog=copy.deepcopy(catalog);objects=read(ROOT/'Authored/manifest.json')['objects']
    rooms=read(ROOT/'Config/rooms.json')['rooms'];mains=read(ROOT/'Config/main-rooms.json')
    by_recipe={r['id']:r for r in rooms};originals={m['id']:m for m in catalog['modules']}
    def parts(rid):
        result=[]
        for obj in objects:
            if obj['room']!=rid:continue
            p=dict(mesh=receipt['meshes'][obj['name']],position=[0,0,0],scale=[1,1,1],yaw=0,
                collision=obj['collision'],fluid=False,materials=[],assembly_role=obj['kind'])
            if obj['kind']=='Tiles' and rid in {r['id'] for r in mains}:
                p['surface_mesh_variants']=[p['mesh']]+[receipt['meshes']['SM_RS_'+rid+'_Skin'+str(v)+'_Tiles'] for v in (1,2)]
            result.append(p)
        return result
    modules=[]
    for r in mains:
        family=r['family_id'];m=copy.deepcopy(originals[family]);authored=parts(r['id'])
        kinds={p['assembly_role'] for p in authored}
        # Reuse unaffected pipes/fluids. Every changed architectural group is replaced.
        m['parts']=[p for p in m['parts'] if not any(p['mesh'].split('.')[0].endswith('_'+k) for k in kinds)]+authored
        m.update(id=r['id'],family_id=family,structural_variant=r['id'].removeprefix(family+'_'),
            dressing_parameters=r['dressing_parameters'],ports=[port(r,o) for o in r['openings']],
            anchors=[dict(role=a['role'],position=vec(a['at'])) for a in r['anchors']])
        points=[vec(p) for p in r['footprint']]
        m['min']=[min(p[0] for p in points)-18,min(p[1] for p in points)-18,-80]
        m['max']=[max(p[0] for p in points)+18,max(p[1] for p in points)+18,(r['height_m']+.25)*100]
        m['cells']=[dict(min=[f[0]*100-18,-f[3]*100-18,-80],max=[f[2]*100+18,-f[1]*100+18,m['max'][2]]) for f in r['floors']]
        for index,l in enumerate(r['lights']):
            p=l['at'][:];p[2]-=.085
            # The parent carries current lighting tuning; move the fixture and source together.
            m['lights'][index]['position']=vec(p)
        for s in m.get('side_sockets',[]):
            rid=r['id']+'_Side'+s['id'];side=by_recipe[rid]
            doorway=next(o for o in side['openings'] if o['id']=='side_'+s['id'])
            s.update(port(side,doorway));s['id']=doorway['id'].removeprefix('side_')
            s.update(variant=rid,replace_suffixes=['_Shell','_Tiles','_Frames'],parts=parts(rid))
        modules.append(m)
    ids={m['id'] for m in modules}
    catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+modules
    catalog['room_ids']=list(dict.fromkeys(catalog['room_ids']+[m['id'] for m in modules]))
    for m in catalog['modules']:
        if m['id'] in catalog['room_ids']:m.setdefault('family_id',m['id'])
    catalog.update(room_variation_version=3,strict_ports=True)
    return catalog
