"""Read back only the two published M24 grip profiles."""
import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
patch=json.loads((O/'quick_melee_patch.json').read_text())
report={'saved_assets':[],'preserved_clips':{},'runtime_tested':False}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
    current=packed(p,family)
    before=json.loads((O/'Backups'/(family+'.json')).read_text())
    target=patch[family]['base'];retained=[]
    for clip in current['clips']:
        if clip['base']==target:
            # Native UE float serialization can differ from Python doubles.
            expected=patch[family]
            assert abs(clip['duration']-expected['duration'])<1e-6
            assert len(clip['tracks'])==len(expected['tracks'])
            for actual,wanted in zip(clip['tracks'],expected['tracks']):
                assert actual['bone']==wanted['bone']
                for key in ('times','values'):
                    assert len(actual[key])==len(wanted[key])
                    assert max(abs(a-b) for a,b in zip(actual[key],wanted[key]))<2e-6,(family,actual['bone'],key)
        else:
            assert clip==next(v for v in before['clips'] if v['base']==clip['base']),'Unrelated clip changed: '+clip['base']
            retained.append(clip['base'])
    assert len(current['clips'])==len(before['clips'])
    assert any(c['base']==target for c in current['clips'])
    file=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset')
    report['saved_assets'].append({'path':p.get_path_name(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    report['preserved_clips'][family]=retained
report['dirty_profiles']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().endswith(('DA_M24_SupportGrip','DA_M24_Mag10'))]
assert not report['dirty_profiles']
(O/'readback_receipt.json').write_text(json.dumps(report,indent=2))
print('M24_CLUB_GRIP_SAVED_READBACK',json.dumps({'saved_assets':report['saved_assets'],'preserved_clip_counts':{k:len(v) for k,v in report['preserved_clips'].items()}}),flush=True)
