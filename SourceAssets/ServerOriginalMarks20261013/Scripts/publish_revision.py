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
 'search_graphics_card':'设施计算中心拆出的三风扇图形扩展卡，银灰切面护罩包围黑色扇叶，金属鳍片与导热管组成完整散热模块。板卡与接口保存完整，适合作为高价值计算硬件带回。',
 'search_ram_module':'机房设备拆出的 DDR4 内存模块，黑色散热马甲覆盖存储颗粒，金色触点与定位缺口保留完整。金属外壳带有折边和开槽，可作为便携硬件收集品带回。',
 'search_ssd':'设施设备拆出的 M.2 NVMe 固态硬盘，窄长黑色板材上保留标签、存储颗粒与贴片元件。端部金手指、定位缺口和安装孔完整，是便于携带的存储硬件。',
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
 'search_graphics_card':'CS-G3 三风扇显卡：原创三轨标识，银灰切面护罩、凹入装配缝、曲面薄刃扇叶、垫圈、线束、鳍片与热管，独立 HDMI / DP 形状接口和供电卡扣。',
 'search_ram_module':'CS-D4 内存：原创三轨标识与 COLD STEEL 字样，黑色金属散热马甲、折边开槽及完整金手指。',
 'search_ssd':'CS-S2 M.2 SSD：原创三轨标识、COLD STEEL 标签与 CS 芯片丝印，黑色裸板、两侧贴片元件、M-key 缺口与半圆安装孔。',
}
for item in design['items']:
    if item['id'] not in art:continue
    identifier=item['id'];model=art[identifier];old=dict(item['model'])
    previous=item.setdefault('previous_model_revisions',[])
    if not any(p.get('ue_mesh')==old.get('ue_mesh') for p in previous) and old.get('ue_mesh')!=meshes[identifier]['path']:previous.append(old)
    item.update(ue_icon=after[identifier]['ue_icon'],status='original_marks_catalog_integrated')
    item['model'].update(appearance=appearances[identifier],status='original_marks_assets_installed',
        dimensions_lwh_cm=model['dimensions'],actual_dimensions_cm=model['actual_dimensions_cm'],
        triangles_lod0=model['triangles_lod0'],texture_size=model['size'],
        source=str(Path(model['source']).relative_to(PROJECT)).replace('\\','/'),
        fbx=str(Path(model['fbx']).relative_to(PROJECT)).replace('\\','/'),
        glb=str(Path(model['glb']).relative_to(PROJECT)).replace('\\','/'),
        ue_mesh=meshes[identifier]['path'],ue_material=meshes[identifier]['material'])
design['delivery']['server_original_marks']='Docs/Art/server-original-marks-20261013.md'
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(stage='original_marks_appearance_published',before=before,after=after,
    footprints_changed=False,rarities_changed=False,prices_changed=False,old_assets_preserved=True,
    runtime_tested=False,player_save_files_changed=False)
(ROOT/'Receipts/publication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('REFERENCE_APPEARANCE_PUBLISHED',list(after))
