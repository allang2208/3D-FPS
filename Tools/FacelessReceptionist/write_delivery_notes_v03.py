import json
from pathlib import Path
project=Path(r'D:\FPS3D\FPSGAME')
base=project/'SourceAssets/FacelessReceptionist20261007'
root=base/'V03'
receipt=json.loads((root/'ue_delivery.json').read_text(encoding='utf-8'))
if receipt.get('stage')!='saved':raise RuntimeError('UE asset save is still pending')
author=json.loads((root/'authoring_receipt.json').read_text(encoding='utf-8'))
cloth=sum(p['triangles'] for p in author['parts']);body=author['body_triangles']
readme=f"""# 无面接待员 V03（2026-10-08）

按用户“把 1–2 都做了”继续完成裙摆／肩袖动作适配与接待员服装细节。可编辑源、穿衣与独立衣物导出、三视图、{len(receipt['saved'])} 个 UE 资产均已后台保存。未进行游戏、PIE 或动态动作验收，由用户测试。

## 本版制作

- 裙腰固定于骨盆；裙摆两侧跟随对应大腿，中前／中后降低双腿相互牵拉。后开衩内衬采用相同分区。
- 西装下摆解除腿骨牵拉；肩袖与衬衫权重平滑；领座跟随颈根与上胸。
- 从当前 UE 已分配的 idle / walk / attack 导出制作输入，取共 33 个源姿态计算衣物余量，并进行表面平顺处理。该步骤属于制作，不代表所有动态穿模已消除或通过游戏验收。
- 补做独立翻领、卷边及明线、圆形包边纽扣与扣眼、双嵌线口袋、西装／袖口／裙侧／背缝与后开衩包边、黄铜珐琅 RECEPTION / M STAFF 胸牌。
- 调整深灰蓝斜纹布 PBR；颜色、粗糙度、法线共用数值表面场，不宣称雕刻高模烘焙。
- 身体、身体权重、原有女僵尸动作曲线与玩法时序保持 V02 基础。衣物仍为骨骼蒙皮，没有 Chaos Cloth 模拟。

## 文件

- Authoring/FacelessReceptionist_V03.blend：完整身体、{len(author['parts'])} 个独立衣物／细节对象、共用骨架；默认绑定姿态，已有 NLA 制作动作静音。
- Authoring/FacelessReceptionist_V03_Fit.blend：动作适配制作中间源。
- Delivery/FacelessReceptionist_V03.glb：完整穿衣模型、蒙皮和贴图，不包含动画。
- Delivery/FacelessReceptionist_Clothing_V03.glb：独立衣物、共同骨架和贴图，不包含动画。
- Delivery/SK_FacelessReceptionist_V03.fbx：UE 合并穿衣网格。
- Delivery/SK_FacelessReceptionist_Body_V03.fbx：独立完整身体。
- Delivery/SK_FacelessReceptionist_Clothing_V03.fbx：新增独立合并衣物 FBX。
- Textures/：六个材质分区的 PBR 图片，共 18 张。
- MotionSources/：本轮从当前 UE 动作副本导出的三段制作源和来源记录。
- Preview20261008/FacelessReceptionist_V03_ThreeView.png：用户请求的正／侧／背三视图，Blender 静态绑定姿态。
- authoring_receipt.json、motion_authoring.json、ue_delivery.json、delivery_summary.json：制作、导出和资产保存记录。
- Logs/：后台制作与 UE commandlet 日志。

当前作者几何：身体 {body} 三角面，衣物 {cloth} 三角面，合计 {body+cloth}；六个材质分区。保留用户已减面身体及其原始 UV，不再次减面，不删除被衣物遮挡的身体。

## UE 接入

目录 /Game/Monsters/FacelessReceptionist：

- BP_FacelessReceptionist 使用更新后的 SK_FacelessReceptionist 完整穿衣网格。
- 独立身体为 SK_FacelessReceptionist_Body。
- 新增 SK_FacelessReceptionist_Clothing，与身体使用相同 SKEL_FacelessReceptionist。当前蓝图仍为合并穿衣方案，未添加运行时换装系统。
- 原女僵尸动作副本 A_Receptionist_idle / walk / attack、物理资产、材质／纹理已保存。
- F6 → 怪物生成 → 无面接待员；沿用既有入口、Nurse 行为、胶囊与导航，不修改地图或 C++。

没有启动 UE 图形编辑器、游戏或 PIE。本轮没有 C++ 构建；此前 V01 的独立 Game 构建问题与历史构建状态见根目录记录，不宣称该问题已解决。

## 制作入口

脚本位于 Tools/FacelessReceptionist：

1. export_motion_sources_v03.py：后台导出当前 UE 动作供制作使用。
2. fit_motion_v03.py：从 V02 重建裙摆／肩袖权重和衣物余量。
3. tailor_details_v03.py：平顺衣料、制作服装细节及贴图，保存最终 Blender。
4. export_delivery_v03.py：保留作者分件，导出完整／独立衣物 GLB 和三份 FBX。
5. import_assets_v03.py：实际导入、赋材质并保存本角色 UE 资产。
6. render_reference_v03.py：仅在用户要求预览时制作三视图。

prepare_delivery_v03.py 与 refine_v03_ease_and_lapels.py、finish_surface_v03.py、finish_lapel_v03.py 是本次编辑脚本的历史步骤，不是以上制作流水线的入口，不应重复运行覆盖最终脚本。重导更新内容时，导入进程需设置 RECEPTIONIST_FORCE_REIMPORT=1；默认按本版本保存回执续接。正在编辑器中打开同一资产时使用既有批次桥，避免外部 commandlet 覆盖未保存状态。

## 来源与状态

身体为用户提供的 Meshy GLB；骨架与动作来自项目现有女僵尸；新增服装几何与布纹为本地制作。V01／V02 保留作追溯。

本次三视图只反映 Blender 静态外观，不证明 UE 材质效果、动态穿模或游戏行为已经通过验收。没有测试、自动运行游戏、提交 Git 或公开分发。
"""
(root/'README.md').write_text(readme,encoding='utf-8')
old=(base/'README.md').read_text(encoding='utf-8-sig')
i=old.index('以下为 V01 历史记录')
(base/'README.md').write_text("""# 当前版本：V03（2026-10-08）

当前制作包见 [V03/README.md](V03/README.md)：裙摆／肩袖动作适配与接待员服装细节均已制作，Blender、GLB、FBX、三视图与 UE 资产已后台保存。新增同骨架独立衣物网格，现有 F6 角色仍使用完整穿衣模型。未游戏测试，由用户体验。

[V02](V02/README.md) 及 V01 原文件保留作追溯。

"""+old[i:],encoding='utf-8')
doc=f"""# 无面接待员 V03（2026-10-08）

当前制作包：[V03/README.md](../../SourceAssets/FacelessReceptionist20261007/V03/README.md)。

用户要求同时推进裙摆／肩袖动作适配和接待员服装细节。V03 已制作分区裙摆权重、骨盆固定腰部、解除西装下摆的腿骨牵拉、平顺肩袖权重，并用当前 UE 三段动作中的 33 个源姿态制作衣物余量；原身体、身体权重和动作曲线保留。衣物仍为蒙皮，没有 Chaos Cloth。

完成独立翻领及卷边、明线、圆形纽扣、扣眼、双嵌线口袋、袖口／侧背缝／后开衩包边、RECEPTION 胸牌及深灰蓝斜纹布 PBR。作者文件含完整身体与 {len(author['parts'])} 个衣物／细节对象；身体 {body}、衣物 {cloth}、合计 {body+cloth} 三角面，六个材质分区。

完整穿衣与独立衣物 GLB、三份 FBX、Blender、PBR 和用户要求的静态三视图已保存。原 /Game/Monsters/FacelessReceptionist 下 {len(receipt['saved'])} 个资产已后台保存，包括新增 SK_FacelessReceptionist_Clothing。蓝图继续使用完整穿衣网格，独立衣物资产供后续模块化使用，未接运行时换装系统。沿用现有 F6 无面接待员入口、Nurse 行为、导航和时序，未改 C++ 或地图。

实际保存回执见 V03/ue_delivery.json，制作记录见 motion_authoring.json 与 authoring_receipt.json；commandlet 退出码 0。三视图为 Blender 绑定姿态，未进行动态动作／游戏测试；没有启动 UE 图形编辑器、游戏或 PIE，交由用户体验。V01／V02 保留，本轮未重新构建 C++。
"""
(project/'Docs/Monsters/FacelessReceptionist20261008.md').write_text(doc,encoding='utf-8')
summary={'version':'V03','requested_work':['skirt_and_shoulder_sleeve_motion_fit','receptionist_outfit_details'],'stage':'exported_and_ue_assets_saved','body_triangles':body,'clothing_triangles':cloth,'total_triangles':body+cloth,'clothing_parts':len(author['parts']),'material_families':6,'saved_ue_assets':len(receipt['saved']),'standalone_clothing_asset':receipt['clothing_mesh'],'runtime_render_mesh':receipt['mesh'],'runtime_outfit_swapping':False,'chaos_cloth_simulation':False,'runtime_tested':False,'editor_gui_started':False,'preview':'Preview20261008/FacelessReceptionist_V03_ThreeView.png','import_process_exit_code':0,'exports':[str(p.relative_to(root)) for p in sorted((root/'Delivery').glob('*'))]}
(root/'delivery_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
