# 现代普通僵尸 V01 · 2026-09-06

用户授权通过公开资产获得现成人形与动作，统一风格和材质后替换游戏现代僵尸。本轮已接入主场景普通僵尸和副本普通僵尸；工头、喷吐僵尸继续使用各自模型。

## 选择与来源

- 采用 [Denys Almaral](https://denysalmaral.com/post/free-zombie-animations-for-your-games/) 的 ZombieMale_A：现代衬衫、领带和长裤，附 10 段作者制作的僵尸动作，CC BY 4.0。下载来自作者公开演示页 HTML 列出的 glTF、BIN 和调色板资源；清单见 `denys-download-report.json`，原文件保留在 `denys/`。
- 补充 [Quaternius UAL](https://quaternius.com/packs/universalanimationlibrary.html) 的 Death01 与 Hit_Chest，CC0。作者公开动画查看器的模型和动画经 Godot 资源接口导出后重定向到同一骨架。原始公开包、提取脚本和原动作渲染均保留。
- 实际查看过 Denys 五个男性版本、现有旧模型、Quaternius Zombie Apocalypse 模型和动作；Quaternius 外观更卡通，未选。Pixelhouse 的公开僵尸素材动作数量较少，未选。Mixamo 需要账户，本轮未使用。
- [完整署名与改动声明](../../../assets/models/modern_zombie/LICENSE.md)。发行时保留 Denys Almaral 的署名。

## 外观与文件

采用灰绿尸肤、低饱和旧衬衫、暗灰裤装、哑光鞋与干血区域；重做 UV、平滑法线与蒙皮权重规范化，烘焙 2K 底色、粗糙度和法线，游戏中合并为一个不透明 PBR 材质。保留原造型身份，仍属于低面数风格。

- 可编辑源：`modern-zombie-v01.blend`；导出：`modern-zombie-v01.glb`。
- 游戏资源：`assets/models/modern_zombie/modern_zombie_v01.glb`。
- 31 骨骼、864 顶点、1724 三角形。最大四骨影响，权重归一化误差约 4.12e-8。
- `build_modern_zombie.py` 为可复现制作脚本；`build-report.json` 记录全部动画时长和骨架适配数据。
- [原游戏 / 作者原版 / 统一材质对照](previews/comparison.jpg)。

## 动作与游戏配置

先实际渲染原生左右攻击、跛行、普通走、慢走、待机和跑步，并查看 UAL 原生倒地与受击动作，再制作适配版本。原始动作帧保留在 `rendered/A/` 与 `rendered/ual/`。

| 游戏动画 | 时长 | 处理与用途 |
| --- | --- | --- |
| Idle | 7.333 秒 | 原作者待机；最后 0.2 秒闭合循环 |
| Walk | 2 秒 | 原作者不对称跛行；最后 0.2 秒闭合循环；按实际移动速度推进 |
| Attack / AttackRight | 各 1.567 秒 | 左右交替挥击；原 70 帧动作整体调整到 47 帧，保留姿态曲线 |
| Death | 2.4 秒 | UAL 倒地重定向，修正脚底与地面，终帧保尸 1 秒 |
| HitReact | 0.333 秒 | UAL 受击重定向；保留为备用，没有新增硬直玩法 |

10 段 Denys 原片段加 4 个游戏别名和 2 段 UAL 动作，共 16 个动画条目。原跑步等备用片段尚未绑定新的游戏状态。

生命 120、基础伤害 13、主场景追击 0.61 m/s、2 秒攻击冷却保持原值。新动作有效命中窗口为 0.60–0.77 秒。头部命中绑定骨架；躯干胶囊缩短到 1.4m，避免挡住新体型头部。`modern_zombie.gd` 提供新时序；副本脚本继承该配置，防止运行时换脚本丢失参数。

## 验证与预览

- 最终 GLB 重新导入 Blender 后，在 6 段游戏动画采样 918 个姿态，检查骨架、蒙皮、有限坐标与地面位置，见 `asset-validation.json`。最深地面穿入约 1.33cm，出现在左攻击中间姿态。
- Godot 普通僵尸战斗行为、动作衔接与循环、弱点命中、工头和喷吐僵尸回归检查通过。日志保留在本目录。
- 实际主场景追击 120 个物理帧约 1.21m，保持落地；检查正式资源、左右攻击、时长、副本继承和头部锚点。`tests/test_modern_zombie_integration.gd` 为入口。
- 最终默认渲染器主场景检查 `runtime-final.log` 无脚本或引擎错误。编辑器无头导入和喷吐僵尸独立回归退出时仍有资源/RID 清理提示，不能把这些日志描述成完全无错误。
- 默认 D3D12 Forward+ 实际 GLB 完整逐帧渲染。GIF 按原时长量化到 10ms，帧数与总时长复核见 `previews/preview-validation.json`。Death GIF 为方便重复查看而循环播放，游戏中只播一次。
- [跛行](previews/Walk.gif) · [左攻击](previews/Attack.gif) · [右攻击](previews/AttackRight.gif) · [倒地](previews/Death.gif) · [待机](previews/Idle.gif) · [备用受击](previews/HitReact.gif)。

主场景截图保留在 `runtime/`。上述自动化检查和画面审查不等于玩家完整战斗试玩；动作自然度可直接通过本次实际模型 GIF 评价。

## 2026-09-06 整理记录

已清理数字命名逐帧截图与 Blender 自动备份；最终 GIF、动作检查表、命名近景、源文件、许可与重建输入保留。再次打包预览前先按重建步骤重新渲染。制作目录已用 `.gdignore` 排除游戏导入。

发布目录保留 Denys / UAL 的构建输入、来源和最终输出；未选用的 Pixelhouse 等研究下载仅留本地，不作为本项目素材发布。旧二维僵尸 V03 的对照模型可能仅存在于原工作区，预览准备会跳过缺失的历史模型；现代模型重建不依赖它。
