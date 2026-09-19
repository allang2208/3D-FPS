# 寒晶·双手剑：模块化作者源

> 2026-09-19 用户确认本轮最终结果成功、符合预期。此记录来自用户实机反馈；本次归档/文档整理没有重新测试。

2026-09-15，按用户批准的拆分方案，将现有寒晶剑制作成四类独立模型，剑身Ⅱ继续作为剑刃表面的符文材质。此次是现有模型拆分与运行接入；未重新生成剑形或动作。

## 当前资源

本轮基础 UE 模块位于 `/Game/Weapons/FrostCrystalSword20260915/Modules20260915/`。三款新增配重锤当前位于独立的 `PommelsRepair20260915/` 目录（2026-09-19 修订）。

| 部位 | 模型 | 当前选择 |
| --- | --- | --- |
| 剑身Ⅰ | `SM_FrostSword_Blade_factory` | 原装外形；现有延锋刃、重脊刃、轻羽刃保留各自数值 |
| 护手 | `SM_FrostSword_Guard_factory` / `bastion_guard` / `riposte_guard` / `light_guard` | 原装、壁垒、反击、轻量四款独立模块 |
| 握把 | `SM_FrostSword_Grip_factory`；新增 `SM_FrostGrip_shock_wrap` / `swift_grip` / `long_twohand` | 原装与三款独立握把；[当前握把作者入口](../FrostSwordGrips20260919/README.md)，长柄联动配重锤位置和动作家族 |
| 配重锤 | `SM_FrostSword_Pommel_factory`；新增 `SM_FrostPommel_ballast_hardened` / `ballast_rune` / `ballast_magic_orb` | 原装及三款 5080 改造模块；当前可编辑源与接入说明见 [配重锤修订目录](../FrostSwordPommelsRepair20260915/README.md)。旧候选及初版源保留 |
| 动画载体 | `SK_FrostSword_Arms` | 仅手臂可见几何，保留原骨架和 `WPN_root` 驱动骨骼 |
| 剑身Ⅱ | `M_SilverRuneSurfaceV2` 和三张现有符文纹理 | 仅挂在独立剑刃上，沿用银白闪烁效果 |

`FrostSword_Modular_Editable.blend` 是本轮可编辑源；四个原装模块组装显示，三款改造护手及原始源对象保留并隐藏。`Export/` 存放七件静态 FBX 和手臂载体 FBX。

## 接口 frost_hilt_v1

Blender 作者坐标为米：剑尖 +Z、宽度 X、厚度 Y。UE FBX 导入为厘米，模块安装位置记录在运行目录中，不在游戏中重新猜尺寸。

| 接口 | 作者坐标与归属 |
| --- | --- |
| 剑刃—护手 | V 形边界 `z = -0.008 + 1.1 × abs(x)`；中央 V 形安装座与两翼一起属于护手 |
| 护手—握把 | `z = -0.050 m` |
| 握把—配重锤 | `z = -0.227 m` |
| 剑刃、护手原点 | `(0, 0, 0)` |
| 握把原点 | `(0, 0, -0.050 m)`，导出顶点已相对此点归零 |
| 配重锤原点 | `(0, 0, -0.227 m)`，导出顶点已相对此点归零 |

切分在原三角面上插值位置、UV、顶点色和原表面法线，只为新切口添加封口。新 V 形接口选在三款护手共用的原模型区域内，上一轮修订的护手两翼和连续连接面保留。各模块共用 `GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze`，保留 UV0、`StockBronzeUV` 与 `GuardFinish`，避免单独换材质造成接口色差。

`interfaces.json` 保存每个模块的安装原点和实际边界顶点环；可编辑源和导出 FBX 保留边界法线及 UV。后续自定义件应从对应原装模块复制安装端，再制作外侧造型。握把两端、握持长度和双手接触区域属于当前动画接口，修改这些尺寸需要另做手部适配。

## 运行组装

- `Content/ColdSteelData/frost-sword-modules.json`：槽位 ID 到独立模型路径的映射、安装位置、符文范围、攻击端点和骨骼安装变换。
- `Weapons/ModularSwordVisual.cpp`：共用组装入口；剑刃为根静态组件，护手、握把、配重锤为子组件。更换护手仅换护手模型。
- `Weapons/RuneSwordComponent.cpp`：手臂载体继续播放原双手剑动画；独立剑挂在 `WPN_root`。原骨架包含约 100 倍缩放，作者生成的安装变换包含约 0.01 的抵消缩放。
- 改造台草稿与应用、物品图标、世界掉落调用同一套模块选择；预览取四个部件的合并包围盒。存档继续保存现有 `gunsmith_parts` 选项 ID，无需更换物品或迁移实例。
- 未提供独立模型的现有数值选项使用该槽的 `factory` 外形；数值仍由原改造系统计算。原整剑 SM/SK 保留为来源和其他旧入口的参考资源。

攻击端点由原剑 `Blade_Base` / `Blade_Tip` 换算为模块坐标，约为 Z=3 cm / 100 cm。这里保留原攻击轨迹；可见剑尖约为 81.17 cm，此轮没有顺带修改命中范围。未来剑刃外形变化时，应同时明确其攻击端点和符文尺寸。

## 后续增加自定义件

1. 从 `FrostSword_Modular_Editable.blend` 复制同槽模块，保留上述安装端的顶点位置、法线和贴图接口；护手造型连同中央安装座整体制作。
2. 保持该槽原点、轴向及单位，导出独立 FBX。FBX 参数参见 `author_modules.py`；不要把组装位移再次烘入已归零的握把或配重锤顶点。
3. 按 `import_modules.py` 的法线、切线、UV、顶点色与材质设置导入；新部件如需独立表面材质，应继续使用安装端一致的金属参数与纹理区域。
4. 在 `melee-gunsmith.json` 添加选项，在 `frost-sword-modules.json` 对应槽用相同 ID 登记模型和安装位置。剑身Ⅰ登记 `trace_base_cm`、`trace_tip_cm`、`rune_dimensions_cm`。
5. 只有重做整套基础模块时才需要重跑下述完整导出入口；普通新配件只导入新增件、追加对应目录项，保留已有目录中的其他配件。

## 本轮重建入口

- `author_modules.py`：读取原始剑与三款接缝修订源，拆分并导出、保存可编辑源。
- `import_modules.py`：导入 UE 资产，生成 `catalog_base.json` 与 `import_receipt.json`。
- `FrostSwordModuleAuthoringCommandlet`：从原 SM/SK 的对应 UV 顶点及参考骨架换算安装变换和原攻击端点，输出最终运行目录；不创建游戏世界，不读取玩家存档。

顺序：Blender 执行作者脚本 → UE Python 导入 → 必要原生构建 → UE 命令行执行 `-run=FrostSwordModuleAuthoring -NullRHI -unattended -nosplash`。本轮使用模块构建后缀 `9152038`，同时构建 FPSGAME、AutoFootstep、AutoFootstepEditor。

记录：`author.log`、`import.log`、`import_receipt.json`、`mount_authoring.txt`、`mount_authoring.log`、`build.log`。

## 交付状态

模型拆分、FBX 导出、UE 导入、运行目录生成和原生构建已完成。按用户规则，没有运行游戏、截图、渲染、自测或回归；效果与交互由用户测试。已经打开的编辑器需重新启动后载入本轮原生代码。
