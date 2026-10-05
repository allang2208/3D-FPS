# 苍龙能量条：认可参考的纹饰与轮廓还原 V7

> 历史记录：相关旧模型／脚本／回执已按 [本轮整理](enchant-azure-dragon-publication-20261005.md) 归档；原路径通过归档清单查询。当前 V9 被用户判为未达标，后续工作见 `Docs/Backlog.md`。

> 历史版本：用户随后否定平面／立体混合观感，当前制作和加载已改为 [实体能量与收指挥爪 V9](enchant-azure-dragon-coherent-v9-20261005.md)。本页保留当时制作／保存记录；EnergyV6 的转发入口现指向 V9。

2026-10-05 用户反馈 Energy V6 与认可参考完全不像，并要求精确复刻。认可的是设计图；V6 的程序化原创龙首、鳞纹、符号和苍炎没有得到视觉认可。本版以原参考直接提供可见纹饰，避免再次发明近似样式。

## 当前制作

原图位于 `SourceAssets/AzureDragon20261004/EnergyV6/Reference/azure-dragon-energy-approved.png`，1672 × 941，保留原始文件不做重绘或裁切。纹理 UV 取左侧主能量条区域，晶柱、顶部侧面龙首、盘绕符文和苍炎各自制作浅浮雕网格；纹饰、角、龙须、九段晶面及符号均直接取原图。材质按苍青色与亮白细节提取透明度，弱背景反光衰减，并裁去晶尖下方地面反射。

这是随镜头悬浮的 2.5D 特效，优先保留认可视角的形状和细节；没有将单张参考宣称为具备背面结构的完整三维龙。模型总计 45,356 个三角面，四个透明组件／四个 MID，单份原图纹理。保留原相机位置与轻浮，火焰亚像素流动；原符文组件的旋转由顶点反向变换抵消，避免投影轮廓每隔数秒侧转消失。

底部充能通过同一原图坐标控制。未充能晶柱保留暗轮廓，已充部分提亮；头部保持可辨轮廓，火焰随 Fill 增强，满条时还原参考的完整苍炎范围。沿用 `Fill/Age/Reveal/Pulse/Burst` 参数、景深后绘制和一次曝光补偿。无新增 Actor、灯光、碰撞、Tick 或同步加载。

## 接入与恢复

运行原生源码不改，继续引用 `/Game/Weapons/AzureDragon20261004/EnergyV6`。替换四份 `SM_AzureDragonEnergy*` 和四份 `M_AzureDragonEnergy*`，新增 `Textures/T_AzureDragonApprovedReference`；路径中 V6 是既有包名，内容修订为 Reference V7。所有资产保留 `AzureDragonEnergyRevision=6` 归属标签，新增 `AzureDragonReferenceRevision=7` 区分当前内容。

当前作者源和恢复入口为 `SourceAssets/AzureDragon20261004/ReferenceV7`。`run_author.ps1` 导出 Blend／FBX，`run_install.ps1` 编译材质并实际保存资产。旧 EnergyV6 恢复入口在完成接入后转发当前版本，旧程序化作者源保留历史。原图是当前材质的正式输入，不可按旧版本目录名清理。RigV2、VisibilityV5 和 CombatV4 未重导入或修改。

九份资产已实际保存，`ReferenceV7/install-receipt.json` 记录 `complete=true` 与逐项 `saved_assets`。第一批因用户 PIE 暂停；用户回复已停止后，重试时编辑器已退出，使用无界面 commandlet 完成导入／材质编译／保存，没有启动 UE GUI。保存执行日志 `ReferenceV7/install-20261005-191444-commandlet.log`。用户 PIE 时不停止游戏、不写入资产；归属不明或其他未保存修改保持现场。本次无原生修改，不触发额外 Game/Editor 构建。

## 交付范围

本轮参考还原制作包含实际浅浮雕模型的 Blender 预览：

- `ReferenceV7/Preview/reference-vs-model.png`：认可原图与实际模型并列，原图平面的背景仅用于对照。
- `ReferenceV7/Preview/model-three-charge-states.png`：实际模型的 1／9、5／9、9／9 三档。
- `ReferenceV7/Preview/preview-receipt.json`：记录制作预览、非 UE 截图。

九次成功攻击充满、激活 30 秒、龙爪显现、攻击延伸和两次伤害结算沿当前战斗合同。未启动游戏或执行回归；不能将 Blender 预览或资产保存称作 UE 中已达到 100% 一致，游戏观感由用户测试。
