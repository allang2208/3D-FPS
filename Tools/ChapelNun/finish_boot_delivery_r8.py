"""Record completed saves without launching gameplay or a review renderer."""
from pathlib import Path
import json
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/BootFinishR8')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json')
if not saved.get('completed'):raise RuntimeError('The asset save batch has not completed')
report={'status':'saved_and_integrated','asset':saved['asset'],'authored_source':str(R/'NunBoots_R8.blend'),'authoring':read(R/'authored.json'),'surface_recipe':read(R/'surfaces.json'),'saved_assets':saved,'integration':'Current ChapelNun boot asset path retained; nun-only materials; final boot reimport follows R8','cpp_build_required':False,'runtime_tested':False,'preview_rendered':False}
(R/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('NUN_BOOT_R8_DELIVERED',len(saved['textures']),len(saved['materials']),saved['lod_count'])
