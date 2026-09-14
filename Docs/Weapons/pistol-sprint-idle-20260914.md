# 手枪奔跑改为待机位置横摆

用户要求 M1911 与 715 等手枪在奔跑时不再大幅向上抬枪，围绕待机位置以中等幅度左右摆动，并匹配步频。

## 改动依据与实现

现有奔跑没有独立手枪动画片段：`UpdateActionPose` 保留各枪的 idle/idle_empty，`UpdateViewmodel` 在整套手臂与枪械上叠加程序姿态。M1911 和 715 使用共同 Manny 播放路径，`bUsingM4Infima` 同样为 true，因此此前也叠加了步枪的固定 `FRotator(35,-12,-8)` 与 `FVector(6,3,-9)` 厘米偏移。

本次按 `IsPistolWeapon()` 分流，手枪使用零均值横摆；中心沿用该枪原腰射待机位置和握姿。原步枪姿态仍由原分支处理。无需重制、导入动画或改动材质。

| 手枪参数 | 当前作者值 |
| --- | --- |
| 左右平移 | ±2.2 cm |
| 前后随动 | ±0.18 cm |
| 上下起伏 | ±0.22 cm |
| 左右偏转 | ±1.5° |
| 侧倾 | ±1.8° |
| 俯仰 | ±0.35°，无固定抬枪 |
| 腕部相位滞后 | 0.30 rad |

这些是满幅目标参数，实际叠加还受移动速度、过渡和平滑跟随影响。位置与角度统一作用于整套视模，保留原双手握持接触和配件装配关系。参数位于 `FPSGAMECharacter.h` 的 `Pistol|Sprint` 分类。

## 步频与过渡

`UFPSFootstepAudioComponent::GetStridePhaseRadians()` 读取原脚步累计距离，两个落脚间隔形成一个完整左右周期。步距复用原来的 150～205 cm 速度映射；满速 700 cm/s 时约每秒 3.41 次落脚、1.71 个左右周期。未替换声音或改变触发节奏。

脚步音频仍以原 30 Hz 更新；视模读取时补上最新角色位置相对上次音频采样的位置差，避免横摆按 30 Hz 阶梯跳动。左右交替由脚步距离结算维护，不使用另一个独立频率时钟。

横摆采用余弦往返，垂直和前后为小幅双频随动；腕部稍滞后。奔跑权重使用指数渐变及平滑曲线，起跑逐渐扩大摆幅，停跑收回待机；瞄准、开火或换弹时加快收束。普通移动 bob 随奔跑权重降低，避免叠加不同频率的两套大幅摆动。空中和滑铲不推进手枪步相位。

## 范围与交付

- 实现文件：`Source/FPSGAME/FPSGAMECharacter.cpp/.h`、`Source/FPSGAME/Movement/FPSFootstepAudioComponent.cpp/.h`。
- 当前统一覆盖 `IsPistolWeapon()` 的 M1911、Dan-Wesson 715，含 M1911 空仓待机状态。
- 沿用原开火结束后换弹、冲刺转开火限制、ADS 和装填动作时序。
- 原生 Editor 构建完成：`Saved/Builds/PistolSprint20260914/build-retry.log`，结果 `Succeeded`，FPSGAME / AutoFootstep / AutoFootstepEditor 模块后缀均为 `71413`。重启编辑器加载。
- 首次构建的 `build.log` 记录共享 UI 头文件与 UHT 生成宏行号不同步的错误；使用 `-ForceHeaderGeneration` 重新生成后构建成功，没有修改开发面板源码。
- 未运行游戏、测试或制作验收预览，实际摆幅和自然程度由用户测试。
