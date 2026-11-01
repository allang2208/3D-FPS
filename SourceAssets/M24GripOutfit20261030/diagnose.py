from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
from collections import Counter
folder=O/'Diagnosis';folder.mkdir(exist_ok=True)
base=pose('idle',0)[0];rt=base['WPN_root']@rest['WPN_root'].inverted()
out={'thumb':{},'advanced_bounds':[list(advanced_rest@Vector(c)) for c in advanced.bound_box]}
for n in ('hand_l','thumb_01_l','thumb_02_l','thumb_03_l','index_01_l','index_03_l','middle_03_l'):
    loc=base[parents[n]].inverted()@base[n]
    out['thumb'][n]={'position_in_source':list(rt.inverted()@base[n].translation),'basis_degrees':[math.degrees(x) for x in (local_rest[n].inverted()@loc).to_euler()]}
edges=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in skin.data.polygons for i in range(len(p.vertices)))
ids={i for e,c in edges.items() if c==1 for i in e}
boundary=[i for i in ids if (skin.data.vertices[i].co-rest['upperarm_r'].translation).length<.15]
out['opening_vertices']=boundary;out['inspect']=[]
path=next(p for p in roles if p.endswith('A_M24_inspect'));clip=roles[path];entry=next(x for x in ue['profiles']['base'] if x['base']==path)
for i in range(clip['keys']):
    t=i/clip['fps'];row,_=local_pose(clip,entry,t);set_pose(row)
    ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();points=[C@me.vertices[k].co for k in boundary];ev.to_mesh_clear()
    visible=[p for p in points if p.x>1 and abs(p.y)<p.x*math.tan(math.radians(37.5))*800/540 and abs(p.z)<p.x*math.tan(math.radians(37.5))]
    out['inspect'].append({'t':t,'visible_opening':len(visible),'shoulder_cm':list(C@row['upperarm_r'].translation),'hand_cm':list(C@row['hand_r'].translation)})
worst=sorted(out['inspect'],key=lambda x:x['visible_opening'],reverse=True)[0];out['worst']=worst
for t in sorted(set((0.,worst['t'],1.,2.,3.))):
    row,_=local_pose(clip,entry,min(t,(clip['keys']-1)/clip['fps']));view(row,folder/('inspect_'+str(t)+'.png'))
view(base,folder/'thumb.png','thumb');view(base,folder/'idle.png')
(O/'diagnosis.json').write_text(json.dumps(out,indent=2));print('DIAGNOSIS',json.dumps({'thumb':out['thumb'],'bounds':out['advanced_bounds'],'worst':worst,'opening':len(boundary)}),flush=True)
