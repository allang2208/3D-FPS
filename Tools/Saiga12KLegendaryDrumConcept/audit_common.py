"""User-requested read-only 12K common attachment integration inventory."""
import json,copy,re,datetime
from pathlib import Path
from PIL import Image
P=Path('D:/FPS3D/FPSGAME')
O=P/'SourceAssets/Saiga12KLegendaryDrumConcept20261018/Audit'
d=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
w=copy.deepcopy(next(w for w in d['weapons'] if w['id']=='ue_saiga12k'))
# Mirror GunsmithSystem::Initialize: common merge, then clone merged tactical
# options into the explicitly supported secondary mount.
for slot,options in d['common_options'].items():
    rows=w['options'].setdefault(slot,[])
    if w.get('inherit_common_options',True):
        rows.extend(o for o in options if o['id'] not in {r['id'] for r in rows})
w['options']['tactical_secondary']=copy.deepcopy(w['options']['tactical'])
expected=json.loads((P/'SourceAssets/Saiga12KCommon20261017/integration.json').read_text())['parts']
mesh_root='/Game/Weapons/Saiga12K/Detail20261018'
profile_root='/Game/Weapons/Saiga12K/Inspect20261018/Profiles'
grips={'vertical_foregrip':'vertical','tactical_vertical_foregrip':'tactical_vertical','canted_foregrip':'canted','prism_handstop':'prism','angled_foregrip':'angled'}
hooks={'optic':'Weapons/Saiga12KOpticVisual.cpp','muzzle':'Weapons/M4MuzzleVisual.cpp','underbarrel':'Weapons/M4HandstopVisual.cpp','stock':'Weapons/SkeletonStockVisual.cpp','reargrip':'Weapons/PhantomRearGripVisual.cpp','magazine':'Weapons/M4DrumVisual.cpp','tactical':'Weapons/TacticalDeviceComponent.cpp','tactical_secondary':'Weapons/TacticalDeviceComponent.cpp'}
icon_root=P/'Content/ColdSteelData/AttachmentIcons20260913';framed=icon_root/'FramedFirearms'
def package(path):return P/('Content'+path.split('.')[0].removeprefix('/Game')+'.uasset')
def icon(slot,id):
    slot='tactical' if slot=='tactical_secondary' else slot
    key=slot+'_'+id;weapon='ue_saiga12k_'+key
    shared=(framed/(key+'.png')).exists()
    use_frame=shared or (framed/(weapon+'.png')).exists() or (not (icon_root/(weapon+'.png')).exists() and (framed/(key+'.png')).exists())
    directory=framed if use_frame else icon_root
    result=directory/((key if shared else weapon if (directory/(weapon+'.png')).exists() else key)+'.png')
    valid=False;size=None
    if result.exists():
        with Image.open(result) as im:size=list(im.size);im.verify();valid=True
    return {'file':str(result),'present':result.exists(),'readable':valid,'size':size}
rows=[];findings=[];asset_paths=set();counts={}
for slot,options in w['options'].items():
    counts[slot]=len([x for x in options if x['id']!='false'])
    seen=set()
    for opt in options:
        id=opt['id']
        if id in seen:findings.append({'kind':'duplicate_id','slot':slot,'id':id})
        seen.add(id)
        if id=='false':continue
        paths=[];profile=None
        if slot=='magazine':paths=[mesh_root+'/SM_Saiga12K_Ext12'] if id=='saiga12k_ext12' else []
        elif slot in ('tactical','tactical_secondary'):paths=[mesh_root+'/Attachments/SM_Saiga12K_'+id+('_2' if slot.endswith('secondary') else '_1')]
        elif slot=='underbarrel':
            family=grips.get(id)
            if family:paths=[mesh_root+'/Attachments/SM_Saiga12K_'+family];profile=profile_root+'/DA_'+('vertical' if family=='tactical_vertical' else family)
        else:
            paths=[mesh_root+'/Attachments/SM_Saiga12K_'+id]
            if slot=='optic':
                paths.append(mesh_root+'/Attachments/SM_Saiga12K_OpticSeat_'+id)
                if id in ('thermal_scope','lpvo_1_6x'):paths.append(mesh_root+'/Attachments/SM_Saiga12K_'+('thermal_selector' if id=='thermal_scope' else 'lpvo_ring'))
        asset_paths.update(paths)
        assets=[{'path':p,'file_present':package(p).exists(),'bytes':package(p).stat().st_size if package(p).exists() else 0} for p in paths]
        ico=icon(slot,id)
        row={'slot':slot,'id':id,'name':opt['name'],'common':slot!='magazine','assets':assets,'icon':ico,'profile':profile,'profile_present':package(profile).exists() if profile else None,'runtime_source':'Source/FPSGAME/'+hooks[slot],'stats':opt['stats']}
        rows.append(row)
        if not paths or any(not a['file_present'] for a in assets):findings.append({'kind':'missing_model','slot':slot,'id':id})
        if not ico['readable']:findings.append({'kind':'missing_icon','slot':slot,'id':id})
        if profile and not package(profile).exists():findings.append({'kind':'missing_profile','slot':slot,'id':id})
        desc=opt.get('description','')
        if any(s in desc for s in ('M4','SUPER90')):findings.append({'kind':'inherited_host_copy','slot':slot,'id':id,'text':desc})
        if any(re.search(r'\d',e.get('text','')) and any(s in e.get('text','') for s in ('装填','换弹')) for e in opt.get('effects',[])):
            findings.append({'kind':'reload_effect_numeric_copy','slot':slot,'id':id,'effects':opt['effects']})
    for required in expected.get(slot,[]):
        if required not in seen:findings.append({'kind':'missing_common_option','slot':slot,'id':required})
profile_sources={}
for family in ('base','angled','vertical','canted','prism'):
    src=P/'SourceAssets/Saiga12KInspect20261018/Profiles'/('DA_'+family+'.json')
    value=json.loads(src.read_text());profile_sources[family]={'asset_present':package(profile_root+'/DA_'+family).exists(),'clips':len(value['clips']),'inspect':any(c['base'].endswith('_inspect') for c in value['clips'])}
stock=w['options']['magazine'];extension=next(o for o in stock if o['id']=='saiga12k_ext12')
result={'date':datetime.datetime.now().astimezone().isoformat(),'scope':'12K catalog merge, source routing, saved asset files, readable icon files, authoring profile source and save receipt; no live game test',
 'weapon':'ue_saiga12k','slot_counts':counts,'common_install_options':sum(counts.values())-counts['magazine'],'unique_common_ids':len({r['id'] for r in rows if r['common']}),
 'common_mesh_files':len({a['path'] for r in rows if r['common'] for a in r['assets']}),'factory_capacity':w['base']['mag_size'],'extended_capacity':w['base']['mag_size']+extension['stats']['mag_delta'],
 'legendary_drum_currently_implemented':any('drum' in o['id'] for o in stock),'profiles':profile_sources,'rows':rows,'findings':findings,'runtime_tested':False}
(O/'common-attachments.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','profiles')},ensure_ascii=False,indent=2))
