# 裸皮犬：Meshy 身体、Godot 动作与预测攻击

用于不同骨架犬科角色的制作、迁移及攻击优化。工程案例入口为 `Docs/Monsters/InfectedDogPublication20260925.md`，参数与运行合同分别见 `InfectedDogMeshy20260924.md`、`InfectedDogHunting20260925.md`。

## 当前模板与素材边界

2026-09-25 用户已认可 `MeshyV2 + GodotRunNaturalV3` 为四足犬科模板。正式数据集是 `/Game/Monsters/InfectedDog/MeshyV2/DA_InfectedDogMeshy_AnimationSet`，Run / RunTurnLeft / RunTurnRight 共用 NaturalV3；其他动作保留 CompletionV2。早期被否决的 **WolfV3** 是另一套重定向，不能因同叫 V3 恢复它。FitV2 保留为改善基线；旧狼换皮 V1/V2、FoxRunV1 和 WolfV3 已退役。

Meshy 原始高模、quad50k、LocalRig 和 CompletionV2 是连续重建依赖，LocalRig 虽旧但不是废案。保留原始 PBR，分开记录生成模型与动作许可证。此次四足 API 请求返回 422；文档中的 quadruped 字段或网页模板不等于账户 API 已成功产出四足骨架。失败回执只作诊断证据。闭嘴生成体还需制作下颌、口腔与牙齿，不能把外表完整当成可咬合模型。

## 跨引擎动作迁移

- 从旧 Godot 的实际 glTF、动作名和播放脚本取源，不拿早期失败的 UE 重定向当源。本例是 Quaternius CC0 `wolf_quaternius.gltf:Gallop`，归档提交 `49cec1dd11d65295f43c737bac327de829cfd7b1`，周期 17/30 秒。
- 51 骨源与 41 骨目标骨长、roll、参考姿态不同。按世界空间解剖方向和目标骨长适配，显式限制前肢肘部、后肢膝部弯曲平面，单独处理跗关节；不可直接复制局部旋转或让近伸直三段链自由翻折。
- 平滑源控制量后再做支撑相与 IK 约束。固定足端后再平滑最终骨旋转会破坏接地。NaturalV3 采用循环控制平滑、躯干/头颈幅度分级和尾巴短延迟，120 Hz 烘焙；这些是本例参数，不是所有犬类统一值。
- 区分动作周期、动画数据集参考步速和角色追击速度。本例参考跑速约 286.755 cm/s，追击 400 cm/s 保持不变；旧 Godot 固定 1 倍速与 UE 速度驱动相位不能直接当成相同播放条件。
- F6 报生成成功但不可见时，先定位生成位置/胶囊与渲染骨点。本例动画单独导入遗漏 Armature 单位，动画根缩放约 1、绑定根约 100。`meshy_animation_units.py` 按绑定根修正一次，不放大 Actor、不重复乘 100。
- 日常只改奔跑时走独立安装器；不要全量重导模型、修改权重或覆盖已认可的攻击/受击合同。只保存对应动画与三处槽位引用。

## 攻击与寻路复用

感染犬通过 `bUsePredictiveHunting` 选择性复用突变体 3 的追踪/导航分支，旧狼默认关闭。保持一套 Behavior Tree，近战按目标胶囊边缘、脚底高度、前向扇区和遮挡判定，沿攻击接触窗口有限子步采样；一次攻击只结算一次。

飞扑在前摇追踪、起跳时重算速度提前量；限制预测距离并用墙体扫掠和少量候选落点约束。起跳后的轨迹固定，避免空中持续追踪造成不可躲避转向。落点和弧线都要有体积碰撞；导航接受半径需与实际可咬距离一致，不能中心距离刚停止却永远够不到。

感染只在实际造成生命损失后施加；格挡、无敌和未命中不触发。三阶段属性倍率同时进入六维、派生战斗值、HUD、存档和净化，重复感染不叠加、不重置恶化计时，离线不推进。不要只降面板显示。

## 重建与交付

制作次序：Meshy 原始/重拓扑 → LocalRig → CompletionV2 口腔/动作 → 安装身体与基线动作 → NaturalV3 单独安装 → hunting 配置。动作源清单位于 `CompletionV2/source_action_bindings.json`，共享奔跑导入器为 `Tools/InfectedDog/install_canine_run.py`。旧方案退役前先抽离这些仍有用的输入，正式重建不能依赖 trash。

NaturalV3 观感已获用户认可；最新预测攻击/寻路仅完成后台编译和配置保存，未作游戏测试。后续仍默认后台制作/保存，只有用户要求时才运行预览、采样或 PIE，不能将旧验收扩展为新机制已验证。
