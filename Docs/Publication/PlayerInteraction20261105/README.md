# 玩家交互、镜头与动作占用

本批整理 2026-10-24 至 2026-11-05 已落盘的工作。Git 基线为 `e055fc4e0728b8fe57c04939b3a1639e82779f66`。

## 玩家可见的变化

- 女性角色的第三人称双手锤、双手剑和弓按男性武器局部接触点重新适配。用户已确认双手锤；其余武器的检查方式和处理结果逐项记在[女性握持记录](../../Characters/kaitlin-weapon-contacts-20261024.md)。
- 第一人称躺床和坐椅时，镜头随身体过渡并避让碰撞。卧姿左右各 60°，坐姿左右各 70°，转向侧面时可用俯仰范围逐渐收窄。[床椅镜头与转头参数](../../Gameplay/bed-first-person-camera-20261026.md)
- 打铁、枪械装配、炼药和木工保留小游戏近景，第三人称角色在工作台旁空手待机。旧的全身打铁层已退役，第一人称淬火轨迹继续由工作台驱动。[工作台待机](../../Characters/workstation-third-person-idle-20261029.md)
- 打开状态、背包等普通栏位后，已开始的动作继续推进。新攻击、连击、装填和施法需要等待手部释放。食物和水可用主开火键取消，该次按下和松开都被消费。HP/MP 药水继续饮用。主动切换装备、成功翻越和攀爬仍可取消。[面板输入](../../UI/panel-action-continuity-20261029.md) · [手部占用规则](../../../skills/ue5-cpp-gameplay/references/consumable-action-ownership.md)
- 联机消耗品沿拥有者的 PlayerState 提交开始、接触与取消。主机按动作标识、角色、物品实例和最早接触时间核准一次结算；拥有者应用库存回执后再推进确认版本。[联机回执规则](../../../skills/ue5-save-load-replication/references/consumable-contact-receipts.md)

## 源码范围与恢复

10 月 25 日的第三人称排查曾把共享手部轨迹误判成缺少动作。回看当时的制作记录，步枪换弹、工具挥动、弓搭箭和法术书开合已有身体定位或接触适配，弯刀快速近战已有男女各自的第三人称资产。当日查到主手手枪搭副手弯刀尚缺第三人称持握入口；此处记录的是当日状态。后续查看某个组合时，需要同时核对当时的开发记录与当前分派。[步枪动作](../../Characters/third-person-rifle-actions-20261006.md) · [同期双持组合](../../Weapons/dual-pistol-kukri-idle-20261025.md) · [弯刀快速近战](../../Weapons/kukri-quick-first-person-arms-20261025.md)

[源码清单](source-manifest.json) 区分直接合入公开基线的 `native`、公开基线已有的 `present`、适配旧版双持接口的 `public-prerequisite` 和需要本机前置的 `deferred`。例如，公开版四类工作台接入空手待机，完整锻造工位预留、部分生产工具和技能的入口，以及真实双进程联机测试宿主，依赖更新的锻造工胚、武器组件或 ShotgunWireAudit 基线。相应改动以补丁保留。

清单中的 `public_base_sha256_lf`、`public_result_sha256_lf` 对应公开文件，`preimage_sha256_lf`、`tested_source_sha256_lf` 对应完整本机宿主的改动前后文本。散列统一使用 UTF-8 去 BOM、LF。恢复到对应宿主时，先比对目标文件。若已等于结果则跳过。只有等于前置散列才使用该行的补丁，先运行 `git apply --check <patch>`，再执行 `git apply <patch>` 并比对结果。前置为 SHA-256 空文本且补丁以 `/dev/null` 开始的条目创建新文件。其他版本需针对当前文件合并。不要对已经含有公开改动的同一文件重复叠加整份补丁。

## 女性握持资产

[38 个包的路径与散列](Kaitlin/packages.json) 和[56 个使用角色及男性参考](Kaitlin/saved_assets.json) 与公开配置 `Content/ColdSteelData/player_body.json` 对应。公开原有 2 个角色键已指向修订版，本次补齐其余 54 个。`packages.json` 分别记录本次从活动 Content 读取的 SHA-256、大小和 10 月首次落盘值。后续保存可产生不同包字节，恢复当前版本以活动包散列为准。仅双手锤有用户画面确认。

授权动画、骨架、骨骼采样及 .uasset 从完整宿主或有许可的本地备份恢复。仓库提供资产路径、配方、逐武器清单及历史离线读回结果。重新制作时，将 [Recipe](Kaitlin/Recipe) 的脚本与输入清单复制到独立制作目录，设置环境变量 `FPSGAME_PROJECT` 为完整工程根，准备 `SourceAssets/KaitlinPlayer20261023/FitInputs` 与 `NativeGeometry`。在独立作者宿主中依次准备、采集、诊断、导出、修订、保存和读回，最后运行 `publish_contacts.py` 按指定角色键接入。历史保存回执放在制作目录外，以便从空的输出目录重建。公开文本不能单独还原获许可的二进制包。

## 整理与验证记录

本地 `trash/PlayerInteraction20261105` 收纳了 663 个退役文件，共 1,344,638,577 字节。包括旧工作台全身动画包和作者输入、未完成的女性作者宿主副本及失败的旧羊排检查输出。[归档清单](archive-manifest.json) 保存原路径、目标、大小、散列和退役原因。恢复单项前核对目标散列以及原位置是否已有更新文件。正式配置退役了男女各 6 个 Forge 角色键；迁移会逐项比较旧资源值。[配置写入规则](../../Workflow/player-body-config-publication.md)

清理后的完整本机工程通过 `FPSGAMEEditor` 和 `FPSGAME` 后台构建。[联机与构建记录](evidence.json) 保留此前真实 UDP 的监听主机和客机检查。双方各设 65 ms 延迟、5% 丢包，8 种消耗品场景全部通过，包含无开始记录、接触前取消、主机拒绝、接触后延迟回执、同瓶两次喝水、重放旧标识和法力药水。另一次断线重连覆盖角色姿态。恰在库存提交途中断线再重连的收敛仍待验证。本轮整理没有重新运行游戏或画面验收。本机完整工程的构建与联机记录不能作为公开源码单独构建或运行的凭据。

需要在完整宿主重跑联机用例时，设置 `UE_ROOT` 并使用 [双进程脚本](../../../Tools/Consumables/run_meal_receipt_wire.ps1)。每次运行的日志和报告写入 `Saved/MealNetworkReview/Wire` 的独立时间目录。

同批历史回执还记录了 105 项单机输入检查和 103 项羊排与库存检查，失败数均为零。羊排检查使用无画面的原生逻辑，跳过了篝火界面。
