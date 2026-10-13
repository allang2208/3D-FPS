# Jason 全身翻越／攀爬接入（2026-10-12）

本轮将本机 Epic Game Animation Sample 的完整人形动画适配到当前 `SK_Jason_Base`，替换全身翻越原有的程序抬腿表现。现有第一人称 V7 手臂、动作执行器、探测高度与胶囊碰撞路线继续复用。

后续第一人称松手采样、镜头回归、持枪恢复及深落差惯性衔接见 [第一人称翻越衔接](first-person-traversal-handoff-20261012.md)。

## 动画来源与时序

复用 `/Game/Characters/JasonPlayer20261003/CrouchGASP20261005/Rig/RTG_GASP_Jason_Crouch` 的骨架对齐。新动画独立保存到 `/Game/Characters/JasonPlayer20261003/TraversalGASP20261012/Animations`，通过 `player_body.json` 的三个 `Traversal.*` 键加载，并加入 Cook 目录。

| 运行时键 | GASP 源动画 | 抓沿／松手／退出源时间 |
| --- | --- | --- |
| Traversal.Vault | M_Neutral_Traversal_Vault_1_0_stand_F_Lfoot | 0.27 / 0.58 / 0.8 秒 |
| Traversal.Mantle | M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot | 0.345 / 1.1 / 2.0 秒 |
| Traversal.Climb | M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot | 0.74 / 2.25 / 3.3333 秒 |

动画按执行器的进入、接触、松手、退出进度分段采样，不增加独立玩法计时器。Vault 只使用原片前 0.8 秒，原片后段长距离下降由现有下落／落地状态替代。高攀爬仍遵守当前游戏允许的高度，源片名中的 2.5 不改变玩法高度上限。

## 全身表现

- 新层位于普通身体、武器姿态修正之后，死亡层之前；动作期间由源动画保留头胸、髋部、双腿和手指运动。
- 根据实际墙面朝向对齐动作；在执行器给出的支撑窗口内，将完整支撑姿态适配到左右独立墙沿点，再以原动作肘弯方向做双手接触修正。手腕朝向沿用重定向动作。
- 动画根位移锁定到参考姿态，角色位置仍只由既有 Sweep 路线推进，避免根运动重复推动胶囊。
- 使用作者动画时跳过旧的程序抬腿、下蹲压低和翻越前倾修正。缺失相应库资产时保留原程序动作。
- 完成或取消后立即停止追踪旧墙沿；最后一个全身姿态在 0.12 秒内混回当前地面、下落或其他动作。深落差继续由此前 `bReleaseIntoFall` 规则进入自然下落。
- 高低攀爬通过既有 `ActionVariant` 区分，墙面方向通过既有 `MotionDirection` 传递；没有新增玩法 RPC 或反射状态字段。

制作脚本：`Tools/PlayerBody/prepare_traversal_sources.py`、`retarget_traversal_jason.py`、`publish_traversal_jason.py`。源文件清单、散列和制作回执位于 `SourceAssets/ThirdPersonTraversal20261012`。原始与派生 UE 二进制保留本机，来源沿用 `Docs/gasp-traversal-20260910.md`。

## 交付状态

- 三段 Jason 动画已通过后台重定向 commandlet 生成并保存；`WeaponAnimationAuthoring.finalize_authored_animation` 在保存前完成动画编译。回执为 `SourceAssets/ThirdPersonTraversal20261012/assets-saved.json`，制作日志为同目录 `retarget.log`。
- 三个动作映射已写入 `Content/ColdSteelData/player_body.json`，对应目录已加入 Cook 配置。
- 常规 `FPSGAMEEditor Win64 Development` 后台构建成功并链接基础 Editor DLL，日志：`Saved/BuildEditor/build-20261012-195919.log`。

未启动交互编辑器或游戏、进行截图或运行测试，动作效果由用户测试。
