import json, struct, zipfile, hashlib
from pathlib import Path
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006')
with zipfile.ZipFile(O/'Original/source.zip') as z:
    dest=(O/'Original/Source').resolve()
    for member in z.infolist():
        if not (dest/member.filename).resolve().is_relative_to(dest): raise RuntimeError('Archive path escapes destination')
    z.extractall(dest)
raw=(O/'Original/glb.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n])
report={'asset':d.get('asset'),'materials':d.get('materials'),'meshes':d.get('meshes'),'skins':d.get('skins'),'nodes':d.get('nodes'),'animations':[]}
for a in d.get('animations',[]):
    times=[d['accessors'][s['input']] for s in a['samplers']]
    report['animations'].append({'name':a.get('name'),'duration':max(t.get('max',[0])[0] for t in times),'channels':len(a['channels']),'targets':sorted(set(d['nodes'][c['target']['node']].get('name','') for c in a['channels']))})
(O/'gltf_source_layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
meta=json.loads((O/'sketchfab_metadata.json').read_text(encoding='utf-8-sig'))
receipt={'source':'https://sketchfab.com/3d-models/fps-benelli-m4-animations-225a62190f6043ca975eaa2798ab7e2c','author':meta['user']['displayName'],'source_credits':meta['description'],'license':meta['license'],'download_method':'Official Sketchfab Download API','files':[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (O/'Original').iterdir() if p.is_file()],'credential_saved':False,'assets_imported':False,'runtime_tested':False}
(O/'acquisition_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'meshes':[m.get('name') for m in d.get('meshes',[])],'materials':[m.get('name') for m in d.get('materials',[])],'skins':[{'name':s.get('name'),'joints':len(s['joints'])} for s in d.get('skins',[])],'animations':report['animations']},indent=2))
