# 雷暴／暴风雪翻卷乌云 RollingV1

用户要求参考百目黑烟或沉匣绿色毒雾重做乌云。两者共用百目 SmokeVisibilityFixV21 的 Mantaflow 密度图集；本次派生独立魔法资产，采用深灰／冷灰配色，保留怪物母版与原有法术规则。

## 制作与接入

**后续用户反馈与修订：** 用户截图否定暴风雪的细小网格云块，要求直接复用雷暴乌云。暴风雪现改为复制当前雷暴的五层云发射器，保留连续重叠的分布、完整云团尺寸、深灰层次和翻卷材质，去掉原 IndoorCloud 网格以及雷电发射器；室内单元仅约束所在位置的净空与墙边宽度。详见 `Docs/Skills/blizzard-storm-cloud-reuse-20261012.md`。以下初版 50 云团配置为被替代的制作历史。

- 作者：`Tools/Skills/build_rolling_storm_clouds.py`。
- 密度源：`SourceAssets/StormCloudRolling20261012/RollingCloudDensity.hlsl`。
- 生产目录：`/Game/Skills/StormClouds/RollingV1`；加入 `DefaultGame.ini` 的 cook 目录。
- 两个材质：`M_RollingStormCloud`（区域／头顶）、`M_RollingGatherCloud`（近手）。
- 三套 Niagara：`NS_StormDomainCloud`、`NS_BlizzardStormCloud`、`NS_BlizzardGatherCloud`。
- 实际引用：`FPSElectricMagicComponent.cpp` 与 `FPSBlizzardZone.cpp` 的异步加载数组。

密度取现有图集 R 通道，双帧插值；连续时间驱动密集段往返、每团独立相位、缓慢形变与边缘散开。浓度不再跟随整次法术归一年龄进入爆炸烟尾的消散段。材质深度测试保留，深度淡出为世界 6 cm／近手 3 cm；世界云固定竖直对齐，近手云保留自身空间与相机朝向。近手材质单独启用 responsive AA，沿用精确运动向量配置；不添加折射、灯光或阴影。

雷暴保留原五层共 48 个核心粒子和边缘层、电光；翻卷云的位置每帧读取 CurrentPosition，XYZ 跟随现有头顶锚点，厚度仍受 CloudThickness 限制。颜色由暗灰云底到较亮云顶过渡，边缘较薄。

暴风雪区域云当前使用雷暴的 48 个核心云团及约 8 个边缘云团，保留 IndoorV5 的 25 单元局部地面／净空／宽度字段及区域生命周期。先按雷暴结构生成连续云层，再由实际云团位置查询所在单元并约束高度，不再按单元中心排列云片。90～180 cm 净空继续渐变显隐；雪、贴地寒雾、落冰、地霜、预览和伤害逻辑沿用 IndoorV5。

近手凝聚云保留 ChargedV3 的 29 个粒子、局部空间、手部跟随、运动和尺寸，只换为独立翻卷材质与冷灰配色。

## 成本与恢复

复用现有图集，不新增密度纹理；材质每像素两次图集采样。主体粒子数、区域并发上限、运行组件数和已有距离预算保持。此处记录制作配置，不代表实测性能。

完整恢复时先恢复百目 SmokeVisibilityFixV21、雷暴 StormDomainV2、暴风雪 ChargedV3／IndoorV5 输入，再执行本作者。旧作者仅重建旧目录，不覆盖 RollingV1；运行引用以 RollingV1 为准。追加参数模块各自保存稳定 metadata，重复执行复用本层模块，不覆写前置单元查询与源模块。

在 UE 未运行且无其他 UE／UBT 作业时，通过 `UnrealEditor-Cmd -run=pythonscript -script=Tools/Skills/build_rolling_storm_clouds.py -unattended -NullRHI` 保存；实际命令使用工程与脚本绝对路径。若编辑器已经运行，沿既有 MCP 批次互斥执行，目标包有未保存修改时停止以保留现场。

## 本轮状态

源码、作者、密度 HLSL 和 cook 接入已写入，两个材质和三个 Niagara 已实际编译、保存。资产 commandlet 退出码 0，日志汇总 0 errors／9 warnings（五项已有建模插件 Python 重名提示、四项旧 Blizzard 输入资产加载时的插值标记提示；新副本按 NoInterpolation 编译保存）。实际保存回执：`SourceAssets/StormCloudRolling20261012/asset-authoring.json`；本轮日志目录：`Saved/StormCloudRolling20261012`。

必要构建已完成：最终 `FPSGAMEEditor Win64 Development` 返回 Succeeded／退出码 0（当前目标已更新），`FPSGAME Win64 Development` 返回 Succeeded／退出码 0（33.11 秒）。分别见 `Editor-final-console.log`、`Game-final-console.log`；交付状态 `delivery.json`。后台命令未启动 GUI 编辑器或游戏。

不运行游戏、截图、渲染或验收；最终观感和游戏表现交由用户测试。

构建依赖补齐：本轮 Editor 构建中 `FPSWeaponFXComponent.cpp` 对 `UGameplayStatics` 的既有调用缺少直接头文件，已仅加入 `Kismet/GameplayStatics.h`，保留武器实现不变。
