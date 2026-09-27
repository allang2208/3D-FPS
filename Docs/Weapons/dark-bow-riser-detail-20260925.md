# 暗纹猎弓弓体细节升级（2026-09-25）

用户反馈原弓近景棱角和锯齿过重。本轮只升级弓体网格，不改动作、弦锚点键和木纹贴图。已保存并曾切换运行引用；运行弓体现已换成木质长弓，本网格留作回退。未进游戏验收。

## 原模型

\SM_DarkBow_Riser\：5666 三角、3579 顶点，超过一半顶点硬边大于 25°（中位 33.7°，p90 100°），还有零长边。这是 Fab 低模反曲弓去掉 124 个烘焙弦三角后的结果。

## 制作

Blender 5.1 在原形上做：去重／消退化 → 32°／1.6 mm／3 段倒角 → Catmull-Clark 一档 → 弓臂平滑（握把和弓梢权重大大降低）→ 加权法线。可编辑源 \RiserDetail_Editable.blend\，导出 \Export/SM_DarkBow_RiserDetail.fbx\。

| 项 | 原弓体 | 细节版 |
| --- | --- | --- |
| 三角 | 5666 | 71276 |
| 硬边顶点占比 | 52% | 22% |
| 中位夹角 | 33.7° | 6.9° |
| 包络 | 38.223 × 3.511 × 139.999 cm | 导入后按原包络对齐，握把原点仍在 0 |

UE 导入时 Blender 米制被当成厘米，先 ×100；FBX 前向把 Y 镜像，已翻回并按原包络逐轴对齐。木纹三槽仍绑 MI_BowWood_Body/Limb/Inlay；后续按结构分色见 [木纹表面](dark-bow-wood-finish-20260925.md)。

## 运行引用

\ows.json\ 的 \ow_part_riser_mesh\ 改为 \/Game/Weapons/DarkBow20260925/RiserDetail20260925/SM_DarkBow_RiserDetail\，\ow_presentation_revision\ 11，旧存档会重挂网格。后续木色分槽见 [木纹表面](dark-bow-wood-finish-20260925.md)。原 \ArmsV2/SM_DarkBow_Riser\ 保留回退。弦坐标键未改。

作者脚本：\uthor_riser_detail.py\、\import_riser_detail.py\、\ix_riser_axis.py\。未做游戏测试。
