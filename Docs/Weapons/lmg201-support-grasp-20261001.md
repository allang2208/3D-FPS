# 201 无握把托枪握姿（2026-10-01）

用户要求：201 机枪未安装握把时，左手贴合枪身下沿并握紧，参考其他枪械的持枪手型。

本次从当前保存的基础姿态制作独立的 `base` 姿态层。原姿态的手指与 AKM 待机相同，但腕掌在 201 护木坐标中的朝向不同，手指弯曲后仍主要处于枪身下面。以当前 SVD 待机的托握朝向、五指和掌骨关系为供体，并参考 M4 的中节／末节自然屈曲范围，针对 201 封闭护木的底面和两侧拟合托握。沿枪管方向保留原支撑位置，四指沿侧面包握，拇指对握；保持骨长、局部平移、比例、蒙皮及统一 V7 裸手。

姿态层包含 16 个基础动作：待机、瞄准、腰射、瞄准射击、装备、检视、快速近战、冲刺三段，以及普通弹匣、弹鼓、布弹箱的普通／空仓换弹。只在源左手托住护木的区间渐入修正，离枪交互时归零；左臂主骨和辅助骨随新的腕掌关系重解。冲刺循环中原手离开托握位，保持源姿态。动作时长、事件、枪体、右手与装填轨道沿用原动作。

## 接入

- 作者源：`SourceAssets/LMG20120260927/SupportGrasp20261001/`。
- `collect.py` 读取当前 201 源姿态及 M4、SVD、AKM 参考；`author.py --fit` 制作新托握；`bake.py` 生成局部差分；`install.py` 保存运行时资产。
- 资产：`/Game/Weapons/AnimationProfiles20261001/ue_lmg201/DA_base`。
- 运行代码：`FPSGAMECharacter.cpp` 装备 201 时载入 base；`SVDGripProfiles.cpp` 使无前握把的 201 弹鼓沿用 base。
- 复用既有的 `UWeaponGripProfile` 与各动画通道混合前的差分节点。带 angled／vertical／canted／prism 握把时选择各自 profile，不叠加 base。
- 原 16 个动画包和其他握把 profile 均不改写。已回撤的 SupportFingers59 保持停用。

必要构建与资产保存记录位于作者目录。没有启动编辑器窗口、游戏、PIE、预览、截图、渲染或运行验收，实际效果由用户测试。

## 交付状态

- `FPSGAMEEditor` 与 `FPSGAME` 的 Win64 Development 后台构建均成功，记录为 `build-editor.log`、`build-game.log`。
- `DA_base` 已经由后台 Python commandlet 实际保存，含 16 个基础动作，记录为 `import-02.log` 和 `delivery.json`。
- 导入使用未保存的临时动作副本及既有 `BakeClip` 接口生成差分；没有发布额外的整套动画副本。
- 已经装备 201 的运行实例需卸下并重新装备，以重新载入新 profile。未测试，不作实机视觉通过声明。
