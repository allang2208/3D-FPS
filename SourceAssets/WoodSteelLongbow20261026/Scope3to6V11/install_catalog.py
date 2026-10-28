"""Publish only the saved Peakwatch special optic to the bow catalog."""
from pathlib import Path
from datetime import datetime
import json, os

P=Path(__file__).parent;ROOT=Path('D:/FPS3D/FPSGAME')
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save Peakwatch assets before publishing its recipe')
author=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
location=','.join(f'{v:.5f}' for v in author['ring_mount_cm'])
option={
 'id':'highland_peakwatch_3_6x','name':'观峰变倍镜','weapons':['bow_woodsteel'],
 'description':'高地长弓专属变倍镜，圆形镜片搭配望远镜式刻度调节环，提供 3–6 倍放大。',
 'appearance':'银钢薄框、旧黄铜滚花环与胡桃木饰片，细十字准星配下方参考刻线。',
 'special_effects':['变倍｜开镜时使用鼠标滚轮调节 3–6 倍放大，每格 0.5 倍。'],
 'visual':{
  'bow_part_slots':'riser,grip,string,arrow_rest,sight,sight_zoom,arrow',
  'bow_part_sight_mesh':receipt['saved']['SM_Highland_Peakwatch3to6'],
  'bow_part_sight_material':'','bow_part_sight_rods':0,'bow_part_sight_scale':1.0,
  'bow_part_sight_location_cm':'0,0,0','bow_part_sight_rotation_deg':'0,0,0',
  'bow_part_sight_zoom_mesh':receipt['saved']['SM_Highland_PeakwatchZoomRing'],
  'bow_part_sight_zoom_material':'','bow_part_sight_zoom_rods':0,'bow_part_sight_zoom_scale':1.0,
  'bow_part_sight_zoom_location_cm':location,'bow_part_sight_zoom_rotation_deg':'0,0,0',
  'bow_ads_sight_cm':location,'bow_ads_sight_distance_cm':author['eye_distance_cm'],
  'bow_scope_magnification':3.0,'bow_scope_min_magnification':3.0,'bow_scope_max_magnification':6.0,
  'bow_scope_ring_degrees_per_power':author['degrees_per_power']
 },
 'stats':{'ads_mult':1.25}
}
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json';raw=path.read_bytes();data=json.loads(raw)
column=next(c for c in data['columns'] if c['key']=='sight')
index=next((i for i,o in enumerate(column['options']) if o['id']==option['id']),None)
if index is None:column['options'].append(option)
else:column['options'][index]=option
new=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=P/('before-bow-gunsmith-'+stamp+'.json')
if new!=raw:
    backup.write_bytes(raw)
    temp=path.with_name(path.name+'.peakwatch.tmp');temp.write_bytes(new)
    if path.read_bytes()!=raw:raise RuntimeError('Preserving concurrent catalog edit')
    os.replace(temp,path)
result={'weapon':'bow_woodsteel','slot':'sight','tier':'Special','option':option,
        'asset_import':str(P/'import-receipt.json'),'backup':str(backup),'gameplay_tested':False,
        'saved_at':datetime.now().isoformat()}
(P/('catalog-receipt-'+stamp+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PEAKWATCH_CATALOG_INSTALLED',flush=True)
