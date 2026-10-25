"""Apply only saved sofa clips and slot variants to fresh shared configurations."""
import json, os, runpy, uuid
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/RelaxedSeatV5'
receipt=json.loads((OUT/'assets_saved.json').read_text())
helper=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))
for filename,prefix in [('furniture_rest.json','Sofa'),('apartment_furniture_rest.json','ApartmentSofa')]:
    path=ROOT/'Content/ColdSteelData'/filename
    before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'))
    update=json.loads((OUT/filename).read_text(encoding='utf-8'))
    owned=[]
    for role in receipt:
        if not role.startswith('Rest.'+prefix):continue
        candidate['clips'][role]=update['clips'][role];owned.append(('clips',role))
    for suffix in ('Left','Right'):
        kind=prefix+suffix
        candidate['types'][kind]=dict(candidate['types'][prefix]);owned.append(('types',kind))
    targets={p['mesh'] for p in update['furniture'] if p['slots'][0]['kind'].startswith(prefix)}
    # The text writer treats JSON arrays as one value. Build this value from
    # the fresh file, changing only the selected slots' kind fields below.
    owned.append(('furniture',))
    for i,row in enumerate(candidate['furniture']):
        if row['mesh'] not in targets:continue
        for j,slot in enumerate(row['slots']):
            slot['kind']=prefix+('Left' if slot['seat'][0]<0 else 'Right' if slot['seat'][0]>0 else '')
            owned.append(('furniture',i,'slots',j,'kind'))
    edits=list(helper['_changes'](json.loads(before.decode('utf-8-sig')),candidate))
    text=before.decode('utf-8-sig')
    for key,value in edits:
        if not any(key[:len(scope)]==scope for scope in owned):raise RuntimeError('Unowned change '+repr(key))
        text=helper['_set'](text,key,value)
    result=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    assert json.loads(result.decode('utf-8-sig'))==candidate
    with helper['_lock'](ROOT/'Saved/FurnitureRestConfigWrites/writer.lock'):
        if path.read_bytes()!=before:raise RuntimeError('Configuration changed; retry with fresh input')
        backup=OUT/(filename+'.before.json')
        if not backup.exists():backup.write_bytes(before)
        temporary=path.with_name('.relaxed-seat-'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_bytes(result)
            if path.read_bytes()!=before:raise RuntimeError('Configuration changed during write')
            os.replace(temporary,path)
        finally:
            if temporary.exists():temporary.unlink()
    (OUT/(filename+'.applied.json')).write_text(json.dumps({'changed_paths':[list(k) for k,v in edits]},indent=2))
    print('RELAXED_SEAT_CONFIG_INSTALLED',filename)
