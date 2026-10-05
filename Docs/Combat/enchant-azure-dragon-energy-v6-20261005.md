# 苍龙 Energy V6：按用户认可参考图升级

> 历史记录：相关旧模型／脚本／回执已按 [本轮整理](enchant-azure-dragon-publication-20261005.md) 归档；原路径通过归档清单查询。当前 V9 被用户判为未达标，后续工作见 `Docs/Backlog.md`。

> 后续状态（2026-10-05）：用户明确反馈 V6 与参考完全不像，否定本版外观。当前改为 [Reference V7](enchant-azure-dragon-reference-v7-20261005.md)，原认可图纹饰与四层浅浮雕的九份资产已保存。V6 包名仍被运行引用，但其中模型／材质内容为 V7；本篇描述仅保留历史，V6 编译与保存成功不代表用户认可。旧作者／安装入口已转发 V7。

用户于 2026-10-05 认可 `SourceAssets/AzureDragon20261004/EnergyV6/Reference/azure-dragon-energy-approved.png` 并要求按图制作。图为 AI 生成设计参考，不是游戏截图；本轮按既定后台工作规则制作与接入，不执行游戏、截图或验收渲染。

## 表现与几何

- 尖端收束的八面半透明晶柱，实际厚度与切面；材质叠加龙鳞刻纹、晶面亮线、三股上行能流、清晰液面及九档刻度。未填充区保留低透明玻璃轮廓，蓄能严格从下向上。
- 顶部建模苍龙侧面龙首，含盘曲颈部、上下颌与牙齿、双角、双眼、眉骨、两条须及颈鳞／背棘。表面保留半透明苍青能量质感，边缘和眼睛明亮；随能量渐醒，满能量增强。
- 三维螺旋符文绕晶柱缓慢旋转，25 组原创符号，真实前后空间关系；共用一个网格，没有逐符号 Actor 或 Tick。
- 苍炎在一个有界透明平面内分外焰、白青内焰、侧焰与细烟缕，上行扰动；高度／宽度／密度随 Fill 增强。满能量产生细光环，鳞片形光屑最多 12 个解析槽，命中脉冲与召唤盛燃沿原事件。
- 镜头附着、视场／宽高比适配、微浮动与转向惯性沿原拥有者本地显示。增大整体可读尺寸，限制到屏幕左边的窄列，不加入不透明面板。

## 运行与玩法

`UAzureDragonEnergyComponent` 预加载并复用晶柱、火焰、龙首、符文四组网格／MID；沿现有 `TG_PostUpdateWork` 更新。公开 API 不变，新增字段附在类末端。只替换能量条表现，不修改命中／伤害入口：9 次成功攻击充满，30 秒激活，激活期按剩余时间燃烧消耗；龙爪立即显现与源时钟攻击同步、范围延伸及两次伤害结算沿当前 V4/V5 逻辑。

资源异步预载，显示 Tick 无磁盘读取、同步加载、纹理生成、场景遍历或资源等待。作者导出共 11,702 个三角面，四个拥有者可见组件，无碰撞、阴影、导航或动态灯；透明材质景深后绘制，仅做一次曝光补偿。实例与 MID 随组件 EndPlay 清理；停用或死亡隐藏全部四层。以上是实现预算，未测帧时间。

## 可重建源与落盘

- 作者源 `SourceAssets/AzureDragon20261004/EnergyV6/author_model.py`，Blender 源 `AzureDragonEnergyV6.blend`，导出 `Export/*.fbx` 与 `Export/meshes.json`。
- 四份同源 HLSL 与 `install_ue.py`。按 `run_author.ps1` → `run_build.ps1` → `run_install.ps1` 进行后台制作、必要 Game/Editor 构建、材质编译和实际导入保存。
- 资产目录 `/Game/Weapons/AzureDragon20261004/EnergyV6/{Meshes,Materials}`；运行软引用切到此目录。保留旧 EnergyV3 作为恢复源；Fab 龙爪与 RigV2 骨架／动画不重导入。
- 保存完成程度见 `EnergyV6/install-receipt.json`；构建与资产交付状态见 `Saved/AzureDragonEnergyV6/delivery.json`。只有实际导入和保存后才记为已接入，作者脚本不等于已保存资产。

龙首、符文与晶柱为本次原创 Blender 制作，参考图为本次对话生成且获用户认可；不复用 Fab 新模型或外部龙首贴图。苍龙原爪沿既有 CaptainHC Fab 许可记录。本轮未实机测试／渲染验收，最终观感由用户确认。
