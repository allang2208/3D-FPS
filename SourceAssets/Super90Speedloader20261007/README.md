# Super90 管式快速装填器（2026-10-07）

**当前动作状态：旧版手部动作被用户否定后，已按视频 40–44 秒制作 Reference R2。** 制作源和导出文件已更新；导入、构建及最终交付状态见 `../Super90MotionRevision20261007/README.md`，原分段计划见同目录 `PLAN.md`。未做游戏视觉验收，不作为已获用户认可的动作模板。

入口：M4 Super90 → 改造 → 装填装置 → 管式快速装填器。默认仍为逐发装填。使用既有枪匠 Installed/Draft、装备存档、属性汇总与图标缓存流程，选项 ID 为 `super90_tube_loader`。

## 动作与结算

- 参考用户提供的 BV11wTe6sEsS 的 40–44 秒节奏：右手持枪侧倾，左手取管、对口、推送、撤管并回握。未提取或使用视频中的游戏模型与动画文件。
- 原创游戏配件包括留在枪上的导向件、换弹时可见的装填管与手驱动推杆。原生 V7 骨架不变；新动作沿用当前裸手，装备外观继续跟随。
- 普通、空仓分别提供补入 1–7 发的动作，共 14 段；另有只完成枪机动作的续接片段。各数量版本共用入仓前缀，打断时切换对应数量版本并保持播放时钟。
- 每发到达入仓接触点才调用既有弹药事务。开火/瞄准请求结束补弹时，先完成正在入仓的一发，再撤管回握。硬中断沿用现有动作仲裁；未入仓的弹药不扣除。
- 空仓末段包含左手操作枪机释放，完成后清除未上膛状态。纯上膛续接不生成或消耗装填器弹药。
- Reference R2 源为 60 FPS：第一发 90/60 秒，后续间隔 4/60 秒；完整 7 发源时长普通 146/60 秒、空仓 182/60 秒。保留基础 1.3 倍速度及现有角色/配件倍率。实际动作按本次缺弹数量缩短。
- 管式装填模式的面板普通换弹时间表达完整装填器操作；原厂模式仍表达单发装填。选项说明已写明两者口径。
- 四类既有前握把配置各保留 15 段装填器左臂差量、12 段原动作及 3 段战术冲刺；战术直握把沿用现有直握把家族。原握把导入入口也会保留这些扩展。
- 新模型使用项目 WS1 共享母材质的独立金属/聚合物实例、独立 UV 和平整结构法线，不投射原枪旧图集。
- 改造预览及整枪图标包含固定导向件；临时装填管在动作外隐藏，改造展示副本显式排除 `WeaponReloadProp`，不把其范围计入整枪构图。

## 已落盘

- 可编辑模型与动画：`Super90_Speedloader_Editable.blend`；FBX 在 `Exports/`。
- UE 模型、材质和动作：`/Game/Weapons/Super90/Speedloader20261007`。
- 四份既有握把资产：`/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_*`，修改前包保存在本目录 `Before/`。
- 原创部件图标素材场景：`Speedloader_Icon_Editable.blend`。`speedloader_icon_source.png` 仅用于实际配件图标制作，不是游戏验收渲染。
- 正式图标母图：`speedloader_framed.png`；项目 PNG 与 Texture2D：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/reload_device_super90_tube_loader`。
- 图标使用内置 imagegen，输入为实际新模型图和 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png`。原始工具结果保留在 Codex generated_images；完整提示词见 `icon_prompt.txt`。
- 导入保存回执：`import_receipt.json`；改造目录发布回执：`catalog_receipt.json`。
- 原版构建日志：`Saved/BuildEditor/build-20261007-184036.log`。Reference R2 的 19 份资产保存回执位于 `../Super90MotionRevision20261007/import_receipt.json`，当前原生构建 Succeeded / Target is up to date，日志为 `Saved/BuildEditor/build-20261007-205111.log`。
- 未启动 UE 编辑器或游戏，未进行自动测试、动作预览、截图或游戏验收；游戏表现交由用户测试。

## 重制入口

在工程根目录，依次运行 Blender 后台 `author_speedloader.py`、`Tools/ModularOutfit/Run-Authoring.ps1 -Script SourceAssets/Super90Speedloader20261007/import_assets.py -Log SourceAssets/Super90Speedloader20261007/import_assets.log`，然后用 Python 运行本目录 `publish_catalog.py`。发布器只更新 Super90 的装填装置槽，并要求资产已成功导入。不要用最初的整枪目录发布脚本覆盖后续瞄具、前握把等配置。

模型和动画重制继承既有 Super90 源场景与手臂源的许可边界；新配件几何、动作编排和本次脚本为本项目制作。参考视频只用于动作节奏参考。

## 启动崩溃修复（2026-10-07）

用户反馈 `InitializeForegripAnimations` 第 45 行访问异常。既有崩溃转储表明，DLL 中该函数按角色偏移 `0x1420` 读取待机动画，而当前角色类型的对应偏移为 `0x1460`；错误读取的值是 `0x40C0000000000000`。启动阶段建立 M4 前握把动画映射即崩溃，尚未恢复玩家装备。修复对象为采用不一致角色布局的原生编译产物。

`Tools/Build/Build-Editor.ps1` 新增显式 `-RecompileGameplay` 恢复选项：保留原 DLL/PDB，清除 FPSGAME 和 ColdSteelNet 的生成目标文件，强制 UHT，并以 `-NoUBA` 从当前源码重编译后完整链接。源码、Content 和玩家存档保留。

本次 345 个构建步骤完成，结果 `Succeeded`，FPSGAME 与 ColdSteelNet DLL 已重新落盘。日志：`Saved/BuildEditor/build-20261007-190235.log`；原 DLL/PDB 与失效目标文件清单：`Saved/BuildEditor/layout-recovery-20261007-190235/`。未启动 UE、未运行游戏测试，运行结果由用户确认。
