from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
node=next(n for n in ast.parse((O/'author.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='held_weight');exec(compile(ast.unparse(node),'mask','exec'))
out={}
for family in ('base','mag10'):
    reference_pose=pose('idle',0,family)[0];reference=reference_pose['WPN_root'].inverted()@reference_pose['hand_r'];out[family]={}
    for path,clip in roles.items():
        if not any(path.endswith('A_M24_'+r) for r in ('fire','aim_fire','cycle','equip','reload_empty')):continue
        entry=next((x for x in ue['profiles'][family] if x['base']==path),None)
        if not entry:continue
        samples=[]
        for i in range(clip['keys']):
            t=i/clip['fps'];row,_=local_pose(clip,entry,t);samples.append([t,held_weight(row,reference,t,path,'r')])
        out[family][path]=samples
(O/'right_contact_mask.json').write_text(json.dumps(out))
print('RIGHT_CONTACT_MASK',json.dumps({k:{p.split('.')[-1]:v[15:42:5] for p,v in data.items()} for k,data in out.items()}),flush=True)
