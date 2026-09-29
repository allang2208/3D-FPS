# 手套背包图标专用规则

2026-09-27，FPSGAME。用户选择空手套展示、不出现皮肤，并否定两只叠放造成的遮挡与穿插。本规则优先于旧装备图标的双只平铺构图；320×320、透明底和 91% 填充规则继续沿用。

## 固定展示合同

1. **一张图只显示一只空手套。** 不叠放第二只，不显示皮肤、手臂或人台。指头、虎口、腕口不能被另一个展示对象遮挡；编辑场景也只显示当前物品。
2. **使用当前穿戴网格的真实形状。** 按 `modular_outfits.json` 的 `appearance_family` 和资源引用选母版及生产 PBR。2026-09-28 黑色为 `BlackLeatherStitchWearV4`，棕色／战术／钢甲为 `FingerlessDetail20260928`／`TacticalDetail20260928`／`SteelDetail20260928`；实际源和入口见 [手套制作配方](../../ue5-fps-arms-animation/references/glove-clothing-production-recipes.md)。`FittedFieldGlovesV1`、`TailoredFingerlessV1` 和 `FingerlessHuntV2` 是对应历史形状／依赖，不因旧出图脚本硬编码而回退。旧 Body 拾取姿态不充当新的手型母版，颜色、材质与款式沿用同一当前装备。
3. **图标姿态独立制作。** 以骨骼旋转形成轻微弯曲、自然分指的松弛手型，保持掌宽、指长、骨段长度和拇指位置；不得把手压平、拉长或五指排齐。出图入口不回写穿戴网格、动画或世界掉落模型。若任务同时要求一致的掉落外观，可由独立模型导出步骤复用选定空壳；本款由 `save_tailored_fingerless_family.py` 导出，出图时不隐式重导。
4. **坐标变换保持形状。** 掌长方向、横向与手背法线必须正交归一；统一处理 UE 到 Blender 的轴系与面序。不能把非垂直的 across/forward 直接当成矩形投影轴，否则会斜切掌形。
5. **全指与露指采用不同视角。** 黑色突出完整五指、虎口和空腕口；棕色从指根与拇指一侧斜看，让真实指口、拇指孔、卷边和暗内衬可辨。主轴朝上，允许小幅倾斜。禁止为了“像手套”画皮肤、添半截手指筒，或伪造实际不存在的指口。
6. **皮革要有结构辨识。** 棕色使用实际扫描、原有边距和缝线字段，内衬比外皮暗；黑色沿用 V7 掌背与缝线区域贴图。保留写实暗色，不用肤色、纯黑剪影或强镜面高光代替材质。
7. **画幅仍与背包一致。** 2×2 占格输出 320×320 RGBA，透明背景、正交镜头；按旋转后的实际轮廓居中，主轴约占 91%，不裁指尖、拇指或腕口。曝光从生产材质色出发做有限修正，不能靠整体提亮掩盖形体错误。

## 当前制作链

以下 9 月 27 日链路保留作历史来源；继续出图优先按活动家族分流。黑色 V4 与三款伴随家族的正式图标和作者源 PNG 要同步，外观升级同时维护后续出图入口，避免下一次批量渲染恢复旧腕口、旧光滑壳或皮革衬底。当前参数与入口见 [手套制作配方](../../ue5-fps-arms-animation/references/glove-clothing-production-recipes.md)，表面一致性见 [手套衣物标准](../../ue5-fps-arms-animation/references/glove-clothing-surface-production.md)。

- 棕色裁片款：`author_tailored_fingerless_family.py` → `save_tailored_fingerless_family.py` → `import_tailored_fingerless_family.py`。先继承代表样件的裁片和烘焙 UV，再适配原生骨架；拓扑不同的身体和单手局部分别烘焙，不强套 UV。`render_field_glove_icons.py` 按活动 `appearance_family` 分流，避免后续批量出图恢复旧光滑壳。共用贴图保证材质输入一致，不宣称 Blender 与 UE 光照完全相同。

- `Tools/ModularOutfit/glove_icon_display.py`：当前原生网格、正交坐标架、单只松弛姿态、空内衬及原有缝线字段。
- `Tools/ModularOutfit/render_field_glove_icons.py`：材质、取景、曝光与最终 PNG；只写图标和单独的编辑场景。
- `save_fingerless_hunt_sources.py`：模型重导后调用上述图标入口，不能恢复旧的双只平铺出图。
- 最终 PNG：`Content/ColdSteelData/Icons/ModularOutfit20260924/ue_field_gloves_fingerless.png`、`ue_field_gloves_black.png`。
- 编辑场景与生产回执：`SourceAssets/ModularOutfit20260927/GloveIconDisplayV2/`；`render-final.log` 为本次单只成图日志。

本次失误有两类：旧展示源和非正交投影造成手型不自然；之后的双只构图又遮挡轮廓、发生穿插。颜色与填充比例正确不能证明手套可辨。当前改为单只空壳、自然手型和分类视角，不将之前被否定的成对版本作为后续母版。

图标制作不自动触发游戏、UE 预览或装备动作测试。交付显示最终 PNG，运行时效果由用户试玩；没有实际检查的穿模项目不得声称通过。
