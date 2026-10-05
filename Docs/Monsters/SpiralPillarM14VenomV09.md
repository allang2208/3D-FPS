# 螺柱 M-14 — V09 黏稠液团与断裂液丝

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。用户采用上一轮推荐的毒液视觉方案：出嘴短喷、不规则液团、断裂拉丝、命中液膜和飞溅。

## 效果实现

- 主体：从原共享毒液材质复制出 M14 独立外膜和内芯，通过连续局部形变增加较长的细颈尾部、非对称液团翻动、出嘴时的短暂拉伸和内部密度流动。每弹的种子和飞行年龄使用 Custom Primitive Data，不分配动态材质实例。包围范围同步扩大以覆盖材质变形尾部。
- 出嘴：沿原实际 `mouth_socket` 发出的投射物初始位置，生成七个短促拉长滴液、两个向下滴落的较重液滴。寿命 0.11–0.30 秒，复用已有毒液粒子池。
- 尾迹：改为每飞行 22 cm 生成一组，原先按 0.065 秒生成，在现有速度下约间隔 65 cm。每三组增加一条约 0.16 秒的细液丝，液丝和滴液采用不同脱落速度形成断裂感。网络客户端沿接收的移动段补点。
- 命中：保留原湿痕和薄雾，新增九个沿接触面方向散开的拉长液滴；只有 M14 本次分配的湿痕扩大到约 56×68 cm。
- 接触液膜：在场景碰撞表面生成法线对齐的薄液膜，迅速展开、出现不规则裂孔，然后消失，寿命 0.4 秒；使用独立池化 ISM 和真实透明边界。玩家胶囊不生成悬空液膜或贴花，只接收飞溅。
- 外观属于程序化液体表现，不启用实时流体求解。共享毒蛆、药瓶等原材质、原尾迹及原命中入口保持已有行为，M14 使用新增入口。

## 玩法与预算

- 保留一发直射、1000 cm/s 速度、1100 cm 飞行上限和 9.5 cm 碰撞半径。发射时序、起手距离、伤害、减速、死亡时清理及网络命中规则保持原配置；装饰液滴和液膜均不造成伤害。
- 沿原投射物 Tick 和共享毒液池 Tick 更新，没有为碎滴或液膜添加 Actor Tick。
- 原共享池上限仍为 192 液滴、48 雾片、40 湿痕；新增接触膜最多 16 个实例，满时循环复用。所有生成受 `FluidPresentationSubsystem::AllocateDetail` 数量额度控制。
- 尾迹单弹最多 64 个采样点，单帧最多补 4 点，长帧丢弃积压；液丝仅近处 18 m 内生成，尾迹和新增飞溅限 30 m，出嘴细节限 25 m。主弹体及伤害碰撞不随细节预算消失。
- 新材质不引入纹理或实时模拟缓存。没有进行帧率或显存测量，不推断性能提升。

## 文件和资产

- 资产：`/Game/Monsters/SpiralPillarM14/VenomV09/M_M14_VenomBody`、`M_M14_VenomCore`、`M_M14_VenomFilm`，前两者绑定原 M14 蓝图，液膜由共享池的 M14 分支加载。
- [材质制作与绑定](../../Tools/SpiralPillarM14/author_venom_v09.py)
- [液团形变](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Shaders/M14LiquidShape.hlsl)
- [液团流动](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Shaders/M14LiquidFlow.hlsl)
- [接触液膜](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Shaders/M14ContactFilm.hlsl)
- [投射物接入](../../Source/FPSGAME/Monsters/M14MucusProjectile.cpp)
- [M14 共享池分支](../../Source/FPSGAME/Monsters/PoisonMaggotVenomFXM14.cpp)

## 状态

三份专用材质与 M14 蓝图已实际保存，材质编译及 Editor/Game 常规后台构建完成。继续从 F6「螺柱 M-14」生成。

没有打开编辑器、游戏、PIE，没有运行截图、验收渲染或测试。后台启用渲染接口仅用于必要材质编译，未生成画面。效果与实际性能由用户试玩确认。

落盘回执：[材质与蓝图](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Records/assets.json)、[Editor 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Records/build_FPSGAMEEditor.json)、[Game 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09/Records/build_FPSGAME.json)。
