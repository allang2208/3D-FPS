# 战锤图标修正、轻量锤数值与中央锤座设计

中央锤座后续已完成三款建模和外观接入，见 [中央锤座建模交付](common-hammer-seats-build-20261014.md)。本页保留前一阶段设计记录。

轻量鼓锤 `light_drum` 物理伤害倍率由 0.88 改为 0.90，详情文本改为「物理伤害 -10%」。制作源 `SourceAssets/CommonHammerHeads20261014/catalog.py` 与正式 `Content/ColdSteelData/common-hammer-heads.json` 同步。攻速 1.15、体力消耗 0.88、韧性伤害 0.85 保持不变。

## 图标修正

对照技能 `attachment-icons.md`、认可的 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 母版，以及现有 `pommel_ballast_hardened.png`、`blade_1_heavy_spine.png`，原图问题为：自行构造的光滑边框和小铆钉偏离母版、成对锤头主体偏小、板底及金属明暗不一致。

此轮使用当前实装模型的独立作者场景提取九份部件素材，经统一灰阶助手处理，再以认可母版为边框参考逐项使用 imagegen 制作。锤头图只显示左侧一件作为代表，实装网格仍然成对；其他部件保留竖直安装方向。没有修改运行模型、PBR、挂点和动画。

- 3 张通用锤头母图对应 `hammer_heads_heavy_forged`、`hammer_heads_flanged_breaker`、`hammer_heads_light_drum`。
- 6 张原装母图各复用于本武器对应分类和原装选项，共 12 个键。
- 实际路径仍为 `Content/ColdSteelData/AttachmentIcons20260913`。当前 UI 对普通近战改造优先读取共享键，分类与原装读取武器键；没有修改加载代码。
- 15 个 PNG 与 15 个 Texture2D 已实际导入保存。UI 纹理组、Editor Icon 压缩、sRGB、Never Stream、无 mip。
- 替换前正式图及纹理副本存于 `trash/warhammer-icons-replaced-20261014`，附清单。历史作者输入保留；后续重建正式图使用本轮目录，不能重新部署旧简化边框图。

作者目录 `SourceAssets/WarhammerIconCorrection20261014/` 保存实际来源映射、可编辑 Blender 图标场景、透明素材、imagegen 提示词和生成路径、最终母图、部署脚本与 `import_receipt.json`。无界面导入进程返回 0，回执 complete=true。没有运行游戏或追加验收测试。

## 三款通用中央锤座设计

设计图：`SourceAssets/CommonHammerSeats20261014/DesignV1/common-hammer-seats-design-v1.png`。

| 方案 | 结构身份 | 玩法方向提案 |
| --- | --- | --- |
| 厚壁重铸座 `reinforced_block` | 整体承力芯、阶梯加厚盖板、嵌入铆钉 | 偏打击与削韧，以重量和速度为代价 |
| 镂肋轻型座 `ribbed_light` | 连续承力芯、前后减重窗、外部支撑肋 | 偏快速出手，以单次力度为代价 |
| 叠片缓冲座 `laminated_damper` | 内芯、叠片盖板、薄层缓冲垫、拉杆 | 偏体力效率，以部分削韧为代价 |

共用当前宿主的真实接口：左右 X=±0.040 m、下接面 Z=0.865 m、锤头轴线 Z=0.925 m；后续建模仍以原始接口边界环为准，概念图不代替尺寸依据。跨锤类宿主须适配自己的安装端。

本轮为设计提案，包含三视图及装配示意，尚未建模、导入或注册三款选项，未设置它们的游戏属性倍率。`brief.md` 和两次提示词保留结构约束；初稿的额外自动尺寸已在最终图中移除，轻型座侧视也改回实体接触板。
