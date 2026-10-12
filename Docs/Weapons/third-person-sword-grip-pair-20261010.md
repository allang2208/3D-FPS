# 竖劈双手穿叠：整手握点修正

> 后续用户仍明确反馈手臂位置不对，本版不视为问题已解决。用户要求左右臂上下握位对调，后续制作记录见 [左右臂换位](third-person-sword-arm-swap-20261010.md)。下文保留本版的历史制作与定向采样范围。

用户再次提供画面，明确上一轮收拇指没有解决两手叠在一起。本轮继续限定普通竖劈与冲刺竖劈。

## 上一轮遗漏

`HandClearance` 只改了左拇指，两手沿柄的腕部握点仍相距 10 cm。上次报告的约 7 mm 来自裸手源模型，不能代表穿钢甲手套后的间隙。

本轮读取了当时已经运行的角色：武器为 `ue_tang_dao`，身体使用 `SK_Jason_Base`，钢甲手套使用 `StaffSurfaceRepair20261009/SK_Jason_SteelGauntlets`。读取实际手套几何，并通过独立预览世界的原生动画图采样当前 `KwangSwordHandClearance20261010`：左拇指确实使用了新姿势，但两手手套的轴向外包络仍重叠约 0.46–0.53 cm。只改拇指、只看裸手局部数据都不足以解决用户反馈。

## 修改

右手、右臂和刀身轨迹保留；左手整个握点沿当前剑柄轴向柄尾移动 2.4 cm，使轴向腕部握距变成 12.4 cm。

左腕组件空间朝向保持原样。左臂按原生骨长在新肩腕可达圆上选离旧肘最近的解，保留原来的肘弯方向；仅更新左臂主骨旋转与扭转／修正辅助骨，未重新运行自由握柄角搜索。制作源中左肘最大跟随约 2.73 cm。身体、腿、右臂、手指包握、动作时序、120 Hz／193 帧及周期绕柄曲线继续沿用。

保存到独立目录 `/Game/Characters/JasonPlayer20261003/KwangSwordGripPair20261010/Animations`，只替换两项竖劈引用。运行时代码沿用已编译的绕柄与拇指支持，本轮不新增原生代码修改。

## 落盘与定向结果

两段资产已保存，`assets-saved.json` 为 `complete: true`；两项引用已切换，`assets-published.json` 记录前后路径。保存 commandlet 正常退出。

新配置经过原生图重新采样，在攻击进度 10% 至 90% 的九个定向姿态中，实际钢甲手套的轴向包络间隙最小约 1.8604 cm；旧版对应最小值为 -0.5304 cm。`pair-comparison.png` 上排旧版、下排新版，使用相同视角和比例。该结果覆盖这些完整动作权重的姿态采样，不表示实机淡入、淡出、中断或任意装备组合全部通过。

## 入口与证据

- 作者脚本：`SourceAssets/ThirdPersonSwordGripPair20261010/author_grip_pair.py`。
- 制作数据：同目录 `candidate-actions.json`、`pair-authoring.json`。
- 实际身体／装备读取：`live-pair.json`、`production-steel.json`。
- 原生图定向读回：`native-before.json`、`native-after.json`。
- 保存／接入：`Tools/PlayerBody/save_sword_grip_pair20261010.py`、`publish_sword_grip_pair20261010.py`；完成状态分别记录于 `assets-saved.json`、`assets-published.json`。
- 姿态图：`pair-comparison.png`，蓝色为右手、橙色为左手；使用实际钢甲手套几何和原生图姿态，按剑柄空间绘制，不是游戏截图。

本轮定向诊断是对用户要求重新研究该问题的回应。未启动新的 PIE／游戏或扩大回归范围；已有编辑器自行退出后，继续通过后台 commandlet 保存。实机完整攻击、中断与移动混合效果仍需用户最终确认。
