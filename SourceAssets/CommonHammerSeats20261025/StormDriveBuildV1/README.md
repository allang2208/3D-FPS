# 鸣雷疾驱座

依据用户认可的 `../StormDriveConceptV2/storm_drive_seat_design_01.png` 制作；双手锤通用特殊中央锤座，ID `storm_drive_seat`。

## 制作

钢制双手锤与符文战锤分别使用原装侧接面与柄套下端面。Steel 接面 X = ±0.040 m、下端 Z = 0.865 m；Runebound 接面 X = -0.0354452141 / +0.0345547859 m、下端 Z = 0.842 m。坐标原点保持武器原生根位置，目录偏移为零。替换中央锤座，不新增中间转接模块。

连续锻铁芯、厚壁尖拱、嵌银边线、两侧导雷柱、凹刻雷纹音板、铭文肋柱、嵌入铆钉、阶梯顶盖与柄套均为实体几何。每宿主有独立 4K BaseColor、ORM、切线法线；ORM = AO / Roughness / Metallic，OpenGL 法线在 UE 翻转绿色通道。发光雷纹为真实刻槽中的独立嵌件。

`StormDrive_*_Construction.blend` 保留分件制作源，`StormDriveSeats_Editable.blend` 保存两个最终模型，`Export/` 为 FBX。图标输入来自最终模型的独立灰阶渲染，内置 imagegen 按项目通用金属框制作最终图标。

## 属性与特效

- 重击蓄力速度 +35%；攻击速度 +20%；体力消耗 +30%。
- 锤座常驻金色电弧沿实际安装网格边缘跳动，材质复用镇魂钟黄色闪电。
- 与镇魂钟同时装备时，成功对敌人造成伤害的普通、重击、快速近战及战锤武技命中产生额外金色分叉电弧；不要求符文苏醒，不追加伤害、异常状态或额外音效。
- 命中特效约 0.46 秒，沿目标命中点随动；服务器从既有有效命中入口发送不可靠多播，客户端只绘制表现。最多四组命中电弧复用；常驻电弧形状更新 30 Hz，变换逐帧跟随，近处可见，切换或卸装后隐藏，结束时清理。

## 接入

运行文件为 `ProductionStormDriveLightning.cpp`；挂入现有 `ProductionToolComponent` 的表现更新和 `RecordRuneboundHit` 命中回执。共享改造品质在 `GunsmithModificationTier.h` 登记。两种模型使用 CommonHammerSeats / RuneboundWarhammer 各自资产路径，保留符文战锤原有锤座锚点识别。

`prepare_pipeline.py` 派生制作入口，`import_assets.py` 完成真实 UE 导入与材质编译保存；已有编辑器时通过现有桥执行。`build.ps1` 完成 Editor/Game 必要构建；`publish.py` 仅在两个构建与资产保存完成后合并本改造目录，不覆盖其他选项。

进度以 `production_receipt.json`、`import_receipt.json`、`build_receipt.json` 和 `published.json` 区分。未启动游戏、运行测试、截图或联机验收。

2026-10-25 已完成接入：Editor / Game 正式构建均成功；两款模型、六张 4K 贴图、三份材质和标准图标均已导入、编译并保存。`import_bridge_02.txt` 记录成功的资产保存批次；`published.json` 记录共享特殊改造目录与两款宿主目录的正式接入。此前 PIE 中断留下的一张贴图已按其原始来源接续保存。第一次失败的后台日志保留为 `import-attempt1.log`，不作为成功记录。未主动启动编辑器或游戏，未执行游戏或联机测试。
