# 散弹枪通用消音器 / SUPER90 首发接入

用户于 2026-10-15 要求制作散弹枪消音器，初版仅接入消音、减弱火光和降低敌人听声范围；后续要求将三款散弹枪枪口件归为特殊改造，并为消音器配置常驻数值。

当前目录此前仅有原厂枪口、收束器与鸟笼消焰器。本次增加独立 `shotgun_suppressor`，不替换上述选择。

## 模型与素材

- `ShotgunSuppressor01_Editable.blend`：圆角长壳、上置出口、下置主体、纵向侧筋、端盖与独立后座。原创建模，复用前两款配件的美术作者流程与 SUPER90 接座基准。
- `Exports/SM_ShotgunSuppressor01_LOD{0,1,2}.{fbx,glb}` 与 `SM_ShotgunSuppressor01_Lods.fbx`：游戏网格和统一 FBX LODGroup。
- 五组 WS1 材质，平直表面、几何圆角、加权法线与平面法线贴图，不使用表面噪声凹凸。
- `muzzle_shotgun_suppressor.png`：当前正式图标，来自 `../ShotgunIconsFramed20261015/Final`，以实际模型单件图和认可金属框母版经内置 imagegen 重制。`author_icon.py` 恢复最终母图；`ShotgunSuppressor_Icon.blend` 为已否决简化边框的历史场景。
- `Audio/S_Super90_Suppressed.wav`：由当前用户选定的 SUPER90 普通枪声加工，保持原声道、时长与音高；属于游戏设计音色。来源与制作参数见 `audio_provenance.json`，继承源素材权利范围，不重新声明公开分发许可。

## 接入

UE 资产根：`/Game/Weapons/CommonShotgun/Suppressor20261015`。

使用既有 SUPER90 上枪管安装面，UE 原生坐标 `(0,-49.9307,-74.43155)` cm，配件 +X 映射原枪 -Y，枪口特效跟随前端 `Muzzle` 插槽。各枪型仍须按自身接口适配，当前正式选项仅启用 SUPER90。

目录 `Content/ColdSteelData/gunsmith.json` 新增独立枪口项，沿用现有配方、装备存档和第三人称附件同步。`IsMuzzleSuppressed` 识别该项，复用本地与服务端既有消音、枪口特效和听声分支；SUPER90 专属音源在装备时固定绑定，避免继承步枪音源。

当前 `stats` 为后坐力 ×0.75、稳定性 ×1.20、子弹速度 ×0.85、开镜耗时 +10%；伤害与弹丸散布不变。保留消音特效，与收束器和鸟笼互斥。

收束器、鸟笼消焰器与散弹枪消音器均由 `GunsmithModificationTier.h` 归为特殊改造；收束器与鸟笼的原数值保留。此次分类与调参记录位于 `SourceAssets/ShotgunMuzzleSpecial20261015`。

## 制作状态

模型导出、图标与音效制作完成；`install_receipt.json` 与 `audio_import_receipt.json` 记录实际保存的 UE 包，`catalog_receipt.json` 记录枪匠条目。原生编译结果单独记录，不以素材落盘替代编译结果。

最终共享工程的 Game / Editor 常规构建均已成功，正式 EXE / DLL 已更新；结果与日志来源见两份 `build_*_receipt.json`。先前 Live Coding 取消、Game 构建排队超时不作为成功证据。用户授权关闭 UE 后，编辑器保持关闭，没有自动重开。

未试听、未启动游戏、未进行运行时或联机测试；交由用户体验。图标为生产素材，不属于整枪效果验收。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90Suppressor20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
