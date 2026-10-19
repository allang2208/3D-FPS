# 生活区员工 M-01（2026-10-17）

本轮建立三名独立员工怪物与 F6 生成入口。使用当前三名 M-01 职员保留的完整原生身体，复用已适配的男女动作。没有修改供体模型、材质、骨架、动画及蓝图。本轮未安排生活区各房间的自动刷怪数量、位置或清场目标。

| 显示名称 | 稳定 ID | 完整身体供体 | 生命 | 攻击 | 移速 cm/s |
| --- | --- | --- | --- | --- | --- |
| 男性员工 M-01 | LivingStaffMale | 安保员 Body V09 | 270 | 24 | 94 |
| 女性员工A M-01 | LivingStaffFemaleA | 接待员 Body V04 | 230 | 20 | 92 |
| 女性员工B M-01 | LivingStaffFemaleB | 研究员 Body V01 | 250 | 22 | 90 |

统一使用「名称 + 空格 + M-01」格式，女性 A/B 作为名字中的个体区分，F6 与战斗血条一致。等级 3、普通品阶，物防/魔防/抗暴均为 0，基础经验 241；命中、等级差与品阶奖励仍走现有共享系统。以当前普通人形 `BP_NurseZombie` 的 250 生命/22 攻击为数值基准，三人在附近小幅分配；移速处于当前 M-01 职员 90–95 cm/s 的区间。

## 资产与动作

目标目录 `/Game/Monsters/StaffLiving`，三份蓝图为 `BP_LivingStaffMale`、`BP_LivingStaffFemaleA`、`BP_LivingStaffFemaleB`。

- 男性完整身体：`/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Body_V09`；直接引用安保当前 V06 待机/行走、V10 攻击、V12 受击/倒地/仰起/俯起/眩晕。
- 女性A完整身体：`/Game/Monsters/FacelessReceptionist/SK_FacelessReceptionist_Body_V04`；直接引用接待员 V04 待机/行走/攻击、V05 受击/倒地/仰起/俯起/眩晕。
- 女性B完整身体：`/Game/Monsters/FacelessResearcher/SK_FacelessResearcher_Body_V01`；直接引用研究员 V04 待机/行走/攻击/受击、V05 倒地/仰起/俯起/眩晕。

三者保留各自骨架、物理资产、皮肤材质、导航胶囊、网格变换、攻击窗口、共享音效和人形死亡路径。员工用完整身体，男性员工清空供体帽子组件的网格，原安保帽子未修改。没有重新生成模型、重定向或复制动画。

保留 `FacelessSecurity` / `FacelessReceptionist` / `FacelessResearcher` 家族标签，以继续使用现有动画过渡与地形脚部处理；新增独立身份标签和 `StaffLivingEmployee`。显示名优先识别独立身份。`NurseZombie::BeginPlay` 对 `StaffLivingEmployee` 跳过供体岗位倍率，避免保存的最终生命/攻击/移速又被原职业二次改变。共享全局生命倍率、品阶、奖励和战斗调节保留。

## 制作记录

`SourceAssets/StaffLivingEmployees20261017/source_inputs.json` 记录制作所用当前供体引用与基准数值，`ue_delivery.json` 记录实际资产保存；`Before/` 保留本轮修改前的源码和名册，包含当时已有的并行修改。

制作入口：`Tools/StaffLivingEmployees/read_sources.py`、`install_assets.py`、`save_assets.ps1`。原生接入涉及 `DevelopmentSpawnComponent.cpp`、`MonsterCombatComponent.cpp`、`NurseZombie.cpp`。

执行状态以本轮交付回执为准。未运行游戏、自测、截图或渲染，由用户测试外观、动作、战斗与联机表现。

### 本轮保存与构建

- 三份正式蓝图已通过后台 Python commandlet 保存，`asset_process.json` 记录退出码 0。
- 必要代码曾在原编辑器中 Live Coding 成功。该编辑器随后自行退出；没有执行关闭、重开或停止 PIE 操作。
- 常规 `FPSGAMEEditor` 构建成功，结果见 `SourceAssets/StaffLivingEmployees20261017/build-FPSGAMEEditor.json`。F6 构造默认值已编入正式 Editor 二进制，下次启动可加载三个新入口。
- 临时 `register_catalogue.py` 未实际修改模板，已于 2026-10-19 归档到 `trash/facility-monster-hits-20261019/Tools/StaffLivingEmployees/`；正式 F6 入口以常规构建为准。
- 常规 `FPSGAME` Game 构建成功，结果见 `SourceAssets/StaffLivingEmployees20261017/build-FPSGAME.json`。Editor 与 Game 两个目标均已完成并落盘；未启动编辑器或游戏进行测试。

## 后续接入

2026-10-17 三房自动刷怪与盲祷者通行目标已进入后续开发，具体编成、落点、任务及构建状态见 [生活区三房遭遇](../Dungeons/staff-living-encounters-20261017.md)。本文上方“未配置刷怪”描述的是员工本体阶段的交付范围。

2026-10-19 整理：女性 A/B 的当前网格为 StaffLiving 下 ShoulderV02，命中体积为 FittedHits20261018；具体恢复顺序见 [发布记录](../Publication/FacilityMonsterHits20261019/README.md)。上文供体清单保留作为最初制作来源。
