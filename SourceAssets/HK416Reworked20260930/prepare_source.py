"""Preserve/extract the user source and record its public provenance."""
from pathlib import Path
import json,zipfile,hashlib,urllib.request
O=Path(__file__).parent;Z=Path(r'C:\Users\allan\Downloads\hk416-full-reworked.zip');D=O/'Original';D.mkdir(exist_ok=True)
with zipfile.ZipFile(Z) as archive:
    for member in archive.infolist():
        target=(D/member.filename).resolve()
        if not target.is_relative_to(D.resolve()):raise RuntimeError('Archive path escapes source folder')
        if not target.exists():archive.extract(member,D)
data={'archive':str(Z),'archive_sha256':hashlib.sha256(Z.read_bytes()).hexdigest(),
      'url':'https://sketchfab.com/3d-models/hk416-full-reworked-669a9ee17dc44580b53425a08c2f83d0',
      'model_uid':'669a9ee17dc44580b53425a08c2f83d0','user_provided_source':True}
try:
    req=urllib.request.Request('https://api.sketchfab.com/v3/models/'+data['model_uid'],headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=25) as response:meta=json.load(response)
    (O/'sketchfab_model.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    data.update(author=meta.get('user',{}).get('displayName'),license=meta.get('license'),title=meta.get('name'),description=meta.get('description'))
except Exception as error:data['page_fetch_error']=str(error)
(O/'provenance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False))
