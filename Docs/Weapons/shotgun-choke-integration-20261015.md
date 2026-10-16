# 通用霰弹枪收束器接入

用户已选择初版游戏数值：弹丸散布减少 35%，腰射和 ADS 均生效，其他属性不变。本轮将此前制作的方形外壳方案接入 SUPER90；共享模型、材质、ID 与图标可供之后适配的霰弹枪复用。

## 目录及表现

- 配件：`shotgun_choke`，显示名称「收束器」，安装于 `ue_super90` 的 `muzzle` 槽。
- 共享网格：`/Game/Weapons/CommonShotgun/Choke20261015/Meshes/SM_ShotgunChoke_Box01`。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_choke.png`，由实际源模型制作，沿用灰白金属框样式。
- 安装位置来自当前 native SUPER90 上方枪管的前端圆环，转回 `WPN_root` 局部坐标；旧 `WPN_SOCKET_Muzzle` 标记偏低，未用它代替网格接触面。原厂枪体、骨骼、动画保持原状。
- 网格包含 `Mount`、`Muzzle`、`AimGuide` 挂点；新枪口位置参与已有第一人称、第三人称及枪口烟火/弹道起点路径。卸下后恢复原厂路径。
- 本项是收束器，沿用普通开火声音及噪声规则，不进入消音器分支。

## 数值和存档

唯一数据源为目录 `stats.pellet_spread_mult = 0.65`；`UGunsmithSystem::PelletSpreadMultiplier` 读取已加载目录中的合法枪口选项。原厂默认倍率 1。

该倍率作用于现有弹丸锥角，保留 ADS 的原有散布系数。腰射中心随机偏移 `hip_spread_mult`、伤害、弹丸数量、弹速、射程和后坐力不变；独头弹只有一枚弹丸，因此不增加额外锥角。

本地开火、客户端预测、服务端权威 SUPER90 发射和准星包络使用同一数据值。服务端从其已有装备配方解析，不接收客户端上传的收束系数。

改造能力卡、总览及物品浮窗补充「弹丸散布倍率」与相应增减。目录选项沿用现有 `gunsmith_parts.muzzle` 草稿、应用、卸下、存档、掉落预览与联机装备路径；不另建存档字段。

## 制作与交付记录

制作入口：`SourceAssets/Super90Choke20261015`。`package_runtime.py` 将三档作者 LOD 合成 FBX LODGroup；`install_assets.py` 导入保存共享网格、WS1 材质和图标。表面使用独立复制的真实平直法线；不采用 `/Engine/EngineMaterials/DefaultNormal`。五个材质区保留色调和粗糙度，无额外噪声凹凸。

`catalog_receipt.json` 记录目录与共享图标。后台 RHI commandlet 已完成导入，`install_receipt.json` 的 complete 为 true，保存三档 LOD 网格、五组材质、平直法线纹理和图标共八个资产。

最终 `build_game_receipt.json` 与 `build_editor_receipt.json` 的 exitCode 均为 0，完成 Game 和 Editor 的常规构建。本轮最终未使用 Live Coding，也未主动打开图形编辑器。早期 Game 构建受 HeQueNetAudit 生成代码的成员名遮蔽错误中断；相关源码自行更新后，本任务重试构建成功，没有修改该怪物模块。

未运行游戏、联机、视觉或回归测试，实机效果由用户确认。新的其他霰弹枪尚需制作本枪的安装变换后才能启用该共享配件。
