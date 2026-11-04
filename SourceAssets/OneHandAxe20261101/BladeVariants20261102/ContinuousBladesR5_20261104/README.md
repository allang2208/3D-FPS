# 通用斧刃 R5：连续厚度、刃口与标准图标

2026-11-04 已完成源模型、FBX、两套原厂同源 PBR，后台导入保存 13 个 UE 资产，并登记两款模型与三张共享图标。未启动 UE 界面、游戏测试或验收渲染；最终外观由用户验收。

## 几何处理

| 部件 | 肩部厚度 | 刃面支撑区标称厚度 | 锋缘厚度 | 三角面 |
| --- | ---: | ---: | ---: | ---: |
| 厚背重劈 | 24 mm | 11 mm | 0.6 mm | 42,950 |
| 百炼弧锋 | 18 mm | 8.6 mm | 0.6 mm | 39,702 |

两款重新构建连续厚度场，厚背、斧腹与磨刃沿同一实体逐渐收薄；凸弧磨刃在内侧与主体相切，并向上下端自然收窄。加密轮廓与曲面，非切削边采用 0.55 mm 圆角，保留作者法线。

保留原厂 Z=11.5 cm 装配端与 Z≤13 cm 柄颈；上段用 16 段 Hermite 过渡接入斧肩。接口和斧身共用边环。外轮廓、有效攻击距离、数值、强化公式和动作不变。钩月保留已制作的 R4 几何。

最终可编辑源为本目录的 HeavyCleaver_Editable.blend、FoldedArc_Editable.blend；Geometry 子目录是材质转移前的中间源。Export 内为本次导入 FBX。

## 材质

主体与磨刃分别采样原厂 M_TacticalHatchet 的真实 BaseColor、ORM、Normal，按实际毫米尺度转移。主体深灰石洗钢、刃口浅银磨刃；百炼保留低对比钢纹。切线法线经目标 TBN 重建，UE 导入仅翻转一次绿色通道。

新游戏网格与材质名称分别以 HeavyCleaver_R5、FoldedArc_R5 结尾，位于 /Game/Weapons/TacticalHatchet20261101/ModulesV1。

## 三张标准图标

统一采用 FirearmFramedIcons20260930/muzzle_brake_framed_v2.png 母版，保留厚倒角金属方框、四角八角铆钉、宽银色内环和深色凹面底板。每张图只放对应斧刃，刃向左、柄颈向下，完整留在内环内。

生产流程为实际当前模型正交透明输入 → imagegen 独立编辑母版 → 原始生成 PNG 原样复制。IconInputs 为输入图和源场景，Icons 为正式图标；没有用 Blender 自画边框替代标准母版。

- [生成提示](icon_prompts.json)
- [生成来源与部署路径](icon_deployments.json)
- 本机钩月图标：`Icons/blade_1_axe_swift_crescent.png`
- 本机厚背重劈图标：`Icons/blade_1_axe_heavy_cleaver.png`
- 本机百炼弧锋图标：`Icons/blade_1_axe_folded_arc.png`

以上 PNG 按仓库资产发布边界保留本机，不随文字配方上传。

同步 canonical AttachmentIcons20260913 共享 PNG 与对应 UE 纹理，若有既存 FramedFirearms／FramedBows 副本也同步替换。UE 使用 UI 纹理组、EditorIcon 压缩、sRGB、无 mip、NeverStream、MaxTextureSize=1024；保存原始生成图片，不缩放覆盖原件。

## 后续制作入口

1. Blender 后台执行 author_all.py：重建两款几何、原厂 PBR 和最终 FBX。
2. Blender 后台执行 render_icon_inputs.py：仅生成三款实际模型输入；最终图标仍按 icon_prompts.json 经 imagegen 制作。
3. 将新的生成结果记录到 collect_icons.py 并执行，保留原始生成文件。
4. run_import.ps1：使用既有 UE 批次互斥后台导入；若 UE 已运行，改用同一互斥下的现有桥执行 import_assets.py。
5. py -3.11 register.py：保存成功后更新两款视觉配方、外观说明与三张共享图标。

上级 author_blades.py、render_icon_inputs.py、import_blades.py、register_blades.py 均已接续本版本。旧材质批次和旧手绘边框脚本仅为历史来源。

import_receipt.json 记录实际保存资产；delivery.json 记录登记结果。Before 保留本次覆盖的资产、共享 PNG、数据与旧入口。没有修改攻击、强化或改造数值，也没有新增 C++ 构建需求。
