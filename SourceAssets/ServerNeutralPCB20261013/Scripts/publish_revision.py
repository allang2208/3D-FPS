"""Switch only the three requested item appearances; retain stats, grid and old assets."""
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
models=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
icons=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
imported=json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))
installed=json.loads((ROOT/'Receipts/installation.json').read_text('utf-8'))
if installed['stage']!='assets_installed' or icons['stage']!='icons_saved':raise RuntimeError('Finish production before publication')
art={a['id']:a for a in models['assets'].values()}
meshes={m['item_id']:m for m in imported['meshes']}
desc={
 'search_network_card':'设施服务器使用的双口网络扩展卡，白色电路板搭配银色屏蔽接口与散热片，黑色芯片和浅色丝印清晰可辨。接口与板材完整的模块具有回收价值。',
 'search_raid_controller':'设施存储服务器的阵列控制卡，黑色主板与缓存副板搭配银色散热片、白色标识和多组内部数据接口。成套模块负责组织存储设备，完整板卡较为珍贵。',
 'search_processor':'设施服务器的处理器模块，银色金属顶盖与黑色封装基板保留在防静电保护托中。接触面受到保护，完整封装使其具有较高回收价值。',
}
path=PROJECT/'Content/ColdSteelData/items.json';raw=path.read_text('utf-8-sig')
decoder=json.JSONDecoder();before={};after={}
for icon in icons['icons']:
    identifier=icon['id'];match=re.search(r'^  '+re.escape(json.dumps(identifier))+r':\s*',raw,re.M)
    if not match:raise RuntimeError('Missing requested item '+identifier)
    start=match.end();item,end=decoder.raw_decode(raw[start:]);before[identifier]=dict(item)
    item.update(world_mesh=meshes[identifier]['path'],ue_icon=icon['ue_icon'],icon=icon['ue_icon'],desc=desc[identifier])
    after[identifier]=dict(item)
    block=json.dumps(item,ensure_ascii=False,indent=2).replace('\n','\n  ')
    raw=raw[:start]+block+raw[start+end:]
path.write_text(raw,encoding='utf-8')
design_path=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
design=json.loads(design_path.read_text('utf-8'))
appearances={
 'search_network_card':'白色阻焊 PCB 与灰白板边，银色接口和散热片、黑色芯片、白色网口指示灯，无绿色表面。',
 'search_raid_controller':'石墨黑主 PCB 和缓存副板，银色金属散热片与数据接口，灰白丝印，无绿色表面。',
 'search_processor':'银色顶盖、黑色封装基板及保护托，灰白元件与丝印，无绿色表面。',
}
for item in design['items']:
    if item['id'] not in art:continue
    identifier=item['id'];model=art[identifier];old=dict(item['model'])
    previous=item.setdefault('previous_model_revisions',[])
    if not any(p.get('ue_mesh')==old.get('ue_mesh') for p in previous) and old.get('ue_mesh')!=meshes[identifier]['path']:previous.append(old)
    item.update(ue_icon=after[identifier]['ue_icon'],status='neutral_pcb_catalog_integrated',icon_orientation='upper_left_45')
    item['model'].update(appearance=appearances[identifier],status='neutral_pcb_assets_installed',
        dimensions_lwh_cm=model['dimensions'],actual_dimensions_cm=model['actual_dimensions_cm'],
        triangles_lod0=model['triangles_lod0'],texture_size=model['size'],
        source=str(Path(model['source']).relative_to(PROJECT)).replace('\\','/'),
        fbx=str(Path(model['fbx']).relative_to(PROJECT)).replace('\\','/'),
        glb=str(Path(model['glb']).relative_to(PROJECT)).replace('\\','/'),
        ue_mesh=meshes[identifier]['path'],ue_material=meshes[identifier]['material'])
design['delivery']['server_neutral_pcb']='Docs/Art/server-neutral-pcb-20261013.md'
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(stage='neutral_pcb_appearance_published',before=before,after=after,
    footprints_changed=False,rarities_changed=False,prices_changed=False,old_assets_preserved=True,
    runtime_tested=False,player_save_files_changed=False)
(ROOT/'Receipts/publication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('REFERENCE_APPEARANCE_PUBLISHED',list(after))
