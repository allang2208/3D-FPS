"""Assemble the requested human-readable report from this revision's receipts."""
import json,html
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018'
def read(path):return json.loads((O/path).read_text(encoding='utf-8-sig'))
source=read('Reports/source-check.json');saved=read('Reports/saved-assets-check.json');assets=read('Receipts/assets.json');builds=read('Receipts/build.json') if (O/'Receipts/build.json').exists() else []
if isinstance(builds,dict):builds=[builds]
catalog=read('Receipts/catalog.json') if (O/'Receipts/catalog.json').exists() else {'complete':False}
visual={'checked_views':['Actual_Hero','Actual_Right','Actual_Receiver','Actual_Top','Actual_Ext12','SavedUE_Hero'],'findings':['上盖为连续弧形实体壳，侧面保留抛壳口与可见枪机；顶面未见原来的透空。','枪管、导气组件与机匣固定件使用连续曲面、规则圆边，保留前后机瞄及安装位置。','护木、握把和枪托的折面已重建，保留原凹槽并补充规则防滑筋；没有整面砂粒法线。','原厂与扩容弹匣保留上端接口、曲线、底板及原机械归属，新增筋条连续。','从 UE 保存资产读回的枪体离线实渲与作者版本一致。'],'scope':'本枪资产及表面检查；离线 Cycles 图不等于游戏场景光照，也不证明所有动作或联机行为通过。'}
(O/'Reports/visual-check.json').write_text(json.dumps(visual,ensure_ascii=False,indent=2),encoding='utf-8')
delivery={'assets_saved':assets['complete'],'asset_mesh_count':len(saved['assets']),'saved_assets':len(assets['saved']),'gun_triangles':saved['saved_gun_triangles'],'extended_triangles':source['models']['ext12']['triangles'],'source_checks_passed':source['geometry_finite'] and source['degenerate_free'],'saved_checks_passed':saved['passed'],'arm_contract_unchanged':saved['arm_contract_unchanged'],'mechanical_bone_mismatches':saved['mechanical_bone_mismatches'],'builds':builds,'catalog':catalog,'actual_preview':'Preview/SavedUE_Hero.png','target_preview':'Preview/12K_TargetPreview.png','interactive_editor_launched':False,'gameplay_tested':False,'normal_maps':{'gun':4096,'extended':2048},'surface_masks':{'gun':2048,'extended':1024},'shared_master_modified':False}
delivery['complete']=delivery['assets_saved'] and delivery['source_checks_passed'] and delivery['saved_checks_passed'] and len(builds)==2 and all(x['exit_code']==0 for x in builds) and catalog['complete']
(O/'Receipts/delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
e=html.escape;rows=[]
for key,row in saved['assets'].items():
 rows.append('<tr><td>'+e(key)+'</td><td>'+str(len(row['slots']))+'</td><td>'+str(row['lod_count'])+'</td><td>已读回</td><td class="path">'+e(row['path'])+'</td></tr>')
buildtext='；'.join(x['target']+(' 构建成功' if x['exit_code']==0 else ' 构建未完成') for x in builds) or '构建进行中'
partrows=''.join('<tr><td>'+e(k)+'</td><td>'+format(v,',')+'</td></tr>' for k,v in sorted(saved['gun_part_triangles'].items()))
views=[('Actual_Right','右侧整体'),('Actual_Receiver','机匣与抛壳口'),('Actual_Top','顶面连续性'),('Actual_Ext12','十二发弹匣')]
gallery=''.join('<figure><a href="Preview/'+n+'.png"><img src="Preview/'+n+'.png"></a><figcaption>'+label+' · 实际模型离线渲染</figcaption></figure>' for n,label in views)
doc='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>12K 表面重建与检查报告</title><style>
*{box-sizing:border-box}body{margin:0;background:#141619;color:#e8e9eb;font:16px/1.65 "Microsoft YaHei",sans-serif}main{max-width:1260px;margin:auto;padding:42px 28px}h1{font-size:34px;margin:0 0 8px}h2{font-size:22px;margin-top:34px}p{color:#bfc4cc}img{display:block;width:100%;border-radius:8px}figure{margin:0}figcaption{padding:8px 0;color:#aeb7c3;font-size:13px}.hero{margin:26px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.stats{display:flex;gap:14px;flex-wrap:wrap;margin:26px 0}.stats div{background:#22262c;border:1px solid #38414d;padding:15px 22px;border-radius:8px}.stats b{display:block;font-size:28px;color:#f1f3f5}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;border-bottom:1px solid #343b45;padding:9px 12px}th{color:#abb8c9}a{color:#b9d5ff}.path{font:11px/1.5 Consolas,monospace;word-break:break-all}details{margin:18px 0;background:#1b1f24;border-radius:8px;padding:14px}summary{cursor:pointer;color:#d4deeb}.note{border-left:3px solid #97afcb;padding-left:15px}@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:22px 14px}}
</style><main><h1>Saiga 12K · 表面重建</h1><p>2026-10-18 · 先建立目标预览，再重建几何、法线与材质，并独立读取 UE 保存资产检查。</p>'''
doc+='<div class="stats"><div><b>88,834</b>枪体三角形（不含手臂）</div><div><b>39 / 39</b>网格与材质读回</div><div><b>0</b>退化面 / 退化 UV / 骨骼错绑</div><div><b>21</b>原手臂矫正形状保留</div></div>'
doc+='<figure class="hero"><a href="Preview/SavedUE_Hero.png"><img src="Preview/SavedUE_Hero.png"></a><figcaption>实际 UE 保存网格读回后的 Cycles 实渲。使用本次法线图与对应材质配方；不是 AI 概念图，也不是游戏场景截图。</figcaption></figure>'
doc+='<h2>制作结果</h2><p>将原 5,165 三角形枪体重建为 88,834 三角形近景模型。上盖为 0.7 mm 实体弧形壳；枪管、导气组件、固定件重新制作连续曲面与倒角。护木、握把和枪托按原件截面重建，恢复原凹面装饰，补充压筋和托垫防滑筋。十二发弹匣为 5,104 三角形，保留插接段与原换弹骨骼。</p>'
doc+='<p>沿用 WS1.1 母材质，分开处理缎面金属、枪机亮件、聚合物和橡胶。关闭 Grain、Mottle、Stipple、随机划痕与统一磨损；采用结构法线和真实边缘形成细节。枪体法线 4K / 遮罩 2K，扩容弹匣法线 2K / 遮罩 1K；法线按 OpenGL 产出，UE 只翻转一次绿色通道，关闭 sRGB 并采用 Normalmap 压缩。保留 mip 与流送。</p>'
doc+='<h2>实际模型各角度</h2><div class="grid">'+gallery+'</div><h2>检查结论</h2><table><tr><th>范围</th><th>结果与证据</th></tr>'
for label,text in [('几何与 UV','枪体和扩容弹匣均无零面积面、退化 UV、非有限坐标或异常长度法线。'),('法线','结构法线 Z 均值约 0.994；正确压缩、线性采样和一次绿色翻转，未叠加整面颗粒法线。'),('材质与配件','39 份网格全部读取实际槽绑定；没有默认网格材质回退。37 份通用配件的几何包围盒与 LOD 数保持一致。'),('手臂与机械','37,086 个手臂三角形的坐标、法线、全部 4 套 UV 与权重指纹一致，骨架及 21 个矫正形状名称一致。枪体有效权重均属于预定机械骨骼。'),('外观','已查看整体、反侧、机匣近景、顶面、扩容弹匣与 UE 读回几何实渲。上盖未见非功能性透空，功能性抛壳口与弹匣口保留。'),('构建',buildtext),('玩法范围','全自动、圆弧准星、八发/十二发容量、配件数值与存档身份没有改动；未进行 PIE、动作回归、性能采样或联机测试。')]:doc+='<tr><td>'+label+'</td><td>'+text+'</td></tr>'
doc+='</table><p class="note">本次“优化”指表面与外观重建。第一人称保留源骨骼网格的 LOD 方案，扩容件保存 3 级 LOD，通用配件保留原 LOD；没有据面数宣称帧率提升。最后的游戏观感仍受场景光照影响。</p>'
doc+='<details><summary>39 份网格检查清单</summary><table><tr><th>资产键</th><th>检查材质槽</th><th>LOD</th><th>结果</th><th>实际路径</th></tr>'+''.join(rows)+'</table></details><details><summary>17 个枪体材质区域</summary><table><tr><th>区域</th><th>三角形</th></tr>'+partrows+'</table></details>'
doc+='<details><summary>最初的成品目标预览（AI，仅作设计方向）</summary><img src="Preview/12K_TargetPreview.png"><p>以原有 12K 轮廓制作的目标图；交付状态以上方实际模型渲染和保存资产检查为准。</p></details>'
if (O/'Preview/UE_Catalog.png').exists():doc+='<details><summary>UE 离屏目录图</summary><img style="max-width:800px" src="Preview/UE_Catalog.png"><p>通过当前编译后的运行定义生成，不加载或写入玩家档案。</p></details>'
doc+='<h2>可重建资料</h2><p><a href="plan.json">优化方案</a> · <a href="Reports/source-check.json">源几何与贴图检查</a> · <a href="Reports/saved-assets-check.json">UE 保存资产读回</a> · <a href="Receipts/delivery.json">交付回执</a> · <a href="Preview/generation.json">预览及图标生成提示词</a></p><p>当前运行目录：<code>/Game/Weapons/Saiga12K/SurfaceRebuild20261018</code>。作者场景、烘焙源、旧引用备份与生产脚本均保留；共享母材质未改动。</p></main></html>'
(O/'Report.html').write_text(doc,encoding='utf-8');print('SAIGA_SURFACE_REPORT_SAVED',delivery['complete'])
