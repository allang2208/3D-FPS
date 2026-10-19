import json,html,datetime
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KLegendaryDrumConcept20261018'
r=json.loads((O/'Audit/common-attachments.json').read_text())
e=html.escape
labels={'optic':'瞄具','muzzle':'枪口','underbarrel':'前握把','stock':'枪托','reargrip':'后握把','magazine':'专属扩容弹匣','tactical':'战术挂件Ⅰ','tactical_secondary':'战术挂件Ⅱ'}
generation={'tool':'built-in image_gen','created':datetime.datetime.now().astimezone().isoformat(),'concept_name':'12k 大弹鼓','revision':'V02','status':'外观概念，未制作模型；未设定容量、数值或专属机制','reference':'Preview/12K_ThunderDrum_Concept_V01.png','output':'Preview/12k_Drum_Concept_V02.png','prompt_file':'design-prompt-v02.txt','prompt':(O/'design-prompt-v02.txt').read_text(),'orientation':'圆形端面朝枪口；鼓体轴线与枪管平行，整枪侧视显示鼓体窄侧面。','review':'按用户反馈修正装枪方向并统一名称；独立部件、正面、侧面和装枪外观同板展示。概念尺寸和接口不视为已完成模型装配。'}
(O/'generation.json').write_text(json.dumps(generation,ensure_ascii=False,indent=2),encoding='utf-8')
body=[]
for row in r['rows']:
    assets='齐' if row['assets'] and all(a['file_present'] for a in row['assets']) else '缺失'
    profile='已保存' if row['profile_present'] else '—'
    body.append('<tr>'+''.join('<td>'+e(str(x))+'</td>' for x in (labels[row['slot']],row['name'],row['id'],str(len(row['assets']))+' / '+assets,'可读取' if row['icon']['readable'] else '缺失',profile))+'</tr>')
issues=[]
for f in r['findings']:
    if f['kind']=='inherited_host_copy':issues.append('<li><b>'+e(f['id'])+'</b>：'+e(f['text'])+'</li>')
    elif f['kind']=='reload_effect_numeric_copy':issues.append('<li><b>saiga12k_ext12</b>：装填说明仍写“增加25%”。按现行文字规范，说明应使用定性措辞，具体倍率由属性详情显示。</li>')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>12K 通用改造核对与传说弹鼓概念</title><style>
body{max-width:1260px;margin:40px auto;padding:0 24px;background:#15181b;color:#e4e7e8;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}h1,h2{font-weight:650}h1{font-size:29px}h2{font-size:22px;margin-top:36px}p,li{color:#c7cdd0}a{color:#d6b87d}img{width:100%;border-radius:9px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #353a3e}th{color:#d6b87d}.note{padding:16px 20px;background:#23282d;border-left:3px solid #ad9361}.muted{color:#99a2aa}
</style><h1>12K：通用改造核对与传说大弹鼓设计</h1>
<p class="muted">2026-10-18 · 本轮未改动游戏资产、数值和目录，未启动 UE 或游戏。</p>
<div class="note">静态接入清单齐全：26 种通用件，对应 29 个安装选项，37 个配件及安装座网格；另有 12 发专属加长弹匣。仍有 4 条借用枪型的旧说明和 1 条扩容弹匣文案需收尾，不能将本次静态核对称为实机验收。</div>
<h2>12k 大弹鼓 · V02</h2>
<img src="Preview/12k_Drum_Concept_V02.png" alt="12k 大弹鼓：圆形端面朝前方的修订概念设计">
<p>传说专属改造。厚实单圆鼓、封闭分区圆形端盖、黑色枪钢与聚合物握持边，少量暗金嵌线和雷纹徽记。按用户反馈，圆形端面朝向枪口，鼓体轴线与枪管平行；装枪侧视显示鼓体窄侧面。上部轮廓衔接当前 12K，装枪图用于判断体量和扳机／握把周围空间。</p>
<p><b>仅外观概念：</b>尚未制作模型或换弹动作，也未写入弹匣容量、数值及传说专属效果。后续制作仍需按本枪弹匣挂点、完整包握和独立弹鼓换弹分支适配。</p>
<p>使用内置 image_gen 修订。<a href="design-prompt-v02.txt">本版完整提示词</a> · <a href="generation.json">生成记录</a></p>
<h2>核对范围与结果</h2>
<p>按现有 GunsmithSystem 的实际合并顺序补入热成像、赐福激光及第二侧战术挂件；逐项核对目录 ID、运行代码入口、正式网格文件、图标文件可读性和握姿配置。四类前握把的差量源均包含待机、开火、装备、普通／空仓换弹、冲刺、快速近战及检视；战术垂直握把使用垂直家族。原厂检视配置也已保存。</p>
<p>枪托、后握把和弹匣具有原厂部件隐藏／恢复入口；角色世界外观快照接续这些隐藏状态及附件。枪口散布、消音声、双侧战术装置、属性计算及保存均有现行代码入口。此处记录实现存在性，未执行安装／拆除、ADS、音效、换弹或联机运行验证，也未重新加载网格检查材质和骨骼。</p>
<table><thead><tr><th>槽位</th><th>改造件</th><th>ID</th><th>网格文件</th><th>图标</th><th>握姿配置</th></tr></thead><tbody>'''+''.join(body)+'''</tbody></table>
<h2>尚未收尾的说明</h2><ul>'''+''.join(issues)+'''</ul><p>上列属于文字残留，本轮只检查和出图，尚未修改。</p>
<p><a href="Audit/common-attachments.json">逐项核对 JSON</a></p></html>'''
(O/'Report.html').write_text(page,encoding='utf-8')
print('Saved concept and static attachment inventory:',O/'Report.html')
