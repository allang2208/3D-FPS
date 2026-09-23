"""Enable SVD stocks using the existing stock effects and save contract."""
import json,copy
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1];p=R/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');data=json.loads(text)
svd=next(w for w in data['weapons'] if w['id']=='ue_svd')
donor=next(w for w in data['weapons'] if w['id']=='ue_akm')
if 'stock' not in svd['allowed']:svd['allowed'].append('stock')
svd['options']['stock']=copy.deepcopy(donor['options']['stock'])
descriptions={
 'false':'恢复 SVD 原厂镂空肩托、贴腮板与尾垫，保留原厂后握把。',
 'skeleton':'镂空骨架枪托，通过 SVD 专用连接杆、机匣座和锁紧环装配。',
 'core_stock':'独立镂空枪托，安装于 SVD 专用后托连接杆，保留原厂后握把。',
 'qr_performance':'带贴腮面、镂空斜撑和橡胶肩垫的枪托，使用 SVD 专用连接杆。',
 'tactical_telescopic':'带伸缩套筒与锁止结构的战术枪托，通过 SVD 专用连接杆装配。'}
for item in svd['options']['stock']:
 item['description']=descriptions[item['id']]
 if item['id']=='false':item['name']='原厂镂空枪托'
for trait in svd.get('traits',[]):
 if trait.get('icon')=='neutral' and '改造' in trait.get('text',''):
  trait['text']='瞄具、枪口、枪管、战术挂件与前握把可改造；后托通过专用连接杆替换'
needle='"id": "ue_svd"';idpos=text.index(needle);start=text.rfind('{',0,idpos)
_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
before=O/'Before/gunsmith.json';before.parent.mkdir(exist_ok=True)
if not before.exists():before.write_text(text,encoding='utf-8')
encoded=json.dumps(svd,ensure_ascii=False,indent=2).splitlines()
new=text[:start]+encoded[0]+'\n'+'\n'.join('    '+line for line in encoded[1:])+text[end:]
p.write_text(new,encoding='utf-8')
(O/'catalog_change.json').write_text(json.dumps({'definition':'ue_svd','stock_options':[x['id'] for x in svd['options']['stock']],
 'stats_source':'existing AKM common stock options, unchanged','connector':'automatically included in replacement assembly',
 'factory_grip_retained':True,'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SVD_STOCK_CATALOG_SAVED')
