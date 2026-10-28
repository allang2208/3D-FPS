# 山鸣弓弦：印记与金色弦影箭

接入日期：2026-10-27。适用高地长弓 `bow_woodsteel`，弓弦 `highland_mountain_echo`。

## 表现

- 拉弓进度条下方 24 px 增加三枚横排山峰菱形印记。零层为暗金轮廓，叠层点亮并短促增亮；首次达到三层时播放 0.65 秒扩散金环与碎光，之后保持轻微呼吸光。采用游戏时间，暂停时不继续动画。
- 印记直接读取服务器同步的当前武器实例层数；可在箭飞行、收弓间隙看到命中叠层，也可在 ADS/物理瞄具下看到。菜单、翻越、换装、死亡沿用现有隐藏或状态清理规则。
- 弦影箭使用独立金色发光材质、箭头光核、沿箭杆流动的金丝和细碎尾光。保留原箭矢轮廓与既定 0.18 秒延迟。
- 击中目标、墙壁、地面或可破坏玻璃时播放短闪、金色扩散环和 32 枚飞散火星，另有短余辉。整套命中效果为有限生命周期，不附带范围伤害。

## 接入

`BowMountainEchoComponent` 持有复制层数及本机表现时间，装备时异步预载三项运行时入口资源。`ColdSteelBowResonance` 在现有 HUD 中绘制，不新建输入或存档入口。

`BowMountainEchoVisual` 创建一个附着箭矢的 Niagara 飞行组件；命中停止飞行组件，复制接触位置与法线，保留箭 actor 1.5 秒让近距离命中也能进入首次网络复制。命中粒子脱离箭 actor，自行完成并归还 Niagara 池。销毁时取消异步加载、清理飞行组件；专用服务器不创建特效。

原有伤害、暴击继承、穿心箭限制、耗体、弹药、叠层与时限逻辑不变。效果资源位于已有 AlwaysCook 武器目录内。

## 已保存资产

`/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFXV14/`

- `M_MountainEcho_GoldenArrow`
- `M_MountainEcho_GoldCore`
- `M_MountainEcho_GoldSpark`
- `M_MountainEcho_GoldRing`
- `NS_MountainEcho_GoldenFlight`
- `NS_MountainEcho_GoldenImpact`

作者脚本：`author_assets.py`；保存回执：`asset-receipt.json`。使用项目已有 Niagara 编辑辅助函数与发射器模块，所有外观材质及发射参数写入本目录的独立资产。

必要构建入口：`build.ps1`，分别输出 Editor/Game 构建日志与 JSON 回执。没有启动编辑器、游戏、截图、预览或运行测试；实际观感和联机表现由用户自行测试。
