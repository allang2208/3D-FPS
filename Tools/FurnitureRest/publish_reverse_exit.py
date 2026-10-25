"""Update only the six exit camera tracks, matching the newly saved sequences."""
import json,os,runpy,uuid
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/ReversedExitV7'
receipt=json.loads((OUT/'assets_saved.json').read_text())
helper=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))
for filename,prefix in [('furniture_rest.json','Rest.Sofa'),('apartment_furniture_rest.json','Rest.ApartmentSofa')]:
    path=ROOT/'Content/ColdSteelData'/filename;before=path.read_bytes()
    original=json.loads(before.decode('utf-8-sig'));candidate=json.loads(before.decode('utf-8-sig'))
    update=json.loads((OUT/filename).read_text(encoding='utf-8'))
    owned=[]
    for role in receipt:
        if role.startswith(prefix):
            assert role.endswith('.Exit')
            candidate['clips'][role]=update['clips'][role];owned.append(('clips',role))
    edits=list(helper['_changes'](original,candidate));text=before.decode('utf-8-sig')
    for key,value in edits:
        if not any(key[:len(scope)]==scope for scope in owned):raise RuntimeError('Unowned camera change '+repr(key))
        text=helper['_set'](text,key,value)
    result=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    assert json.loads(result.decode('utf-8-sig'))==candidate
    with helper['_lock'](ROOT/'Saved/FurnitureRestConfigWrites/writer.lock'):
        if path.read_bytes()!=before:raise RuntimeError('Furniture config changed; retry from fresh input')
        backup=OUT/(filename+'.before.json')
        if not backup.exists():backup.write_bytes(before)
        temporary=path.with_name('.reverse-exit-'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_bytes(result)
            if path.read_bytes()!=before:raise RuntimeError('Furniture config changed during write')
            os.replace(temporary,path)
        finally:
            if temporary.exists():temporary.unlink()
    (OUT/(filename+'.applied.json')).write_text(json.dumps({'changed_paths':[list(k) for k,v in edits]},indent=2))
    print('EXIT_CAMERA_INSTALLED',filename)
