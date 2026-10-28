"""Publish only the Cloudpiercer special body after its packages have been saved."""
from pathlib import Path
from datetime import datetime
import json, os

P=Path(__file__).parent
ROOT=Path('D:/FPS3D/FPSGAME')
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save Cloudpiercer assets before publishing their recipe')
option={
 'id':'highland_cloudpiercer','name':'穿云弓体','weapons':['bow_woodsteel'],
 'description':'高地长弓专属弓体，采用细长的反曲轮廓与一体式护脊。',
 'appearance':'深烟褐层压木衬着浅色边线，连续银钢双脊收束于菱纹护片。',
 'visual':{'bow_part_riser_mesh':receipt['saved']['SK_HighlandLongbow_Cloudpiercer'],
           'bow_part_riser_material':'','bow_part_riser_scale':1.0,
           'bow_flex_distribution':1.35,'bow_release_return_seconds':.038,
           'bow_release_ring_seconds':.19,'bow_feedback_scale':1.20},
 'stats':{'range_mult':1.45,'crit_damage_bonus':.75,'physical_damage_mult':1.10,
          'draw_speed_bonus':-.35,'stamina_mult':1.55,'charge_stamina_mult':1.55}
}
path=ROOT/'Content/ColdSteelData/bow-gunsmith.json';raw=path.read_bytes();data=json.loads(raw)
column=next(c for c in data['columns'] if c['key']=='riser')
index=next((i for i,o in enumerate(column['options']) if o['id']==option['id']),None)
if index is None:column['options'].append(option)
else:column['options'][index]=option
new=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup=P/('before-bow-gunsmith-'+stamp+'.json')
if new!=raw:
    backup.write_bytes(raw)
    temp=path.with_name(path.name+'.cloudpiercer.tmp');temp.write_bytes(new)
    if path.read_bytes()!=raw:raise RuntimeError('Preserving concurrent catalog edit')
    os.replace(temp,path)
result={'weapon':'bow_woodsteel','slot':'riser','tier':'Special','option':option,
        'asset_import':str(P/'import-receipt.json'),'backup':str(backup),
        'gameplay_tested':False,'saved_at':datetime.now().isoformat()}
(P/('catalog-receipt-'+stamp+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('CLOUDPIERCER_CATALOG_INSTALLED',flush=True)
