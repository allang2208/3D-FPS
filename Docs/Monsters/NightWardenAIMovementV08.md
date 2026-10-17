# 守寝者 AI 移动 V08

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

在 V07 原始身体、短围布和沉稳步态上接入实际移动，沿用原 F6 守寝者入口。新增 `ANightWardenMonster` 和 `UNightWardenAnimInstance`；复用现有 `BP_MonsterAIController`、`BT_Monster`、视听记忆、导航重试及游荡预算，不另建追击决策 Tick。

后续巨臂近战已接入 [V09](NightWardenGiantArmMeleeV09.md)。V08 的待机、行走和导航继续使用，原 F6 入口已扩展为近战版本；本文未含攻击的状态是 V08 当时记录。

| 行为 | 进入／退出 | 移动表现 |
|---|---|---|
| 游荡 | 无已知目标；发现目标或受控时退出 | 出生点附近选择可达位置，半速移动，到点随机停留 |
| 追近／调查 | 共用感知发现玩家或听到声源 | 追近约 150 cm 停下；声音只调查位置，不透视跟人 |
| 返回 | 共用记忆／活动范围决定 | 返回出生点，重新进入游荡 |
| 停步／阻挡 | 实际速度下降 | 步态时钟按实际速度减慢至零，混入匹配骨架的徒手待机 |

V07 行走循环保持不变，标称速度 177.376873 cm/s。追近速度采用相同数值，游荡由现有移动组件乘 0.5。动画推进量为 `dt × 实际水平速度 / 源步态速度`，不随速度修饰器同步修改分母，不给停下或碰墙的角色保留最低踏步速度；待机／行走采用 0.18 秒渐变并保留循环相位。地面移动使用 180 cm/s² 加速度、240 cm/s² 刹车减速度和 100°/s 转向速度。

待机从项目 `MM_Idle` 经 V07 已配准的 IK Retargeter 生成，使用原参考局部骨架写入，延续相同手臂姿势和裸脚接地。保存独立的动画与 Blender 制作源，不覆盖 V07 行走或原始身体。

胶囊半径收为 34 cm、高度保持 170 cm；导航显式使用工程现有 Nurse 规格 34 / 184 / 40 cm，F6 落点与运行寻路读取同一规格。无需新增 SupportedAgent 或改旧导航索引。仍要求生成位置已有该规格的导航覆盖。

围布保留已保存的巫婆式 Chaos 绑定、腰口锚点和身体碰撞。骨骼每帧刷新，不随 Idle／Walk 切换反复重置布料；加减速和转向的物理惯性由现有求解器处理。20 / 24 m 距离滞后与 0.35 秒淡入淡出复用巫婆方式；传送或远距恢复时才重置。专用服务器不运行视觉布料。内层遮挡继续蒙皮。

本轮只接入移动，没有新增攻击、伤害、死亡或生活区刷怪。原入口重定父类前保留 `V08AIMovement/Records/BP_NightWarden.before_v08.uasset`。

制作脚本为 `SourceAssets/NightWarden20261015/Scripts/prepare_idle_v08.py`、`author_idle_v08.py`、`install_movement_v08.py` 和 `v08_background.ps1`。2026-10-16 已完成必要 Editor 构建：初轮局部变量遮蔽 `APawn::Controller` 的错误已修正，随后共享 Editor 构建编译了修正版并链接基础 DLL，成功日志保存于 `V08AIMovement/Records/Build-final-shared.log`，详情见 `build_receipt.json`。

Source 和最终 Install 后台批次均退出 0。首次安装中待机和骨架已保存，Python 未暴露布料传送阈值 setter；改用编辑器属性写入后，从蓝图步骤续接，最终 `ue_delivery.json` 为 `ai_movement_idle_and_cloth_entry_saved`、`complete: true`。已保存独立待机动画、V07 骨架依赖及原 `BP_NightWarden` 的新父类、AI 控制器、动画类与布料设置。待机制作源含 228 个采样、30 fps，位于 `V08AIMovement/Authoring/NightWarden_StandingIdle_V08.blend`。

F6 入口名称为“守寝者 M-01（AI移动）”，稳定 ID `NightWardenRig` 不变；重新生成角色使用本轮资产。若以后重新执行旧 V07 预览激活脚本，需要最后重新执行 V08 接入，以保留 AI 父类和动画配置。

按用户规则未启动游戏、渲染或验收测试，实际寻路、观感与联机效果待用户体验；构建和资产保存不代表运行验收。
