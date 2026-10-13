import json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
source=next(w for w in data['weapons'] if w['id']=='ue_m4a1')
start=text.rfind('{',0,text.index('"ue_super90"'));old,end=json.JSONDecoder().raw_decode(text[start:]);new=copy.deepcopy(old)
keys={'skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'}
descriptions={
    'skeleton':'双管上梁、镂空后架与橡胶抵肩垫，通过 SUPER90 专用连接杆安装。',
    'core_stock':'轻量化镂空托架配橡胶肩垫，前端通过连接杆接入原装接座。',
    'qr_performance':'宽贴腮面、镂空斜撑后架与橡胶肩垫，配有 SUPER90 专用连接杆。',
    'tactical_telescopic':'带贴腮面与伸缩套筒的战术枪托，通过连接杆与原装前端接座衔接。',
    'legendary_adjustable_tactical_stock':'连续贴腮面、镂空托架与宽橡胶肩垫，保留香槟色饰条和红色嵌片，以连接杆固定。'}
new['options']['stock']=[{'id':'false','name':'原厂枪托','description':'恢复 SUPER90 原厂肩托、尾垫和衔接结构。','effects':[],'stats':{}}]
for row in source['options']['stock']:
    if row['id'] not in keys:continue
    option=copy.deepcopy(row)
    option['description']=descriptions[row['id']]
    new['options']['stock'].append(option)
if 'stock' not in new['allowed']:new['allowed'].append('stock')
indent=len(text[text.rfind('\n',0,start)+1:start]);replacement=json.dumps(new,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_bytes(path.read_bytes())
path.write_text(text[:start]+replacement+text[start+end:],encoding='utf-8')
(O/'catalog_integration.json').write_text(json.dumps({'weapon':'ue_super90','slot':'stock','options':new['options']['stock'],'source_weapon':'ue_m4a1','shared_option_icons':True,'existing_parts_save_schema':True,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SUPER90_COMMON_STOCK_CATALOG_SAVED')
