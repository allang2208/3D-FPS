# ClothTop45：201 布料弹箱上部修整

2026-09-30 已后台保存现用枪体、ClothFeed33 分件、湿润映射与配件图标，四个目标资产；两份私有材质已编译保存。回执为 `delivery.json`，最终后台记录为 `integrate_retry1.log`（`C45_CURRENT_SAVED 4`，退出码 0）。

## 问题与方案

方案正本：[plan.md](plan.md)。用户要求的旧模型排查图位于 `Inspection/before_upper.png`、`before_broad.png`、`before_top.png`。原几何虽然没有开放边，但上部存在不规则穿孔、扭曲薄片和粘连翻边；不是仅调打光或粗糙度能消除的问题。

- 在原模型局部 Z=-30 mm 处提取单个 614 顶点边界环，保留下部几何和面角属性；以共享顶点连续接回新上沿。
- 重建有限幅度的布面过渡、圆润包边、浅褶皱与箱口内壁。旧的上部碎片由实际表面替代；不叠加平板遮盖。
- 按现有弹链底段范围制作有厚度的圆角供弹口框及两个连接块。安装最高面维持原 Z=-4.822 mm；具体造型是对现有游戏模型的局部整理，未宣称参考视频 1:1。
- 织物 UV0／UV1 的原下部图集保留；UV2 标记新面过渡，UV3 使用米制织物坐标。新布面采用 0.65 mm 尺度的细纹、轻微针脚法线与粗糙度；硬接口另用暗色材质，避免旧图集凹凸污染新面。
- 单箱布面 79,076 三角形、接口 1,336 三角形，共 80,412；原袋身 77,482。预算用于近景曲面、真实内壁和接口，未生成百万面运行模型，未据此推算性能。

## 活动资产与不变合同

- 主体 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`：仅替换 `M_LMG201_Cloth33__OldBox*`／`NewBox*` 分区。
- 分件 `/Game/Weapons/LMG201/ClothFeed33/Parts/SK_LMG201_Cloth33_Props`：同步旧箱、新箱，保留原弹链。
- 新硬接口也沿用 OldBox／NewBox 槽名前缀，与既有显示切换规则一致。
- 骨骼 `LMG201_Box`／`New_LMG201_Box`、弹链、动画、125 发选项、存档及枪身其他分区不改。
- 私有材质位于 `/Game/Weapons/LMG201/ClothTop45/Materials/`；对应湿润映射及 `Material21/bindings.json` 已更新。
- 图标键仍为 `ue_lmg201_magazine_lmg201_cloth_box`；Content 中 PNG 与 Texture2D 均已替换。

## 重复制作与恢复

1. `capture.py` 读取现用资产、材料槽和文件散列；`Inputs/CurrentProps.fbx` 保留制作起点。
2. `model.py` 在原 R30 袋身基础上局部重建与绑定，输出 `LMG201_ClothTop45.blend`、FBX 与 `model.json`。该 Blend 的旧整枪仅作坐标上下文，不代表 J44 后的全枪母版，不能整场导入覆盖当前整枪。
3. `author_icon.py` 依据新网格、有效织物过渡与灰阶规范制作现用配件图标。材质的 UE 实现以 `materials.py` 为准，图标副本不修改游戏色彩。
4. `integrate.py` 先编译保存材质，再调用 `install.py` 局部替换两个骨骼网格、保存湿润表及图标；保持已有材质槽名称和原生骨架。用 `run_background.ps1 -taskScript integrate.py -taskLog <新日志名>` 在无编辑器占用时执行。
5. 完整现用枪体导出为 `Exports/After_Body.fbx`，完整供弹分件为 `Exports/After_Props.fbx`。旧包／图标在 `Before`；不要重跑 ClothFeed33 旧安装器覆盖当前枪体。

本轮完成了用户要求的旧模型上部排查、方案、制作和保存；未打开 UE GUI，未运行游戏或追加验收渲染。配件图标属于交付制作。实际外观、装箱接触和动作效果由用户测试。
