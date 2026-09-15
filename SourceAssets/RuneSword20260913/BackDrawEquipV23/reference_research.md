# GitHub 装备与转花剑参考 · 2026-09-14

用户要求查找第一人称单手转花剑参考。本次搜索 first-person sword spin / flourish / twirl / equip 等组合，并阅读相关仓库说明。没有找到已确认具有合适成品动作、可直接接入当前 Manny 第一人称骨架的单手转花剑资源；这不是对 GitHub 全部资源的穷尽结论。

| 仓库 | 实际查到的内容与用途 |
| --- | --- |
| [BigAndCrispy/Unity-First-Person-Melee](https://github.com/BigAndCrispy/Unity-First-Person-Melee) | README 声明作者提供免费 CC0 模型、声音与动画；[LICENSE](https://github.com/BigAndCrispy/Unity-First-Person-Melee/blob/main/LICENSE) 为 CC0 1.0。适合参考基础第一人称握持、挥砍与节奏。项目已有本地归档，本次没有重新导入其资产。 |
| [rico345100/unity-basic-melee-combat-system-for-fps-rpg](https://github.com/rico345100/unity-basic-melee-combat-system-for-fps-rpg) | README 展示基础攻击、武器摆动、格挡与踢击，武器切换列为后续计划；本次未确认可用的单手转花剑片段及资产复用许可，没有复制其动作。 |
| [Trainguy9512/locomotion](https://github.com/Trainguy9512/locomotion) | Minecraft 第一人称动画项目，风格与当前写实手臂不同，README 标注 All Rights Reserved；没有复制其动画。 |
| [WynnSystems907/COBRA-FPS-Feelkit](https://github.com/WynnSystems907/COBRA-FPS-Feelkit) | 程序化第一人称表现和近战占位方案，未提供本次要找的成品转花剑骨骼动画。 |

本地 `../Reference/COMMIT.txt` 记录第一项归档提交 `592b08e2e1fe81a51f712fa65d806fa3621e2032`。其 `Arms.fbx.meta` 动作表包含 `Sword_Idle`（0–80，循环）、`Sword_Slash1`（0–20）、`Sword_Slash2`（0–20）、`Sword_Walk`（0–22，循环），没有命名为 Equip、Spin 或 Flourish 的片段。本次读取该动作表、控制器和原参考画面，结合现有 V5 装备源的关键帧与时长制作 V23。

两个仓库的 GitHub API 文件树请求遇到 HTTP 403，回执保存在 `github_research.json`；资源判断仅限实际读取的仓库页面与本地归档，没有声称完成所有分支或二进制内容检查。

制作决定：先实现用户首选的右肩后拔剑，再由左手接稳，整段 1.20 秒。V23 为现有授权手臂与剑上的新制作动作，没有把基础挥砍参考称为转花剑来源。
