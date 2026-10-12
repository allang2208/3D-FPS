"""Read the actual saved grip packages and compare the authored pose payloads."""
import unreal as u,json,gzip,array,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
with gzip.open(O/'profiles_after.json.gz','rt',encoding='utf-8') as f:authored=json.load(f)
report={'profiles':{},'meshes':{},'runtime_tested':False}
for family,expected in authored.items():
    obj=u.load_asset(expected['path']);actual=obj.get_editor_property('clips')
    assert len(actual)==len(expected['clips'])
    for a,b in zip(actual,expected['clips']):
        assert a.get_editor_property('base').get_path_name()==b['base']
        assert abs(a.get_editor_property('duration')-b['duration'])<1e-5
        tracks=a.get_editor_property('tracks');assert len(tracks)==len(b['tracks'])
        for x,y in zip(tracks,b['tracks']):
            assert str(x.get_editor_property('bone'))==y['bone']
            for field in ('times','values'):assert array.array('f',x.get_editor_property(field))==array.array('f',y[field]),(family,y['bone'],field)
    report['profiles'][family]={'clips':len(actual),'saved_payload_matches':True}
for family in ('vertical','tactical_vertical','canted','prism','angled'):
    path='/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_'+family;obj=u.load_asset(path)
    assert obj
    report['meshes'][family]={'path':path,'material_slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in obj.static_materials]}
receipt=json.loads((O/'import_receipt.json').read_text())
report['packages_match_saved_hashes']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==s for p,s in receipt['saved_sha256'].items())
assert report['packages_match_saved_hashes']
(O/'saved_readback.json').write_text(json.dumps(report,indent=2))
print('SUPER90_GRIP_SAVED_READBACK_OK',flush=True)
