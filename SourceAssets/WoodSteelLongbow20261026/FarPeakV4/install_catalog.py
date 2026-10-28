"""Add the accepted exclusive option while preserving every other current catalog field."""
from pathlib import Path
import json, os, datetime
P=Path(__file__).parent
root=Path('D:/FPS3D/FPSGAME')
receipt=json.loads((P/'import-receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Save formal assets before publishing their recipe')
path=root/'Content/ColdSteelData/bow-gunsmith.json';raw=path.read_bytes();data=json.loads(raw)
option={
    'id':'highland_far_peak','name':'远峰重弓体','weapons':['bow_woodsteel'],
    'description':'高地长弓专属重型弓体，厚实的弓臂与加固钢背组成完整轮廓。',
    'appearance':'加厚层压木芯贴合分段暗钢背，铜色束箍压住护片，弓根饰有三重山峰纹。',
    'visual':{'bow_part_riser_mesh':receipt['saved']['SK_HighlandLongbow_FarPeak'],
              'bow_part_riser_material':'','bow_part_riser_scale':1.0,
              'bow_flex_distribution':1.45,'bow_release_return_seconds':.04,
              'bow_release_ring_seconds':.20,'bow_feedback_scale':1.25},
    'stats':{'range_mult':1.30,'shot_damage_mult':1.25,
             'draw_speed_bonus':-.25,'stamina_mult':1.40,'charge_stamina_mult':1.40}}
column=next(c for c in data['columns'] if c['key']=='riser')
old=next((i for i,o in enumerate(column['options']) if o['id']==option['id']),None)
if old is None:column['options'].append(option)
else:column['options'][old]=option
new=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
if new!=raw:
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during edit; rerun the field edit')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')
    (P/('before-bow-gunsmith-'+stamp+'.json')).write_bytes(raw)
    temp=path.with_name(path.name+'.farpeak.tmp');temp.write_bytes(new);os.replace(temp,path)
result={'weapon':'bow_woodsteel','slot':'riser','option':option,'asset_import':str(P/'import-receipt.json'),
        'gameplay_tested':False,'saved_at':datetime.datetime.now().isoformat()}
(P/'catalog-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
design_path=P.parent/'HighlandV3/design.json';design=json.loads(design_path.read_text(encoding='utf-8'))
design['exclusive_part'].update(stage='integrated',runtime_integrated=True,balance_values=option['stats'],
                                option_id=option['id'],production_source=str(P/'HighlandLongbow_FarPeak_Production.blend'))
design['exclusive_part']['directions'].pop('critical_damage',None)
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FAR_PEAK_CATALOG_INSTALLED')
