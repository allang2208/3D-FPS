"""Archive the completed UE icon output with this model revision."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/SpecialDutyBackpack20261024';R=ROOT/'MeshyFitR1_20261024'
log=max(R.glob('export_icon-*.log'),key=lambda p:p.stat().st_mtime_ns)
if 'WeaponIconCatalog: COMPLETE failures=0' not in log.read_text(encoding='utf-8-sig',errors='replace'):
    raise RuntimeError('The latest icon export did not finish successfully')
icon=P/'Content/ColdSteelData/Icons/ue_special_duty_backpack.png';raw=icon.read_bytes()
archive=R/'Icon/ue_catalog_front.png';shutil.copy2(icon,archive)
receipt={'status':'exported','renderer':'ColdSteelWeaponIconCatalog / runtime equipment icon studio','view':'outward_front',
         'dimensions':list(struct.unpack('>II',raw[16:24])),'sha256':hashlib.sha256(raw).hexdigest(),
         'catalog_png':str(icon),'archive_png':str(archive),'commandlet_log':log.name,
         'texture_streaming_disabled_for_authoring_process_only':True,'runtime_tested':False}
(R/'Icon/exported.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=R/'published.json';data=json.loads(path.read_text(encoding='utf-8'));data.update(icon_export=receipt,icon_export_pending=False)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=ROOT/'design.json';data=json.loads(path.read_text(encoding='utf-8'));data.update(catalog_icon='MeshyFitR1_20261024/Icon/ue_catalog_front.png',catalog_icon_exported=True)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SPECIAL_DUTY_SLIM_ICON_SAVED',receipt['dimensions'],receipt['sha256'])
