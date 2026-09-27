"""Keep authored poses at their intended times on the native model's frame grid."""
import hashlib,json,math,shutil
from pathlib import Path
import unreal as u

P=Path(__file__).parent
ROOT=Path(u.Paths.project_dir()).resolve()
E=u.EditorAssetLibrary
receipt={'reason':'Use native animation data-model frames, not compressed sampling frames', 'saved':[]}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

def quat_lerp(a,b,t):
    d=sum(x*y for x,y in zip(a,b))
    if d<0:b=[-x for x in b]
    q=[x+(y-x)*t for x,y in zip(a,b)]
    n=math.sqrt(sum(x*x for x in q))
    return [x/n for x in q]

for variant in ('Standard','LongGrip'):
    for file in (P/variant).glob('*_keys.json'):
        data=json.loads(file.read_text())
        asset=u.load_asset(data['asset'])
        if data['asset'] in dirty:raise RuntimeError('Unsaved animation retained: '+data['asset'])
        model=asset.get_editor_property('data_model_interface')
        frames=model.get_number_of_frames()
        if frames==data['frames']:continue
        if E.get_metadata_tag(asset,'SwordIdle.Revision')!='SwordIdleClose20260926V1':
            raise RuntimeError('Animation ownership changed: '+data['asset'])
        disk=ROOT/'Content'/(data['asset'].removeprefix('/Game/')+'.uasset')
        original_hash=hashlib.sha256(disk.read_bytes()).hexdigest()
        before=P/'BeforeHandoffFix'/variant
        before.mkdir(parents=True,exist_ok=True)
        for source in (file,disk):
            dest=before/source.name
            if not dest.exists():shutil.copy2(source,dest)
        rows=[]
        for f in range(frames+1):
            x=f*data['frames']/frames
            lo=int(math.floor(x));hi=min(data['frames'],lo+1);t=x-lo
            a,b=data['samples'][lo],data['samples'][hi]
            row={'seconds':f*data['seconds']/frames,
                 'posture_weight':a['posture_weight']+(b['posture_weight']-a['posture_weight'])*t,
                 'offset_cm':[v+(w-v)*t for v,w in zip(a['offset_cm'],b['offset_cm'])], 'bones':{}}
            for n,ka in a['bones'].items():
                kb=b['bones'][n]
                row['bones'][n]={k:([v+(w-v)*t for v,w in zip(ka[k],kb[k])] if k!='q'
                                   else quat_lerp(ka[k],kb[k],t)) for k in ('p','q','s')}
            rows.append(row)
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=original_hash:
            raise RuntimeError('Animation changed during repair: '+data['asset'])
        controller=asset.get_editor_property('controller')
        controller.open_bracket('Align closer idle handoff keys with source frame rate',False)
        try:
            for n in data['edited_bones']:
                keys=[row['bones'][n] for row in rows]
                if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
                        [u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                    raise RuntimeError('Track update failed: '+n)
        finally:controller.close_bracket(False)
        old_frames=data['frames'];data['frames']=frames;data['samples']=rows
        data['source_grid_repair']='SwordIdleHandoff20260926'
        file.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        E.set_metadata_tag(asset,'SwordIdle.SourceGrid','SwordIdleHandoff20260926')
        task=u.AssetExportTask();task.object=asset;task.filename=str(file.with_name(file.stem.removesuffix('_keys')+'.fbx'))
        task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption()
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed')
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed')
        receipt['saved'].append({'asset':data['asset'],'old_frames':old_frames,'source_frames':frames,
                                 'key_source':str(file),'fbx':task.filename})
        (P/'source_grid_repair_receipt.json').write_text(json.dumps(receipt,indent=2))
        print('SWORD_SOURCE_GRID_REPAIRED',data['asset'],old_frames,frames,flush=True)
(P/'source_grid_repair_receipt.json').write_text(json.dumps(receipt,indent=2))
