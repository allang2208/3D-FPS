# 篝火：Realistic Vol.2 原生序列火焰（2026-10-12）

用户在本地素材比较后回复“继续”，确定采用首选 Realistic Starter VFX Pack Vol.2 的 `P_Fire_Small` 作为篝火新火焰来源。本轮已制作并保存独立 Niagara 系统和三个材质，未播放、截图、渲染或做游戏验收。素材选择授权不代表新观感已获认可。

## 新资产与结构

运行系统：`/Game/Building/Campfire20261012/Realistic/NS_CampfireRealisticFlame.NS_CampfireRealisticFlame`。

| 发射器 | 材质与实际源 | 图集 | 生成率与寿命 |
| --- | --- | --- | --- |
| ShortNativeFlames | `M_CampfireNative8x4`，复制原 `M_Fire_B`，使用 `T_Fire_D` | 8×4，按粒子年龄播放 0～31 帧并插值 | 7/s，0.85～1.15s |
| RollingNativeFlames | `M_CampfireNative6x6`，复制原 `M_Fire_C`，使用 `T_Fire_F` 和原遮罩 `T_Fire_B` | 6×6，按年龄播放 0～35 帧并插值 | 6/s，1.0～1.35s |
| SparseNativeSmoke | `M_CampfireNativeSmoke`，复制原 `M_Smoke_C`，使用 `T_Smoke_A/B` | 8×8，按年龄播放 0～63 帧并插值 | 1.2/s，1.9～2.6s |

三个材质与系统都保存在同一新目录。原始 `P_Fire_Small` 的 18 层未整体复制；只保留上述两类原生火焰形态和少量薄烟。没有持久实心火体、程序化燃烧场、热扰动、火星或粒子灯。

火焰使用原材质的序列、遮罩、ParticleColor、透明度运算和 DepthFade 接线。专用副本开启 Niagara Sprite 使用标志，关闭折射；接地 DepthFade 调整为火焰 4cm、薄烟 7cm。火焰发光末端加一次曝光补偿，未重写成统一纯色噪声 shader。`M_Fire_C` 的 Dynamic X/Y 沿用遮罩偏移、透明度指数语义。原演示中极高且含蓝紫的颜色曲线改为克制的暖色增益，避免照搬其灯光层数和能量。

Niagara 容器来自项目已有的循环系统，原发射器全部移除；制作助手只复用标准 CPU Sprite 生命周期和属性绑定，最终三个 renderer 均指向本轮独立的 Realistic 材质。原生火焰纹理提供形态，没有使用被否定的 DenseFlame／Tongues 材质。

## 接入约定与范围

- 保持现有每场景最多 8 个可见篝火系统、30m 进入／35m 保留范围，由原共享调度器管理。
- 不新增光源，继续由篝火 Actor 提供原有 350lm、无阴影灯。
- 系统使用局部空间、厘米单位。现有组件相对 Z=20cm；火焰出生时名义底部约在组件上方 6cm。固定边界为 `(-85,-85,-12)`～`(85,85,165)`cm，覆盖薄烟上升。
- 生成率与最大寿命推算的保守同时存活量约 25 个粒子/系统，属于制作参数估算，不是性能测量或运行采样。
- 石圈、木材、生存效果、燃料、共享事务、UI 与存档未由资产子任务修改。主任务负责切换原生 `UNiagaraSystem` 引用和必要源码构建。
- 原包及上一轮被否定的资产保持原样；新包可以独立回退，不覆盖第三方素材。二进制和原始纹理按本机已有许可边界保留，不提交公开分发。

## 可重建源与实际保存

作者：`Tools/Building/author_campfire_realistic.py`。每次只允许保存上述新目录；检测未保存目标包并拒绝覆盖，制作前后比较原始素材及旧火体散列。

原始结构依据：`SourceAssets/Campfire20261012/InventoryExports/P_Fire_Small.t3d` 和 `local-fire-cascade-profiles.json`。本轮参数、来源、原件散列及新文件散列保存在 `SourceAssets/Campfire20261012/Realistic/delivery.json`；制作后的 renderer、图集尺寸、帧混合、纹理及透明度输出读取保存在同目录 `asset-readback.json`。

后台 `author-realistic-cmd.log` 于 15:15 UTC 完成：Niagara `valid=1`，四个包保存成功，退出码 0，UE 汇总 0 错误、5 个既有 Python 命名警告。先前项目模块的初始化崩溃本次未再出现；本资产任务没有修改怪物代码。后台使用 NullRHI，不能将此记录表述为 SM6 实机视觉或性能验收。

本轮没有创建游戏世界、运行 PIE／游戏、渲染、截图或自动测试；实际亮度、通透性、火舌变化与接地效果由用户体验确认。
