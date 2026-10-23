"""Reuse the published native garment sources while UE's commandlet is busy."""
import json, shutil, hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ExpeditionBackpack20261022';out=R/'BodyInputs';out.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
outfits=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['items']
authored={
 'ue_field_sweater':P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021',
 'ue_chainmail_shirt':P/'SourceAssets/ChainmailTorsoRepair20261021'}
rows=[]
for key in ['body','ue_field_sweater_charcoal','ue_field_sweater','ue_chainmail_shirt','ue_blue_mage_robe','ue_st6_sleeves']:
    target=cfg['body_mesh'] if key=='body' else outfits[key]['rig_meshes']['Jason']
    if key in authored:
        root=authored[key];src=root/'Authored'/key/'Jason.json';data=json.loads(src.read_text())
        saved=json.loads((root/'saved_assets.json').read_text())['saved'][key+'/Jason']
        if saved['asset']!=target:raise RuntimeError('Fit source does not match current outfit '+key)
        data['source']=target
        bone_ids={name:b['index'] for name,b in data['bones'].items()}
        data['weights']=[[[bone_ids[name],weight] for name,weight in row.items()] for row in data['weights']]
        data['bones']=[{'name':name,'index':b['index'],'parent':b['parent']} for name,b in data['bones'].items()]
        data['materials']=[{'slot':name} for name in data['material_slots']]
        for field in ['uv','normals','colors']:data.pop(field,None)
    else:
        src=P/'SourceAssets/BackpackHarnessRebuild20261020/Inputs'/(key+'.json');data=json.loads(src.read_text())
        if data['source']!=target:raise RuntimeError('Cached native fit differs from current outfit '+key)
        asset=P/'Content'/(target.split('.')[0].removeprefix('/Game/')+'.uasset')
        if asset.stat().st_mtime>src.stat().st_mtime:raise RuntimeError('Native fit snapshot needs refreshing '+key)
    (out/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
    rows.append({'key':key,'asset':target,'fit_source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
(out/'manifest.json').write_text(json.dumps(rows,indent=2))
print('EXPEDITION_AUTHORING_INPUTS_READY',len(rows))
