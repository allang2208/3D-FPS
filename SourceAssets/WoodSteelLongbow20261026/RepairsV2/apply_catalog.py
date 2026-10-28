"""Patch only this bow's framing and two grip materials in the latest catalogs."""
from pathlib import Path
import json,os,datetime
R=Path(__file__).parent;P=R.parent
if not json.loads((R/'import-receipt.json').read_text()).get('complete'):raise RuntimeError('Save repaired assets before activation')
manifest=json.loads((P/'authoring.json').read_text())
root=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData')
backup=R/('Before-Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
saved=[]
def edit(name,mutate):
    path=root/(name+'.json');raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    mutate(data)
    output=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    if output==raw:return
    if raw!=path.read_bytes():raise RuntimeError('Catalog changed during targeted patch '+name)
    (backup/path.name).write_bytes(raw)
    temp=path.with_suffix('.woodsteel-repair.tmp');temp.write_bytes(output);os.replace(temp,path);saved.append(str(path))
def bow(data):
    w=data['bow_woodsteel'];w['bow_ads_rest_cm']='63,10,-12'
    w['bow_presentation_revision']=max(36,w.get('bow_presentation_revision',0))
def parts(data):
    w=next(x for x in data['weapons'] if x['id']=='bow_woodsteel')['part_overrides']
    for key in ('false','no_sight'):w['sight'][key]['visual']['bow_ads_rest_cm']='63,10,-12'
    for key in ('bow_clearfield_2x','bow_farwatch_4x'):
        v=w['sight'][key]['visual'];v['bow_ads_sight_cm']=','.join(f'{n:g}' for n in manifest['optic_aim_center_cm'])
        v['bow_ads_sight_distance_cm']=manifest['optic_eye_distance_cm']
    for key,finish,appearance in [('waxed_linen','WaxedLinen','深棕蜡麻包面，纤维细纹沿原有缠绕结构延伸。'),('woven_linen_grip','Linen','暖棕麻布包面，交错织纹覆盖原有缠绕结构。')]:
        name='M_WoodSteelLongbow_'+finish+'_Static'
        w['grip'][key]['visual']['bow_part_grip_material']='/Game/Weapons/WoodSteelLongbow20261026/'+name+'.'+name
        w['grip'][key]['appearance']=appearance
edit('bows',bow);edit('bow-gunsmith',parts)
(R/'catalog-receipt.json').write_text(json.dumps({'saved':saved,'backup':str(backup),'revision':36,'gameplay_tested':False},indent=2),encoding='utf8')
print('WOODSTEEL_REPAIR_CATALOG_SAVED')
