# 第三人称单持手枪：替代源调查

用户随后明确选定 GitHub 的免费源，不采用下文付费候选优先建议。实际制作入口为 `SourceAssets/GitHubSinglePistol20261022/README.md`，资产、配置和构建状态分别记录，不能把本调查记录当作已接入。

2026-10-22，用户明确否定当前单持待机、换弹、开火的手臂表现。本次做本地库存、运行入口及 Fab/GitHub 来源调查；未更换运行资产、未购买商品、未启动编辑器或游戏。

## 当前方案不再作为认可基线

上一轮几何采样和网络字段检查不能证明腕肘自然度。`pistol-repair-20261022.md` 的数值记录保留为历史证据，但该版单持动作已被用户否定。

当前消费者存在明确的源动作覆盖：

- `FPSPlayerBodyAnimInstance.cpp:1697` 对 `IsSingleReload` 将 `Upper.Weight` 置0，因此配置里的第三人称 `Pistol.Reload` 不负责单持换弹的最终上身。
- 同文件1280–1284按目标掌点运行 `FitSinglePistolReload`、`FitSinglePistolArm`，重新求解双臂；其他单持路径还经过 `FPSBodyPistolPose.inl` 的腕目标及滚转修正。
- 这说明仅替换片段、仍保留现有覆盖路径，不能保证解决问题。未做本轮画面求值，不能将上述源码定位冒称为已经证明所有扭曲的唯一根因。

## 本地已有资源

实际按磁盘文件检查（包含Git忽略的二进制，不把普通 `rg --files` 的少量结果当作库存）：

| 资源 | 实际存在 | 覆盖与缺口 |
| --- | --- | --- |
| `Content/Characters/Mannequins/Anims/Pistol` | 19段：`MF_Pistol_Idle_ADS`、`MM_Pistol_Reload`、`MM_Pistol_Equip`、8方向Walk、8方向Jog | 可作为现成单枪源。此目录未找到独立开火片段，不能称为完整待机/射击/换弹套装。 |
| `Content/Characters/JasonPlayer20261003/Animations` | 上述19段的 `J_` 版本 | `player_body.json` 已引用待机、移动、换弹、装备。需要先恢复完整源臂链的所有权，而不是继续用第一人称掌点重建双臂。仅确认文件及路由，不宣称这些重定向版本已经视觉合格。 |
| `Content/ParagonTwinblast` 与 Jason 的 `TwinblastDual20261022` | 原始双枪源和此前保存的重定向片段 | 适合双持，不能替代普通单枪完整操作；Twinblast科幻枪械动作也不对应DW715/RSH弹巢机械。 |

本地 `D:/FPS3D/VaultCache/FabLibrary` 本次未列出可用缓存包；没有读取用户云端Fab已购库，因此不推断账号是否已经拥有下列付费包。

## 外部候选（按产品页与实际文件核对）

1. **MoCap Online — Pistol Pro**：[Fab](https://www.fab.com/listings/bc953490-c2e1-4be6-923a-02ad5fc7a89a)、[官方动作清单](https://mocaponline.com/pages/animlist/pistol-pro)、[官方3D查看器](https://mocaponline.com/pages/animviewer/pistol-pro)。产品页明确包含持枪待机、开火、换弹、装备及移动，提供UE工程与FBX，采用UE4骨架并提供UE5重定向资料。按覆盖程度，是成套更换的优先候选；未下载付费源、未在当前Jason上确认观感。左右主手是否都有独立原生片段需进一步看实际包，不能把“pistol”自动理解为双侧俱全。
2. **Kubold — Pistol Animset Pro**：[Fab](https://www.fab.com/listings/c5caff8c-6815-4e81-b825-aeb95967411e)。页面列150个第三人称动作和Aim Offset，包含FBX；是完整第三人称单枪家族候选。具体普通/空仓/左轮机械及左右手覆盖需查实际动作，不凭数量宣称适配完成。
3. **Agent — Tactical Pistol**：[Fab](https://www.fab.com/listings/40c1ab8b-29cd-403c-872b-01addcf22333)。动作清单明确有Idle、Fire、ADS Reload及高/低位Reload，武器数据位于IK hand gun和Weapon r骨；UEFN骨架，需要重定向。适合战术单枪风格的另一候选。
4. **GitHub — ZenXChaos/ThirdPersonShooter-AnimationSets**：[仓库](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets)、[许可证](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets/blob/master/license.md)。仓库声明Unlicense，目录实际列出23个Revolver FBX，含Idle、AimShoot、ReloadInit/Loop/End和蹲姿变体。本次按提交 `f19adc2ece4cab0f89c9236223abb97d4d2badea` 下载5段核心FBX、README和许可证至 `SourceAssets/PistolSourceSearch20261022/GitHubCandidate`。文件头显示FBX 6000旧格式，原项目面向Unity；不能直接称为UE5可用包，仍需格式转换、骨架映射与源动作观感确认，且不能把左轮装填套给半自动弹匣。
5. **MoCap Online Free Pistol Starter**：[作者页](https://mocaponline.itch.io/free-pistol-animation-starter-pack)。免费清单包含持枪待机、站/蹲开火和部分移动，没有列出换弹。适合补充候选或看基础动作，不是本次要求的完整替代套装。

Fab动态价格未在本次页面中可靠显示，不写猜测价格；没有执行任何购买。

## 重做路线

先以本地完整第三人称源恢复右手单枪的肩、肘、腕、twist骨关系，检查原片段与现有Jason重定向是否一致；停止让旧手腕目标覆盖源臂链。需要成套补齐开火与更多状态时，优先取Pistol Pro的实际源文件再接入。左手主握使用完整链镜像/重定向，保留源弯曲平面，禁止只镜像手腕位置后另造肘极。

普通弹匣与左轮机械使用各自操作分支，事件仍同步现有换弹事务。第一人称已认可动作与双持Twinblast路径不随单持重做一起替换。候选尚未做实际姿态预览或运行验收，不能宣称“已套用”或“已经修好”。
