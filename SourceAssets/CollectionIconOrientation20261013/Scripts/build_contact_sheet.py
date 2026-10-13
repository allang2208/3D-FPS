"""Lay out the installed icon PNGs in an HTML contact sheet, preserving their pixels."""
from pathlib import Path
import base64,html,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
OUT=ROOT/'Previews';OUT.mkdir(exist_ok=True)
latest=PROJECT/'SourceAssets/CollectionIconLayoutR2_20261013/Receipts/installation.json'
data=json.loads((latest if latest.exists() else ROOT/'Receipts/installation.json').read_text('utf-8'))
icons={entry['id']:entry for entry in data['icons']}
catalog=json.loads((PROJECT/'Content/ColdSteelData/items.json').read_text('utf-8-sig'))
groups=[('文件材料',[
    'search_usb_drive','search_archive_tape','search_encrypted_archive_case','search_certified_admin_archive']),
    ('检修材料',[
    'search_forging_alloy_blank','search_assembly_component_box','search_resin_adhesive','search_laminated_strip','search_precision_mechanism']),
    ('机房设备',[
    'search_ram_module','search_network_card','search_hard_disk','search_ssd','search_processor','search_graphics_card','search_raid_controller','search_compute_accelerator'])]
cards=[];sources=[]
for group,ids in groups:
    for identifier in ids:
        item=icons[identifier];path=PROJECT/'Content/ColdSteelData'/catalog[identifier]['ue_icon']
        with Image.open(path) as icon:
            w,h=icon.size;box=icon.getchannel('A').getbbox() or (0,0,w,h)
        left,top,right,bottom=box
        # The SVG viewport trims empty canvas margins only; object pixels are unchanged.
        pad=max(right-left,bottom-top)*.075
        viewport=f'{left-pad} {top-pad} {right-left+pad*2} {bottom-top+pad*2}'
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        layout=item['orientation']['mode']
        upright=layout in ('vertical','vertical_centered')
        mode={'horizontal_centered':'水平居中','vertical_centered':'垂直居中','standard_inventory':'标准构图'}.get(layout,'垂直' if upright else '左上 45°')
        grid_w=catalog[identifier].get('grid_w',item['grid_w']);grid_h=catalog[identifier].get('grid_h',item['grid_h'])
        index=len(cards)+1
        cards.append(f'''<article class="card">
          <div class="card-top"><span class="number">{index:02}</span><span>{group}</span><span class="direction {'vertical' if upright else ''}">{mode}</span></div>
          <div class="art"><svg viewBox="{viewport}" preserveAspectRatio="xMidYMid meet" aria-label="{html.escape(item['name'])}"><image href="data:image/png;base64,{encoded}" width="{w}" height="{h}"/></svg></div>
          <div class="caption"><span>{html.escape(item['name'])}</span><span class="grid">{grid_w} × {grid_h}</span></div>
        </article>''')
        sources.append(dict(id=identifier,path=str(path),alpha_bounds=box,orientation=mode))
cards.append('''<aside class="legend"><div class="legend-title">居中布局 · 实际图标</div>
  <div class="legend-rules"><span><b>↔</b> 横向条状物</span><span><b>↕</b> 竖向条状物</span></div>
  <p>名称旁标注背包占格。图片等比展示，不代表物品之间的实际尺寸。</p>
  <p class="muted">来源：已安装的游戏 PNG 图标</p></aside>''')
document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>17件收集物 · 统一朝向预览</title>
<style>
*{box-sizing:border-box}html,body{margin:0}body{background:#161b21;color:#e9edf1;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif}
.sheet{width:2000px;padding:44px 44px 34px}.header{height:124px;display:flex;align-items:flex-start;justify-content:space-between}.eyebrow{font-size:15px;letter-spacing:3px;color:#a6b4c2;margin-bottom:10px}h1{font-size:38px;line-height:1.3;font-weight:600;margin:0}.subtitle{font-size:17px;color:#aab6c3;margin-top:12px}.badge{margin-top:18px;border:1px solid #4b5867;border-radius:24px;padding:12px 22px;font-size:18px;color:#d4e0ea}
.gallery{display:grid;grid-template-columns:repeat(5,1fr);gap:18px}.card{height:397px;background:#303740;border:1px solid #4b555f;border-radius:12px;overflow:hidden}.card-top{height:44px;padding:0 15px;display:flex;gap:10px;align-items:center;font-size:15px;color:#bdc8d1;background:#2b323a}.number{color:#8293a1;font-variant-numeric:tabular-nums}.direction{margin-left:auto;font-size:13px;color:#b8ccd8}.direction.vertical{color:#d9c39a}.art{height:290px;padding:10px 16px;background:radial-gradient(ellipse at 45% 38%,#46505b 0%,#343d47 72%,#303740 100%)}svg{width:100%;height:100%;display:block}.caption{height:62px;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:0 16px;background:#29313a;font-size:20px;white-space:nowrap}.grid{flex:none;font-size:16px;color:#aab9c6;border:1px solid #4b5865;border-radius:6px;padding:4px 7px;font-variant-numeric:tabular-nums}.legend{grid-column:span 3;height:397px;padding:47px 40px;background:#202831;border:1px solid #394754;border-radius:12px}.legend-title{font-size:28px;font-weight:600}.legend-rules{display:flex;gap:50px;font-size:24px;margin:26px 0 32px;align-items:center;color:#dce6ec}.legend-rules b{font-size:38px;font-weight:400;color:#b8cbd8;vertical-align:middle;margin-right:12px}.legend p{margin:12px 0;color:#b7c4cf;font-size:18px;line-height:1.6}.legend .muted{color:#8d9dab;font-size:16px}.footer{display:flex;justify-content:space-between;padding-top:22px;font-size:15px;color:#8d9ca9}
</style><main class="sheet"><header class="header"><div><div class="eyebrow">COLLECTION / ICON CONTACT SHEET</div><h1>17 件收集物 · 统一朝向预览</h1><div class="subtitle">文件材料 4 件 · 检修材料 5 件 · 机房设备 8 件</div></div><div class="badge">↖ 左上 45° &nbsp; / &nbsp; ↑ 竖向保持垂直</div></header><section class="gallery">'''+''.join(cards)+'''</section><footer class="footer"><span>COLD STEEL · 收集物图标</span><span>2026-10-13</span></footer></main></html>'''
document=document.replace('统一朝向预览','图标布局预览').replace('↖ 左上 45° &nbsp; / &nbsp; ↑ 竖向保持垂直','条状物居中 &nbsp; / &nbsp; 宽幅物品标准构图')
(OUT/'collection-icons-contact-sheet.html').write_text(document,encoding='utf-8')
(OUT/'contact-sheet-sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CONTACT_SHEET_LAYOUT_SAVED',len(sources),OUT)
