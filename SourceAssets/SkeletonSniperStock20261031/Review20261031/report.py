import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
root=O.parents[2]
d=json.loads((root/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
catalog={}
def find_options(obj):
 if isinstance(obj,dict):
  if obj.get('id')=='sniper_skeleton_stock':yield obj
  for v in obj.values():yield from find_options(v)
 elif isinstance(obj,list):
  for v in obj:yield from find_options(v)
for w in d['weapons']:
 if w['id'] in ('ue_m24','ue_svd','ue_svch'):
  catalog[w['id']]={'stock_category_allowed':'stock' in w['allowed'],'options':list(find_options(w))}
(O/'catalog_receipt.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
canvas=Image.new('RGB',(1500,990),(28,31,35));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
draw.text((20,12),'SAVED UE ASSETS - STOCK FIT REVIEW',font=font,fill='white')
draw.text((20,52),'Receiver: grey | Stock: cyan | Adapter: gold | Bind-pose assembly',font=small,fill=(210,216,220))
for i,k in enumerate(('M24','SVD','SVCH')):
 y=90+i*298
 full=Image.open(O/(k+'_assembled.png')).convert('RGB').crop((0,135,1100,475)).resize((900,278))
 seam=Image.open(O/(k+'_seam_right.png')).convert('RGB').resize((556,278))
 canvas.paste(full,(15,y));canvas.paste(seam,(930,y));draw.text((30,y+5),k,font=font,fill=(20,25,30))
canvas.save(O/'stock_fit_review.png')
report={
 'scope':['M24','SVD','SVCH'],
 'mode':'read-only saved asset extraction, runtime mount formula reconstruction, offline geometry rendering, source entry-point review',
 'catalog':catalog,
 'geometry':json.loads((O/'connection_contacts.json').read_text()),
 'results':{
  'M24':'Dedicated saved mesh; native rear stock section exists; retained grip boundary meets transition adapter; adapter intersects stock nose.',
  'SVD':'Dedicated saved mesh; native factory stock section exists; retained grip boundary meets adapter; adapter intersects stock nose.',
  'SVCH':'Dedicated saved mesh; native KVInhibitor_stock section exists; adapter and stock nose overlap inside receiver rear, not floating.'},
 'source_routes_reviewed':['first person SetGunsmithStock','factory section restore branch','workbench standalone and live preview','inventory icon preloads and assembly','world pickup assembly','third-person equipment section mask and child part snapshot'],
 'gameplay_tested':False,'network_session_tested':False,'production_assets_modified':False,
 'diagnostic_helper_note':'Legacy ValidateStockAttachment only detects FactoryStock naming, not KVInhibitor_stock; it is called by the old M4/AKM stock audit, not the current visual integration.'}
(O/'review_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(catalog,ensure_ascii=True))
