# 高地·双手剑：游戏接入

2026-09-22，用户指定按武器标准工作流接入。物品 ID：`ue_highland_claymore`。

已完成作者制作、UE 导入保存、目录接入和常规 `FPSGAMEEditor Win64 Development` 构建；编辑器已重新启动。未启动 PIE、游戏测试或验收渲染，由用户体验。菜单图标渲染属于正式 UI 素材制作。

## 获取与玩法

进入游戏后到仓库领取「高地·双手剑」。沿用一次性发放记录 `ArmoryReceived`，占用 2 × 4 格；仓库空间不足时不消耗领取标记，腾出空间后重新进入游戏领取。

- 使用现有物品实例、双手主武器/副手占用、快捷栏、仓库转移、丢弃拾取和保存流程。
- 沿用现有双手剑的三段普通连击、蓄力重击、格挡、突刺、快速近战、冲刺攻击、战术冲刺和旋风动作及结算入口。
- 基础伤害公式和强化成长复制当前符文剑：基础 40，每强化 +5，智力系数 4.5／每强化 +0.9，力量系数 3.5／每强化 +0.6；物品基础近战距离 180 cm。没有增加独有攻击技能或寒晶自带侵蚀。
- 侵蚀符文可正常改造；精神迸发仅限寒晶，金色强化仅限符文长剑，高地不提供该选项。原生蓝色纹样提供微光，共鸣、侵蚀、导魔使用现有彩色覆盖材质；蛮荒采用后续专属 V2。

## 模型与改造

使用用户重新选定的弧形护手、叶形端部原图生成的 Meshy 母版；圆环端部概念不参与接入。原始文件不变。

作者坐标为米：剑尖 +Z、宽 X、厚 Y。按护手和握把的实际位置分段适配到现有握持空间：剑尖 88 cm，握把上端 −5 cm、下端 −22.7 cm；手臂、手指、骨长与现有动作轨道保持原资源。剑刃厚度按武器用途适配，原 UV、纹理和外表面自定义法线随局部变换保留。

- 四个原装独立模块：剑刃、护手、握把、圆盘配重。
- 三种剑刃：延锋刃、重脊刃、轻羽刃；冻结刃根接口，保留中心纹样通道。
- 三种护手：壁垒、反击、轻量；仅改变原弧形护翼外侧，保留中央安装座。
- 三种握把：吸震、速握、长柄；长柄增加 2.8 cm，联动配重位置与现有长柄动作家族。
- 六款共用配重通过两个专属转接件安装；转接上端取本剑真实切口，下端取共享配重的原装截面，保留共享主体。
- 五个改造栏目继续使用 `gunsmith_parts`，持剑、改造草稿/应用/取消、物品预览和掉落共用 `ModularSwordVisual`。

攻击端点写入本剑目录，跟随 `WPN_root`，使用原装 3／88 cm 端点；改造范围仍只由既有倍率计算，不重复叠加延长效果。掉落碰撞沿用装配包围盒生成的独立物理盒。

## 资源入口

- UE 根目录：`/Game/Weapons/HighlandClaymore20260922`。
- 可编辑模块源：`HighlandClaymore_Modular_Editable.blend`。
- 可编辑 UI 棚拍源：`HighlandClaymore_MenuIcons_Editable.blend`。
- 原始生成模型的可编辑副本：`Highland_Original_Editable.blend`。
- 游戏 FBX：`Export/`；PBR 原贴图保留在上级 `Meshy/candidate01/downloads/`。
- 运行装配：`Content/ColdSteelData/highland-claymore-modules.json`。
- 动画载体：`/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms`。
- 普通动作：`/Game/Weapons/AzureRunesword20260913`；长柄动作：`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations`。
- 当前 38 条共用动作路径、帧数和时长保存在 `shared_animation_sources.json`；本次未改动作。

正式 UI 贴图 30 张：本剑库存图及实体模块图、栏目图；符文语义图沿用已接受设计，配重图沿用实际共用模型的同色图。实体图为 1024 × 1024 RGBA 透明实物棚拍，剑尖朝左，保持安装方向；PNG 和 UE Texture 同步保存。改造台使用已有符文剑的中性补光设置。

## 制作与接入脚本

1. `read_source.py`：读取选定模型的作者坐标，保存原始可编辑副本。
2. `author_highland.py`：尺寸适配、保留 UV/法线拆分、改造件和转接件制作、FBX 导出。
3. `render_menu_icons.py`：实际模型菜单图标制作。
4. `import_highland.py`：通过当前编辑器导入 PBR、材质和静态网格；按回执续接已完成项。
5. `install_catalog.py`：重读并合并本剑的物品、伤害公式和改造目录，部署 PNG，保留其他武器。
6. `import_icons.py`：保存对应 UE UI Texture。
7. `finish_in_editor.py`：添加本剑旋风前景材质映射，记录所复用动作资料。
8. 后续专属改造与渐隐按 [发布恢复顺序](../../../Docs/Weapons/melee-runes-publication-20260922.md) 应用，不能只停留在基础接入。

`compile_highland.py`、`close_for_build.py` 与构建日志仅保留本机历史，不作为公开恢复步骤。基础接入阶段曾完成常规构建，记录见本机 `build-native.log`，结果 `Succeeded`，22.73 秒；不代表后续改动已重新编译或验收。

## 来源与交付边界

造型来自用户选定的本任务概念图，三维候选由 Meshy 7.1 生成。单图没有表达的背面和厚度属于生成推断；本次局部厚度和安装适配属于作者制作。Manny 手臂、现有动作、音频和共享配重继续沿用各自项目来源与许可，不把 Meshy 许可扩大到这些资产。全部保存在本机，未提交或公开发布二进制。

`import_receipt.json`、`icon_import_receipt.json`、`catalog_receipt.json`、`whirlwind-material-receipt.json` 和 `build-native.log` 分别记录导入保存、目录部署与构建；它们不代表游戏测试或用户视觉验收。
