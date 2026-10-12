# 普通竖劈／冲刺竖劈：双手握姿间隙

后续否定：用户确认本版仍然两手穿叠。裸手约 7 mm 的局部源包络不代表实际钢甲手套，更没有改变整手握点；本版不能作为解决两手穿叠的完成结论。两项引用由 [整手握点修正](third-person-sword-grip-pair-20261010.md) 接替，下文保留制作经过。

用户确认上一轮手臂姿态正确，剩余问题仅为普通竖劈和冲刺竖劈的两手穿叠。本轮保留上一轮 `KwangSwordWrist20261010` 的全部肩、肘、腕及辅助骨轨道，限定修改左手拇指包握。

交付状态：两段新资产已由无界面 commandlet 保存，`assets-saved.json` 为 `complete: true`；两项配置已发布，回执为 `assets-published.json`。常规 Editor DLL 已编译完成，未进行游戏测试。

## 制作

两手的原腕部握点沿剑柄相距约 10 cm。使用上一轮已经保存的原生装备握姿和 Jason 源蒙皮作为制作输入，右手小指下缘与左拇指上缘的轴向包络几乎重叠。运行时又会在身体动画之后写入装备手指姿势，因此单独修改动画里的手指会被覆盖。

本次将左拇指向本手食指区域收拢，不平移手指骨、手腕或手掌。拇指末节目标沿柄下收 2.5 cm，按原生骨长重新拟合前两节，保留末节掌垫朝向并同步半关节辅助骨。原生拇指相对制作输入的三个局部旋转改变量约为 13.63°、23.78°、37.07°；这是本骨架的制作结果，不作为其他手型的限位标准。

制作使用的裸手蒙皮轴向包络间隙约为 0.695 cm。此数值仅是源模型拟合约束，不代表实机、衣物或全部中间混合状态已经验收。

两段动画增加 `SwordSupportThumb` 曲线。原生动画图只在携带该曲线的动作中，让左拇指及其辅助骨使用动画内的拟合姿势，并按动作权重和原有抓握权重衔接；其他手指继续使用装备握姿。右手、肩肘腕、身体运动、骨段平移／缩放、120 Hz 采样、Contact／Release 和周期绕柄曲线均沿用上一轮。

## 交付文件

- 制作源：`SourceAssets/ThirdPersonSwordHandClearance20261010/author_support_thumb.py`、`candidate-actions.json`、`hand-fit.json`。
- 保存入口：`Tools/PlayerBody/save_sword_hand_clearance20261010.py`。
- 接入入口：`Tools/PlayerBody/publish_sword_hand_clearance20261010.py`，仅切换 `Melee.FullBody.Overhead` 与 `Melee.FullBody.DashOverhead`。
- 新资产目录：`/Game/Characters/JasonPlayer20261003/KwangSwordHandClearance20261010/Animations`。旧腕臂资产保留。
- 原生接入：`FPSPlayerBodyAnimInstance.cpp`、`FPSBodySwordPose.inl`。
- 常规后台编译日志：`Saved/BuildEditor/build-20261010-175958.log`，`Result: Succeeded`。

保存及发布的实际状态以同源目录 `assets-saved.json`、`assets-published.json` 为准。未追加测试、读回诊断、截图或验收渲染，未启动 UE 界面或游戏；最终表现由用户测试。
