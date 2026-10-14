# 法棍握姿与第三人称饮用、进食（2026-10-06）

## 第一人称

实际保存的 UE 法棍约为 4.35 × 5.71 × 30 cm，握持高度 15 cm；旧的尺寸中间文件已经过时，不能用于定位。问题集中在握点、四指包握和拇指对握。此前每节手指只用少量指腹点贴合，没有覆盖整个掌面和手指外形。

`fit_baguette.py` 读取 `food-geometry.json` 中的实际 UE 网格，以及已采用的 V7 手部蒙皮，在完整采样掌面和手指的基础上重新拟合。实体内外使用射线交点判定，避免扫描网格局部法线误导距离；四指张角受限，拇指单独对握。结果存入 `baguette-grip.json`，原运行时配置留在 `baguette-previous.json`。

仅发布法棍的掌中握点和手指姿态；保留原有 2.7 秒时长、送入口轨迹、扣除和恢复时机。没有改变原生手部骨长、蒙皮或共享手模。

## 第三人称

复用本地 Quaternius Universal Animation Library 2 Standard 的 CC0 `Consume` 全身动作。源动作使用左手，包含抬手、停留、收手和轻微躯干/头部动作。来源：https://quaternius.itch.io/universal-animation-library-2 。许可副本位于 `SourceAssets/ThirdPersonSwordCandidates20261006/License.txt`。

`prepare_consume20261006.py` 重定向并导出 Jason 动作、骨架及食品几何；`prepare_consume_contacts.py` 导出实际唇部位置与容器尺寸；`author_body.py` 保留供体动作语义、肘部弯曲平面和固定骨长，调整握物方向、身前持物位置及嘴部接触，生成三套适配：

- `Consume.Drink`：水、药水和易拉罐，按当前实际容器高度补偿瓶口接触。
- `Consume.EatBread`：普通面包。
- `Consume.EatBaguette`：法棍，采用本次新握点。

`save_consume20261006.py` 通过后台 commandlet 真正创建并保存三个 AnimSequence，保存回执为 `assets-saved.json`。动画目录为 `/Game/Characters/JasonPlayer20261003/Consume20261006/Animations`。

运行时按物品原有使用进度将 Contact/Release 标记对齐开始饮用、结束饮用，独立控制第三人称的左臂与躯干。腿部沿用走、跑、下蹲和地面适配；右臂保留装备姿态。第一人称手指接触映射仍复用，但第三人称不再照搬第一人称手腕路径。不同瓶子尺寸通过头部唇点和当前道具顶端修正接触，骨长不拉伸。

物品消耗、恢复数值、左手装备收放、液面、瓶塞和丢瓶继续使用既有组件及事件。动画仅负责表现，不执行消费类动画通知。

## 发布与交付边界

`Tools/PlayerBody/publish_consume20261006.py` 仅更新法棍家族和已保存的三个第三人称动作引用、嘴部接触点，不重写物品表。修改了原生第三人称动画代码，需要后台 Editor 构建。构建结果见本次交付说明。

遵照用户要求，不启动编辑器界面或游戏，不执行运行测试、截图或渲染验收；视觉效果由用户实机测试。几何拟合的数据是制作输入和优化结果，不代表实机视觉验收。
