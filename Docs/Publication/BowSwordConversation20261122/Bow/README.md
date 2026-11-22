# 双弓、观峰与光束弓弦

猎人长弓满弓初速 100 米/秒，有效射程 280 米。高地长弓满弓初速 125 米/秒，有效射程 320 米。原厂重力均为 9.8 米/秒²，越过有效射程后开始下坠。旧存档依靠 `bow_traits_revision` 刷新双弓的射程、箭速及重力，同时保留已装部件和强化。普通箭和弦影箭共用服务器弹道。两倍有效射程处命中伤害系数达到枪械公式的 10% 下限。命中场景和离开世界仍按既有生命周期处理。箭尾荧光供玩家观察实际飞行位置。

观峰的 3–6 倍滚轮输入在持续拉弓期间仍被接收。镜口和刻线保持固定，只有镜内景物随倍率缩放；收起镜片后按当前瞄准权重恢复视角灵敏度。远端玩家看到实体镜环转动和模型上的原始玻璃。

山鸣保留 `bow_woodsteel/string/highland_mountain_echo`，当前名称为「光束弓弦」。弦体上下两端和弦扣使用原骨架，亮芯随拉弓弯折。满弓有效命中累计弦鸣，持续 10 秒，上限三层，下一次满弓射击消耗满层，0.18 秒后产生独立弦影箭。弦影保留 80% 物理伤害，在自己的落点进行一次衰减。三段山脉 HUD 使用 V23 图案和 `ResonanceState`。角色死亡、换武器或卸弦按原规则清空累计。

## 恢复顺序

1. 从 [10 月高地长弓包](../../HighlandBow20261028/README.md) 取弦鸣组件、HUD、弓弦形变和箭矢集成。11 月的[观峰发布](../../PojunPeakwatch20261113/README.md)保留了物理镜口；[按功能拆分的运行时代码](../../CodeSkillCleanup20261118/Integration/)包含 `BowEquipment.cpp`、`BowRelease.cpp` 和角色相机。
2. 本目录的 [source-map.json](source-map.json) 标明增量的工程目标、旧版来源与 LF 归一化 SHA-256。`Integration` 的 unified diff 面向正式工程相应宿主，可在具备对应前置版本的恢复副本中以 `git apply --check <补丁>` 匹配上下文，再用 `git apply <补丁>` 写入。明确注明 reconstructed 的条目按旧字段或公开片段重建上下文；上下文已经演进时按每个差异段合入保留的目标源码。完整源码位于 `Runtime`。公共主线中部分较早的运行时代码以配套恢复补丁形式保存。
3. 原厂山鸣三锚模型制作入口为 `SourceAssets/WoodSteelLongbow20261026/MountainEchoV13/author_model.py`。保留其生产源生成的 `MountainEcho_String.blend` 与 `authoring.json` 后，运行相邻 `BeamString20261121/author_beam.py` 生成光束弦 FBX，使用对应的 `import_beam.py` 在已有原版骨架和五金材质的 UE 制作工程落盘。HUD 使用 `MountainEchoAlpineV23/import_hud.py` 和原始项目纹理，并按既有 `ResonanceHUDRepair20261028/repair_materials.py` 处理编译后的材质。镜片由 `SourceAssets/SharedPhysicalOptics20261030/peakwatch_clear_lens.py` 从原版镜片材质和同目录 HLSL 重建。
4. [历史记录](historical-results.json)保存授权项目包的哈希，以及 2026-11-21 的联机与画面对照数值。模型、贴图、音效、引擎二进制包和检测截图由正式资产库保管。公开源码重建出的 UE 包可能因导入器元数据而产生新的文件哈希。

## 历史覆盖

11 月 21 日，弓网络原生检查 95 项和弦鸣检查 44 项均无失败。Flight、Peakwatch 使用真实本机 UDP 监听服务器、客机和新进程重连，每端增加 60 毫秒延迟与 5% 丢包。补上原厂程序化绳段材质后另跑了 Peakwatch，三进程正常退出。独立镜内画面对照中，1600×900 画幅下两档镜口均约为 646×648 像素，景物尺度比为 2.00211，两档准星横线均为 86 像素。灵敏度回执覆盖 236 组输入状态。此次发布整理没有启动游戏。
