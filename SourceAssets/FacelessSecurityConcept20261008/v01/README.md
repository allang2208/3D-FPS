# 无面男性安保：三视图候选 V01

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

日期：2026-10-08

## 交付

- `M_FacelessSecurity_ThreeView_v01_CoveredStudy.png`：内置 image_gen 生成的正面、左侧、背面设计图。
- `generation_prompt_covered.txt`：最终出图提示词。
- `generation_prompt.txt`：初次无衣基础体提示词，工具返回 moderation_blocked / sexual，未获得图像；随后改为有不透明打底服的方案。

## 设计

延续无面接待员的灰白蜡质皮肤、低饱和冷色血管和封闭无器官头部。男性安保采用宽肩、厚颈、结实四肢及自然人形比例，保持完整五指与脚掌，使用便于后续绑骨的 A 形姿态。怪物编号尚未分配。

灰色不透明连体打底服仅用于三视图中的体型展示，不是最终安保制服。这件打底服可能被 Meshy 一并生成；实际下载模型到位后再处理主体表面并制作独立安保制服、裤装与配件，不承诺依靠提示词自动去除打底服。

用户沿用先生成身体模型、再由助手制作衣物的流程。本轮只交付生成式三视图设计图，没有调用 Meshy，没有制作或导入三维模型、衣物、骨架或动画。三幅图不是同一真实模型的精确正交投影；用于实际多视图生成时应分别准备对应视角输入。

## 参考与状态

视觉参考：`SourceAssets/FacelessReceptionistConcept20261007/v01/M_FacelessReceptionist_ThreeView_v01_CoveredStudy.png`。仅阅读参考图，未修改女接待员资产。

使用 ue5-monster-workflow、asset-model-workflow 与 imagegen 流程；实际生图使用内置 image_gen。未启动 UE，未执行游戏测试，造型交由用户确认。
