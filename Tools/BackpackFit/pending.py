"""Select new or changed clothing/pack pairs from actual saved inputs."""
import hashlib,json,os,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
REG=P/'Tools/BackpackFit/fit_registry.json'
def signatures(plan):
    cache={}
    def asset(path):
        if path not in cache:
            file=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
            cache[path]=hashlib.sha256(file.read_bytes()).hexdigest()
        return [path,cache[path]]
    result={}
    for row in plan['rows']:
        rig=plan['rigs'][row['rig']]
        inputs=[row['body'],*row.get('garment_surfaces',[]),*rig['pants']]
        if rig.get('head'):inputs.append(rig['head'])
        output={key:row.get(key) for key in ['mesh','rigid_mesh','rigid_location','rigid_rotation_quat','hanging_pack','explicit_mapping']}
        motion=row['outfit']['backpack_motion']
        output['motion']={k:v for k,v in motion.items() if k not in ['bounds_min','bounds_max','support_by_shirt']}
        if 'support' in motion:output['motion']['support']=motion.get('support_by_shirt',{}).get(row['shirt'],motion['support'])
        data={'inputs':[asset(path) for path in sorted(set(inputs))],'recipe':output,'saved_geometry':[asset(row['mesh'])]+([asset(row['rigid_mesh'])] if row.get('rigid_mesh') else [])}
        key='/'.join([row['rig'],row['item'],row['shirt'] or 'bare'])
        result[key]={'signature':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'sources':data['inputs']}
    return result
def main():
    runpy.run_path(str(P/'Tools/BackpackFit/prepare.py'),run_name='__main__')
    plan=read(R/'plan.json');current=signatures(plan);previous=read(REG).get('routes',{}) if REG.exists() else {}
    # A clothing item must provide a native source for each currently supported body.
    shirts=set().union(*(set(r['shirts']) for r in plan['rigs'].values()))
    missing=[rig+':'+shirt for rig,data in plan['rigs'].items() for shirt in shirts if shirt not in data['shirts']]
    if missing:raise RuntimeError('Create native shirt sources before backpack fitting: '+', '.join(missing))
    pending=[row for row in plan['rows'] if current['/'.join([row['rig'],row['item'],row['shirt'] or 'bare'])]['signature']!=previous.get('/'.join([row['rig'],row['item'],row['shirt'] or 'bare']),{}).get('signature')]
    (R/'full_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    # A local garment repair may regenerate just its affected pack combinations.
    # Preserve the male body as the existing surface-coordinate reference.
    selected_rig=os.environ.get('BACKPACK_FIT_RIG')
    selected_shirt=os.environ.get('BACKPACK_FIT_SHIRT')
    if selected_rig or selected_shirt:
        if selected_rig and selected_rig not in plan['rigs']:raise RuntimeError('Unknown backpack fit body: '+selected_rig)
        pending=[row for row in pending if (not selected_rig or row['rig']==selected_rig) and (not selected_shirt or row['shirt']==selected_shirt)]
        needed=set()
        active_rigs={row['rig'] for row in pending}
        plan['rigs']={key:value for key,value in plan['rigs'].items() if key in active_rigs or key=='Jason'}
        for rig,data in plan['rigs'].items():
            wanted={row['shirt'] for row in pending if row['rig']==rig}
            data['shirts']={key:value for key,value in data['shirts'].items() if key in wanted}
            data['shirt_surfaces']={key:value for key,value in data['shirt_surfaces'].items() if key in wanted}
            if rig not in active_rigs:
                data['pants']=[]
                data.pop('head',None)
            needed.update([data['body'],*data['pants']])
            if data.get('head'):needed.add(data['head'])
            for paths in data['shirt_surfaces'].values():needed.update(paths)
        for row in pending:
            needed.add(row['mesh'])
            if row.get('rigid_mesh'):needed.add(row['rigid_mesh'])
        plan['assets']=[row for row in plan['assets'] if row['path'] in needed]
    plan.update(rows=pending,include_gravity=True)
    (R/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (R/'pending.json').write_text(json.dumps({'count':len(pending),'routes':['/'.join([r['rig'],r['item'],r['shirt'] or 'bare']) for r in pending]},indent=2))
    print('BACKPACK_PENDING',len(pending),flush=True)
if __name__=='__main__':main()
