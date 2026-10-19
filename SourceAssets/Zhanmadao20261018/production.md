# 斩马刀：首版游戏接入

2026-10-18。用户指定采用下载的 Meshy 模型，模型长度匹配玄螭镇岳，按武器标准工作流先接入游戏。独立定义为 `ue_zhanmadao`。

**当前改造／图标修订**：[CommonModsV2](CommonModsV2/production.md) 已接入 20 项通用改造，保存 13 个适配网格和 9 个图标包。首版临时 Blender 边框已退役，四张原厂母图按认可边框使用 imagegen 重做；通用选项直接使用共享标准图标。以下首版制作记录保留作为历史。

**唐刀双刀身接入**：[TangDaoBladesV1](TangDaoBladesV1/production.md) 记录破锋燕翎／腾云游龙的专用适配网格、标准图标复用、第三段攻击与保存构建回执。

**符文显示与走向修复**：[RuneSurfaceV1](RuneSurfaceV1/production.md) 记录六款刀身的原生符文材质与随刃曲线投射，覆盖现有五种通用符文。

**背嵬传说符文（2026-10-18）**：[接入记录](BeiweiRuneV1/integration.json) 与 [交付回执](BeiweiRuneV1/delivery.json)。已按认可设计接入金色“精忠報國”行书、银灰金属框图标，以及重击、上挑、旋风、冲刺、快速近战的伤害 ×1.5／判定范围 ×1.25；普通连段及其刀身替换动作不受这两项加成。武技释放时沿真实刀刃轨迹留下约 0.24 秒的金色剑气，接入第一人称及世界身体表现，纯视觉、不追加伤害。正式保存 17 个资源包并发布目录，Editor／Game 构建成功；未启动游戏、联机或视觉验收。重新启动游戏后在斩马刀符文槽安装“背嵬符文”。

**攻速调整（2026-10-18）**：按用户反馈降低斩马刀攻速，`attack_seconds` 从 1.775 调为 **2.04125 秒**，采用当前钢铁战锤的重型近战基础档；普通攻击／连段整体播放速率乘以原来的 `1/1.15`，即降低约 13.04%。原先目录基础与镇岳、高地大剑一致；本次读取的 PIE 存档斩马刀使用轻量护手（×1.05）和凝碧星核（×1.15），改造加速合计 ×1.2075，该效果仍保留。不将配装差异归为基础时钟错误。伤害、攻击距离 +25%、改造与独立武技时钟沿用原设置。`publish_catalog.py` 固定新基础值；`ReloadProfile` 仅同步已有斩马刀的 `attack_seconds`，不直接改写存档文件。新物品读取目录，已有物品需重进存档；后台构建回执使用 `speed-01` 后缀。未运行游戏或实机测试。

本次攻速修订的 Editor／Game 后台构建均已完成，`build-FPSGAMEEditor-receipt-speed-01.json` 与 `build-FPSGAME-receipt-speed-01.json` 均记录退出码 0。未启动编辑器或游戏，实际手感由用户重进存档后测试。

## 来源和尺寸

### 赤霄刀身外观接入（2026-10-18）

按用户“先建模接入”完成独立 `blade_1/chixiao`：可编辑母版 [Chixiao_Blade_Editable.blend](ChixiaoBladeV1/Chixiao_Blade_Editable.blend)，三档 LOD 为 28,076／12,172／5,372 三角形。实际原装刀根尺寸、0.6 mm 隐藏插接量与整刀 160.1313919 cm 纵向长度保留；新制宽腹厚脊、修长刀尖、银白刃口、凹入暗红嵌线及两面刀根金云纹。

共 9 个 UE 资源包已保存并发布：网格、3 张 PBR 图、普通／旋风各 2 份材质、标准银灰改造图标。现有五种通用符文及背嵬沿新刀身中部曲线适配，已有背嵬武技剑气继续读取实际刀身端点。可在斩马刀刀身Ⅰ槽选择“赤霄”；选项本轮只有外观，之前的增伤／破韧／120° 横斩仍为未实施提案。

Editor 与 Game 复用同工程在本轮头文件修改后完成的成功构建，日志及时间记录在 [delivery.json](ChixiaoBladeV1/delivery.json)。必要图标生产使用实际模型灰阶渲染再由 imagegen 按认可金属框成图；没有运行游戏、追加自测或制作验收渲染。重启游戏加载新目录后由用户体验。作者／重建入口见 [integration.json](ChixiaoBladeV1/integration.json)。

- 原件：`Original/Meshy_AI_Crimson_Crescent_Blad_1017171549_texture.glb`，从用户 Downloads 复制保留；模型及内嵌贴图来自用户提供的 Meshy 文件，不重新生成外观，不声明已获公开再分发许可。
- 尺寸参考来自当前镇岳 BladeV3 可编辑源的刀身、护手、握柄、柄尾四个实际网格。刚性长度 **160.1313919 cm**，剑尖 Z **120.0000048 cm**，柄尾 Z **-40.1313871 cm**；柔性剑穗不计入武器刚性长度。
- 原斩马刀长轴为 glTF X，刀尖朝 -X；统一旋转为武器局部 +Z，并整体等比缩放 **0.8421713777**。没有减面或重绘原贴图。准确参数及来源见 `fit_manifest.json`。
- 原厂刀身、护手、握柄、柄尾按模型连接处拆分；切面保留原 UV 与法线并封闭。完整整刀另供世界物品路径使用。采样点取实际弯曲刀尖与刃根，而非包围盒中心线。

## 接入路径

| 项目 | 实际入口 |
|---|---|
| 制作源 | `Zhanmadao_Fitted_Editable.blend`、`Zhanmadao_Modular_Editable.blend` |
| 制作脚本 | `prepare_model.py` → `author_modules.py`；独立的背包与原厂部件图标制作器 |
| UE 导入 | `import_background.ps1` → `install_assets.py` |
| UE 资源 | `/Game/Weapons/Zhanmadao20261018/V1` |
| 物品与公式 | `items.json` 的 `ue_zhanmadao`；`combat-weapon-formulas.json` 同名项 |
| 装配 | `zhanmadao-modules.json`，复用 `ModularSwordVisual` 的持握、改造、预览和掉落装配 |
| 近战动作 | 直接共享镇岳当前双手近战序列和时钟，沿用 FrostArms 原生 V7 裸手装备外观配置；不复制整套动画 |
| 攻击距离 | `melee_reach_cm=225`，普通双手剑基准 180 的 1.25 倍；沿用现有判定、技能、角色跨步与快速近战规则 |
| 首版数值 | 基础伤害、攻速、强化及力量／精神公式暂沿用镇岳；无其他专属特效 |
| 改造 | 独立原厂四部件和共享普通数值／符文选项；未制作专属改造，不接入镇岳专属符文与护手 |
| 图标 | 实际模型生成的彩色背包图；四款原厂部件为灰阶金属框图，通用改造使用既有共享图 |
| 获取 | `ColdSteelWarehouseModel.cpp::GrantStartingArmory` 的独立幂等仓库发放项；不直接修改玩家存档 |
| Cook | `Config/DefaultGame.ini` 新增 `/Game/Weapons/Zhanmadao20261018` |

运行时仍使用现有双手近战分类、主手／副手占用、快捷栏、丢弃拾取、保存和服务端命中路径。斩马刀与镇岳有独立物品 ID 和模型目录；模型尺寸不额外乘到距离数值上。

## 落盘与验收边界

制作源和导出已保存。2026-10-18 01:24 的后台 commandlet 已保存 19 个资产并发布目录：三张 PBR 贴图、主体与旋风表现两份材质、五个静态网格、一张背包图标、八个原厂部件／分类图标。`import_receipt.json` 为 `complete=true`，`catalog_receipt.json` 为 `catalog_saved=true`，commandlet 退出码为 0。

Editor／Game 构建分别保留 `build-*-receipt-*.json`。后台执行脚本等待现有批次锁，不结束其他进程，不启动交互编辑器。

- Editor：2026-10-18 01:37 后台构建成功，退出码 0，`build-FPSGAMEEditor-receipt-01.json` 已保存。
- Game：2026-10-18 01:48 后台构建成功，退出码 0，`build-FPSGAME-receipt-01.json` 已保存；输出为 `Binaries/Win64/FPSGAME.exe`。

未运行游戏、PIE、联机测试、截图或视觉验收。图标输出是必要游戏素材制作，不是验收渲染。实际握持、挥砍、格挡及长刀观感交由用户体验。
