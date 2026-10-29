# 弯刀第三人称遗漏动作补齐 — 2026-10-29

本批次已经完成制作、后台导入保存、配置接入及 Editor/Game 正式构建。Jason、Kaitlin 各新增或更新 7 条原生骨架动画，共 14 条。当前主连击一、二段和第一人称动画未重做。

## 已交付动作

| 动作 | 接入键 | 处理内容 |
| --- | --- | --- |
| 单持装备 | `Kukri.FullBody.Equip` | 抛刀、张手、旋转、接刀，与实际武器模型的相对位置同步 |
| 双持装备 | `Kukri.FullBody.Dual.Equip` | 双手错峰抛接，独立左右刀身轨迹 |
| 主手手枪、副手刀上挑 | `Pistol.KukriUppercut` | 左手上挑、换握与回收；右手保留当前手枪的实际握持；支持蹲姿与视线变化 |
| 双持快速近战 | `Kukri.FullBody.Dual.Pommel` | 主手向前击打，副手持刀护持和配重，恢复双刀待机 |
| 双持跑步过渡 | `Kukri.FullBody.Dual.Run` | 按跑步权重过渡上半身，主刀翻为反握，下半身保留当前移动步态 |
| 双持第一段回收 | `Kukri.FullBody.Dual.Recover1` | 从已完成回刀的攻击尾帧平顺收势，不追加一次挥击 |
| 双持第二段回收 | `Kukri.FullBody.Dual.Recover2` | 同上，保留既有第二段主体动作 |

资产目录为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/Completion20261029/`。
`player_body.json` 通过 `Tools/PlayerBody/config_transaction.py` 仅发布本批次的 14 个配置叶节点。
完整资产路径、磁盘大小及 SHA-256 见 [asset-manifest.json](../../SourceAssets/KukriThirdPersonCompletion20261029/asset-manifest.json)，配置发布回执见 [published.json](../../SourceAssets/KukriThirdPersonCompletion20261029/published.json)。

## 制作中定位并修复的问题

- 手枪加副手刀上挑没有进入第三人称专用动作；已连接已有动作状态、进度、节奏和停顿信息。
- 混搭上挑的武器家族仍为 Pistol，旧蹲姿分支只识别 Kukri，导致蹲姿中途回到站姿。已将该原生上挑纳入蹲姿适配。
- 蹲姿低头的上挑进入和回收阶段存在前臂穿胸。现在为两只手保留向前的活动空间，并在短暂的进入混合后重新求解手臂。
- 单纯调整避让会增加左手折腕，现同时放松掌向并重新求解肩、肘、前臂，保持刀柄在手中的安装关系。
- 最终装备握拳层会盖掉抛接张手和上挑换握手指。对应动作现在保留动画里的原生手指，右手手枪仍使用当前枪械的握持。
- 双持快速近战的旧来源存在手部突跳，已重做肩部带动的击打弧线和回收。

第三人称刀身在最终身体姿态输出后，基于稳定的原始安装变换应用抛接、换握和跑步翻刀。使用既有角色装备/动作状态，不新增客户端伤害判定或额外 RPC。

## 已完成检查

| 证据文件 | 检查数量 | 失败 |
| --- | ---: | ---: |
| source-checks.json | 108 | 0 |
| saved-checks.json | 14 | 0 |
| network-checks.json | 83 | 0 |
| uppercut-final-pose-checks.json | 344 | 0 |

- 保存后重新读取全部 14 个动画，核对角色骨架、配置路由和压缩姿态；最大局部旋转误差 0.248°，最大局部平移误差 0.00997 cm。
- 上挑最终姿态检查实际加载 UE 动画实例和武器，覆盖 2 个身体、5 种手枪、4 种姿态/视线条件。所采样的前臂对躯干包络最大侵入 0.000 cm，最大手腕折角 56.60°；同时检查枪柄位置、方向、刀尖上升幅度和最终手指层。
- 83 项联机相关检查是动作路由、攻击回执及服务器规则检查，**不是 UDP 多客户端运行测试**。
- `FPSGAMEEditor Win64 Development`、`FPSGAME Win64 Development` 均构建成功。检查使用无界面 commandlet，临时禁用当前缺失模块的可选插件 `FPSDeformationResidency`，未修改项目插件配置。
- 未启动 UE 编辑器界面或 PIE，未进行实机联机、网络延迟、不同服装动态穿插验收。自然度与实际游戏手感仍需游戏内观察，不能由构建和数值检查代替。

## 可查看预览

这些 GIF 来自**已保存资产的压缩姿态**，不是游戏录像；上挑预览未放入手枪模型，跑步预览展示上半身过渡，未展示游戏中的下半身移动步态。

- [单持装备](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Equip.gif)
- [双持装备](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Equip.gif)
- [副手刀上挑](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Pistol.KukriUppercut.gif)
- [双持快速近战](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Pommel.gif)
- [双持跑步过渡](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Run.gif)
- [双持第一段回收](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Recover1.gif)
- [双持第二段回收](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Recover2.gif)

制作脚本、保存脚本、姿态输入、检查结果及构建日志位于 `SourceAssets/KukriThirdPersonCompletion20261029/`。汇总见 [delivery.json](../../SourceAssets/KukriThirdPersonCompletion20261029/delivery.json)。
