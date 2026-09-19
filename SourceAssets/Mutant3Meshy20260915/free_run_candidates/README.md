# 免费僵尸奔跑候选（2026-09-15）

用户要求继续查找 GitHub 免费来源。本次仅搜索、下载与读取源文件，未改游戏动画、未运行游戏或做验收。

## 可用来源：Quaternius Zombie Apocalypse Kit

- 作者原始发布：https://quaternius.com/packs/zombieapocalypsekit.html
- GitHub 分发：https://github.com/agentkaerf/FreeModels/tree/main/Zombie%20Apocalypse%20Kit%20-%20March%202024
- 作者页明确采用 CC0，允许个人和商业项目使用。GitHub 文件中的 License.txt 同样为 CC0，但标题遗留为 Ultimate Platformer Pack；许可来源同时保留作者的本包页面，不只依赖仓库 README。
- 本地源目录：`QuaterniusZombieApocalypse/`，含三个带骨骼动画的 glTF 与原样许可文本。下载来自 GitHub main，未安装到 Content。

实际读取动画列表与时间访问器：

| 模型 | Run | Run_Arms | Run_Attack |
| --- | --- | --- | --- |
| Zombie_Basic | 0.6667 s | 0.6667 s | 0.6667 s |
| Zombie_Chubby | 0.7333 s | 0.6667 s | 0.6667 s |
| Zombie_Ribcage | 0.6667 s | 无 | 无 |

Basic 和 Chubby 各有 16 段动画，Ribcage 有 9 段。优先比较 Basic / Chubby 的 Run、Run_Arms、Run_Attack；同名片段可能复用动作，不把三个模型的名字当成三套不同狂奔。还没有实际观看这些片段，不能断言已经符合突变体-3 的发狂、厚重、写实要求。

后续只取骨骼动画并重定向到已有 Meshy 网格。保持 Hit_Chest、材质、死亡和战斗时钟；不能因参考模型是低面数卡通角色而替换当前写实外观。

## 排除：Universal Animation Library 2 Standard

已从作者上传的 https://opengameart.org/content/universal-animation-library-2 下载免费 Standard 包，并读取 `UAL2_Standard.glb` 的 43 段动画。僵尸部分只有 Zombie_Idle_Loop、Zombie_Scratch、Zombie_Walk_Fwd_Loop，没有 Zombie Run。完整商品页提到僵尸 locomotion 不能作为免费版包含狂奔的证据。

本目录保留下载包、GLB 与原样 CC0 许可，避免后续重复查找和误选。此前 Hyper Chase 商业候选仍缺源文件；免费路线已有新的实际动画候选，不需要以购买该包为继续找动作的前提。
