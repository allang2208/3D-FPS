# 铸造台写实表面与淬火 V5

用户要求改善铁砧的卡通质感、替换已有木材、闭合桶板、接入水体效果，并增加淬火镜头及大量水蒸气。

## 制作与来源

- `author_geometry.py` 从已认可的 `CastingStation_AnvilReference_Source.blend` 继续制作，保留铁砧形状、尺寸、砧面高度、工具、货架及建筑占地。桶壁改为共顶点封闭环壳，浅槽表现板缝，保留内壁和桶底；水面使用 12 层、96 段圆盘。厘米尺寸与原枢轴不变。
- `materials.py` 复用项目现有 Normandy `T_WoodSurface_00A` 木材扫描，使用独立的桶／台座材质，纵向纹理与局部湿润变暗；不再继承旧材质的腐木、泥土及石材细节法线混合。
- 铁砧沿用已有高炉铁材扫描纹理，保留原砧面顶点分区。铁体使用较暗的金属反射，砧面降低粗糙度；小尺度法线强度降低，去除原先近似岩石的大块起伏。未新增下载资源，既有资产许可边界不变。
- 水体复用 Clearwater 的 `T_ClearwaterRipples_N` 以及现有 UE SingleLayerWater 光学接法，按桶深调整吸收与散射；`BasinWaves.hlsl` 提供厘米尺度微波、入水冲击圈及局部扰动，不把海面大浪直接套到桶内。
- UE 5.8 Nanite 的材质门控不支持 SingleLayerWater，含水材质分区的整台网格使用原三角面；独立木桶仍保留 Nanite。不修改全局渲染设置。

## 动作、接触与预算

`ForgeQuenchPresentation.cpp` 提供 5.8 秒收尾：抬起 → 移到桶口 → 刃部浸入 → 停留 → 提起冷却工件。相机沿连续缓动转向桶口，保留工具握点，再按当前相机解算现有腕肘约束。可编辑动作由 `Tools/Forging/author_quench_motion.py` 写入 `Authored/Forge_Quench_Motion.blend`，不覆盖已认可落锤动作。

真实水面来自 `QuenchSurface` 插槽。剑刃线段穿过桶内水面才开始冷却、蒸汽及波纹；未入水不会预先冒汽。当前铸造台的水材质采用独立 MID，结束／取消／销毁时恢复原材质，不向其他水桶传播事件。

复用原 Mantaflow 图集与实例池；常规热烟仍最多使用 18 槽，淬火可用 56 槽。蒸汽从交点附近向上膨胀、侧向翻卷并衰减，镜头过近和收尾时渐隐。火星、击打时间、品质、材料、领取／废弃和存档逻辑保持原合同。数量是制作预算，未采集性能。

## 接入

`install.py` 保存专属 V5 材质，并重导入现有 `SM_CastingStation`、`SM_CoolingBarrel`、`SM_CoolingWater`，绑定独立铁砧材质；原网格副本保留在 `RealismV5/Before`。原 `install_station.py` 已路由到此版本，避免后续重装覆盖。

### 黑铁参考图调整（2026-09-27）

用户进一步指定采用参考图中的哑黑铁砧外观。`M_BlackenedAnvil` 使用低亮度中性黑氧化表面，减弱泛白反射和凹凸，仅在既有顶点磨损分区保留暗灰砧面与边缘亮痕。主体粗糙度 0.72–0.82，受锤区 0.48–0.60；主体采用较低金属度表达氧化层，受锤区恢复部分金属反射。

`install_black_anvil.py` 只保存此材质并绑定整台、独立铁砧的 `AnvilSteel` 等铁砧槽，不改几何、尺寸、桶箍、台架、钳子或水体。完整重建入口也已同步这一区分；原 `M_WorkedAnvil` 继续服务框架等部件。保存结果见 `black-anvil-*.json`，未启动游戏或制作验收渲染。

### 随风挂件与高炉做旧 V7（2026-09-27，已保存）

在 V6 的既有模型上拆出无挂件台体及四个独立挂件，枢轴设在吊眼与挂钩接触点。台架和挂钩保持固定。运行时 `UCastingToolRackComponent` 复用高炉烟雾的主风、雨天阵风与遮挡数据，按 PKM 式阻尼弹簧和限位驱动轻微摆动，锤子风响应较低。

暗铁材质改为直接继承高炉铁质扫描母材质；黑铁砧保留黑色主体，使用该扫描的颜色、AO、粗糙度及金属度形成氧化变化和磨损工作面。木材压低黄色饱和度并加深纹理凹处，保留桶体湿润分区；水材质及淬火过程不变。此节替代上文 V5 黑铁砧的固定粗糙度数值。

`install_wind_weathering.py` 完成该批资产备份、材质保存与新网格导入。制作和构建状态见 `Docs/Gameplay/casting-wind-weathering-20260927.md`；不自动测试或渲染。

### 工具挂架 V6（2026-09-27）

旧挂钩位于两根钳柄上端之间，钩体未接触钳柄，因而没有承重点。`author_tool_rack.py` 重做静态悬挂钳：仅一根钳柄末端带锻接挂环，两柄继续由铆钉连接；环孔上沿落在 J 形钩的水平承重段，钩头上翘防脱，底板与铆钉固定到原横梁。

架上共四件工具，沿横梁的 X=8/27/43/57 厘米排列：铁钳、横刃锻造锤、带细齿的平锉、拨火钩。三件新工具使用既有木柄和做旧钢材，均由柄尾金属挂环支撑。原架子高度、建筑占地、铁砧及木桶几何保持不变；本次不修改玩家手持的 `SM_ForgeTongs` 或锻造动作。

主几何作者已调用此模块，并导出整台及独立 `SM_BlacksmithTongs`。原源文件位于 `BeforeRackV6`，可编辑模型为 `Authored/CastingStation_RealismV5.blend`。`install_tool_rack.py` 只导入整台和静态铁钳，沿用当前材质、保留已有插槽并更新钳子插槽；保存回执为 `tool-rack-*.json`。

用户结束运行后，已通过现有编辑器的互斥 MCP 批次完成导入和保存，返回 `success=True`；回执为 `Saved/casting-tool-rack-install-r2-20260927.txt`。整台和独立静态铁钳均已更新，黑铁砧、木材和水体材质沿用当前绑定，原网格副本保留在 `RealismV5/BeforeRackV6`。无 C++ 修改，无需常规编译。未截图、渲染或运行测试。

源码、FBX 与两份可编辑 Blend 已完成。后台 Python commandlet 已导入并保存 3 个网格、5 个材质及独立铁砧的材质绑定，原网格副本也已保存；安装清单见本目录 `install-*.json`。执行日志为 `Saved/casting-realism-commandlet-20260927.log`，结果为 `Success - 0 error(s), 5 warning(s)`，警告为 ModelingService 的既有 Python 导出命名重复。

`FPSGAMEEditor Win64 Development` 常规构建已完成，结果为 `Succeeded`，日志为 `Saved/BuildEditor/casting-realism-20260927.log`。未启动图形编辑器或游戏，未截图、渲染或自动测试；实际观感、手臂与桶的接触及操作由用户测试。

> 2026-09-27 发布整理：作者快照 BeforeRackV6 与 BeforeWindWeatheringV7 已移至 trash/forging-publication-20260927/SourceAssets 下对应相对路径。当前 Authored、初版总装与 V3 输入保留；UE 内部资产包未随作者快照移动。详见 Docs/Gameplay/forging-publication-20260927.md。
