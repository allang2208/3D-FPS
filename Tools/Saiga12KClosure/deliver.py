"""Write the delivery from saved receipts and actual UE captures."""
from pathlib import Path
import json,html,datetime
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018'
def read(path):return json.loads((O/path).read_text(encoding='utf-8-sig'))
source=read('Reports/source-check.json');saved=read('Reports/saved-assets-check.json');active=read('Reports/active-assets-check.json');activation=read('Receipts/activation.json');build=read('Receipts/build.json');catalog=read('Receipts/catalog.json')
assert saved['passed'] and active['passed'] and activation['complete'] and catalog['complete']
assert isinstance(build,list) and len(build)==2 and all(x['exit_code']==0 for x in build)
assert read('Preview/UE_Active.json')['complete']
receipt={'complete':True,'completed':datetime.datetime.now().isoformat(),'runtime_root':'/Game/Weapons/Saiga12K/Detail20261018','private_surface_root':'/Game/Weapons/Saiga12K/Closure20261018','saved_meshes':len(activation['updated']),'core_source_triangles':{k:v['triangles'] for k,v in source['models'].items()},'source_degenerate_free':source['degenerate_free'],'active_readback_passed':active['passed'],'arms_preserved':active['arm_contract_unchanged'],'correctives':active['correctives'],'actual_ue_views':['Hero','Foreend','Receiver','Opposite'],'gameplay_tested':False,'multiplayer_tested':False,'lighting_changed_in_gunsmith_only':True,'authored_geometry_backup':'SourceBefore/Content','source':'Authoring/Saiga12K_ClosedShell.blend'}
receipt['gunsmith_lighting']={'key':2.5,'fill':.65,'sky':.28,'softbox_scale':.55,'scene_lighting_unchanged':True}
receipt['build_evidence']={'successful_shared_builds_reused':True,'module_snapshot':'Receipts/isolated-host.json','logs':[r['source_build_log'] for r in build],'assets_saved_into_original_content':True}
(O/'Receipts/delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
pending=O/'Receipts/pending-delivery.json'
if pending.exists():
 old=json.loads(pending.read_text(encoding='utf-8-sig'));old['resolved']=True;old['superseded_by']='delivery.json';pending.write_text(json.dumps(old,indent=2),encoding='utf-8')
def figure(file,caption):return f'<figure><a href="Preview/{file}"><img src="Preview/{file}" alt="{html.escape(caption)}"></a><figcaption>{caption}</figcaption></figure>'
report='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>12K 实体表面修复</title><style>
body{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;color:#ddd;background:#14181d;margin:auto;max-width:1250px;padding:32px}h1,h2{color:#fff}p{max-width:1050px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;display:block}figure{margin:12px 0;background:#080b0d}figcaption{padding:12px}a{color:#b0cef1}table{border-collapse:collapse;width:100%}td,th{padding:10px;text-align:left;border-bottom:1px solid #38404a}.note{color:#b4becb}code{color:#bed4e5}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style>
<h1>Saiga 12K · 实体表面修复</h1><p>依据用户提供的游戏截图，重新追查 UE 实际渲染、模型面向、封闭拓扑、法线构建设置与母材输出。以下均为已保存资产的 UE 骨骼渲染，不是设计目标图或 Blender 替代预览。</p>
'''
report+=figure('UE_Active_Hero.png','正式运行路径的修复结果 · UE 离屏渲染')
report+='''<h2>查明的原因与修复</h2><table><tr><th>问题</th><th>处理</th></tr>
<tr><td>外表面在 UE 中背面剔除</td><td>修正 Blender → UE 坐标反射后多做了一次的角点反转；统一枪体、扩容件与本枪安装座的 UE 面向。没有用双面材质掩盖漏面。</td></tr>
<tr><td>壳体确有裂口与自交</td><td>缝合 T 型接缝，补机匣、枪托垫背面和弹匣壳结构边界；重建相互交叉的弹匣颈部筋条。枪口、抛壳口、供弹开口保留合理内壁，文字贴片的开放边界单独记录。</td></tr>
<tr><td>作者法线被构建步骤覆盖</td><td>关闭法线重算，保留加权法线与硬边；重建 Mikk 切线并使用完整 UV／高精度切线。重新烘焙枪体 4K、扩容件 2K 结构法线，绿色通道只在 UE 中翻转一次。</td></tr>
<tr><td>整面颗粒与金属发白</td><td>沿用 WS 母材，关闭颗粒、色斑、随机划痕和整面磨损；混合配件按原金属遮罩加入私有深色涂层，保留光学分划、镜片和单层湿润响应，并保护亮色文字与警示油墨。</td></tr>
<tr><td>预览强光抹平材质差异</td><td>12K 枪匠预览采用深色枪械灯光级别，降低大面积柔光反射。该调整仅影响枪匠展示，不改变场景光照或公共母材。</td></tr></table>
<h2>实际 UE 近景</h2><div class="grid">'''
report+=figure('UE_Active_Foreend.png','护木、导气组件及安装连接')+figure('UE_Active_Receiver.png','上盖、抛壳口内壁、操纵件和瞄具')+'</div>'
report+=figure('UE_Active_Opposite.png','反侧外壳与弹匣')
report+='''<h2>修复前证据</h2><p class="note">下图复现了用户截图中的护木消失与瞄具泛白。修复后同时改了表面与枪匠灯光，因此这不是仅材质参数的等光照对照。</p>'''+figure('UE_Before_Hero.png','修复前 · 相同 UE 骨骼渲染器、旧表面与旧布光')
report+=f'''<h2>保存与检查范围</h2><p>已更新 {len(activation['updated'])} 份正式网格：枪体、十二发扩容弹匣及 37 个通用配件／安装座。运行资产路径保持 Detail20261018；旧资产逐个备份，私有新材质与纹理存于 Closure20261018。</p>
<p>枪体 {active['saved_gun_triangles']:,} 个三角面，扩容件 {source['models']['ext12']['triangles']:,} 个三角面。结构开放边界和非流形问题已在作者网格中处理；近零几何与退化 UV 均为 0。37 个通用件的原始顶点指纹、三角面数和 LOD 数保持一致，生成 LOD 的包围盒允许正常重建差异。</p>
<p>手臂 {active['arm_triangles']:,} 个三角面、UV0–3、骨骼／权重与 {active['correctives']} 个矫正形状保持原合同。机械骨骼错绑为 {active['mechanical_bone_mismatches']}。Game／Editor 构建完成，目录图标已更新。</p>
<p class="note">为避免共享编译配置反复切换，本轮复用了已包含最终源码的成功 Game／Editor 构建，并保存日志、源码散列和模块快照。资产接入使用隔离的后台宿主，内容目录直接连接原工程；没有改写其他任务正在编译的模块。</p>
<p class="note">本轮完成的是模型、材质、保存读回和 UE 离屏外观检查。没有进行实机射击、换弹动作、性能或联机测试，用户仍需在实际使用场景中确认。</p>
<p class="note">部分借用的通用配件仍出现近零切线／副法线构建提示，本轮没有重做这些配件的全部拓扑。枪体及扩容弹匣的退化几何与 UV 检查为 0；黑色背景上的细小抖动点属于本次离屏图像的显示限制。</p>
<p><a href="Reports/active-assets-check.json">正式资产读回</a> · <a href="Reports/closure-author.json">封闭拓扑记录</a> · <a href="Receipts/delivery.json">交付回执</a></p></html>'''
(O/'Report.html').write_text(report,encoding='utf-8')
doc=P/'Docs/Weapons/saiga12k-integration-20261017.md';text=doc.read_text(encoding='utf-8-sig');marker='## UE 漏面实修与母材纠正 · 2026-10-18'
if marker not in text:
 text+='\n\n'+marker+'\n\n用户的实机截图推翻了前两轮仅凭离线几何预览作出的外观结论：UE 实际存在背面剔除、结构裂缝与法线重算。此前的 SurfaceRebuild／Detail 离线报告不能作为 UE 外观验收。\n\n本轮修正 Blender→UE 角点绕序，缝合结构开放边界，重建弹匣自交筋条，保留作者法线并重烘结构法线。母材仍使用 WS；混合配件使用私有金属区域涂层，保留光学与湿润分支。枪匠对本枪降低柔光强度，避免发白。\n\n正式网格路径保持 `/Game/Weapons/Saiga12K/Detail20261018`，共 39 份资产已更新；私有材质／纹理为 `Closure20261018`。原资产备份、作者源、脚本与真实 UE 对照保存在 `SourceAssets/Saiga12KClosure20261018` 和 `Tools/Saiga12KClosure`。实际报告为前者的 `Report.html`，完整回执为 `Receipts/delivery.json`。手臂、机械骨骼、全自动、圆弧准星及容量逻辑保持原合同。\n\n已按用户要求检查结构、材质、39 份保存资产与实际 UE 离屏外观；Game／Editor 已构建，目录图标已更新。未进行射击、换弹动作、帧时间或联机测试。\n'
 doc.write_text(text,encoding='utf-8-sig')
print('SAIGA_CLOSURE_DELIVERY_WRITTEN')
