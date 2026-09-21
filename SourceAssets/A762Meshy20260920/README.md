# A762 — Meshy 高细节候选

最新修订记录：[Refinement04/README.md](Refinement04/README.md)，重建双杆与尾板的连续接头、支撑骨架和橡胶托垫，并已更新游戏资产。后照门、前端缺面和 ADS 表面修订在 [Refinement03/README.md](Refinement03/README.md)；弹匣及枪口重建记录在 [Refinement02/README.md](Refinement02/README.md)，早期精修在 [Refinement01/README.md](Refinement01/README.md)。保留原候选与首次接入源。

2026-09-20。任务：按用户提供的两张图制作 A762 步枪外观，尽可能还原可见细节。用户随后选择该候选并要求按枪械标准接入 UE5、复用 AKM 当前音效。候选生成记录保存在本目录；后续游戏接入、机械分件、绑定和动作源文件见 [Integration/README.md](Integration/README.md)。

## 参考与形体约束

| 输入 | 用途 |
| --- | --- |
| References/user_01_color_side.png | 主体外形、机匣开口、护木、金属与聚合物配色、弹匣弧度和边缘筋条 |
| References/user_02_clay_threequarter.png | 全枪比例、图一裁切之外的细杆枪托、顶部结构和前端层次 |
| References/a762_side.png | 内置 imagegen 整理的完整侧视输入，枪托左、枪口右 |
| References/a762_front_threequarter.png | 同一候选的前斜上方输入，辅助表达管件宽度与枪口 |
| References/a762_rear_threequarter.png | 同一候选的后斜上方与另一侧输入，辅助表达枪托和顶部 |

三张整理图是生成模型的条件图，不是实际模型渲染，也不是用户确认的精确三视图。源图没有完整表达的另一侧、底部、细部厚度为视觉推断。保留两个用户原图，不把生成图当作原始证据。源图低分辨率且存在遮挡，小文字、内部结构和不可见表面不能保证复刻。

重点：细杆骨架枪托及杆间镂空、细长机匣、长顶部导轨、倾斜握把、细扳机护圈、平滑圆筒护木、前部导气管与枪管的分离、大弧度弹匣及边沿细节、前准星和短筒形枪口件。排除原图背景的另一把枪、地面碎石、UI、红蓝灯光和托枪支撑物。

## 本轮生产设置

- Meshy `multi-image-to-3d` / `meshy-7.1`，单个候选。
- `geometry_resolution=2k`；`texture_resolution=8k`；`enable_pbr=true`。
- `should_remesh=false`，保留原始高细节生成网格；不把设置面数等同于实际几何细节。
- `image_enhancement=false`，采用已整理输入；`remove_lighting=true`。
- GLB、FBX、OBJ 与单独 PBR 贴图本地归档。材质贴图实际种类和尺寸由服务输出决定，8K 参数指基础色目标。
- 不请求额外透明/多视图缩略图，不启动 UE、PIE、验收渲染或测试。
- 设置、输入与提示词保存在本目录。生产客户端改编自工程既有 Meshy 客户端；仅保留 balance/submit/poll 路线，独立保存本任务记录。
- API key 仅保存在交互式生产进程环境中；回执剥离签名查询串。没有将密钥写入脚本、设置或文件。

## 生产入口

Python 3.11：`meshy_session.py`。在隐藏输入中提供密钥后执行 `balance`、`submit`、`poll` 或 `watch`。`submit` 有任务回执时复用原任务；已有请求记录却没有 id 时必须恢复原任务，不能重复扣费提交。`watch` 每 30 秒读取任务状态，完成后立即下载资产。输入 `exit` 结束进程并清除进程内密钥。

`Authoring/create_editable.py` 使用 Blender 导入原始 GLB 并打包纹理，另存可编辑 .blend，不改变生成网格或声称完成活动件拆分。Cloud FBX/OBJ 保留为原始导出。

## 来源

用户提供的两张游戏截图，权利属于各自原作者，未另行授予公开再分发授权。图像整理使用内置 imagegen；三维模型由 Meshy 生成。保存在本机候选目录，不公开发布。账户与生成资产的许可仍以用户账户方案及 Meshy 当期条款为准。

- https://docs.meshy.ai/en/api/multi-image-to-3d
- https://docs.meshy.ai/en/api/pricing

## 当前状态

Meshy 候选生成成功，任务 `01a0bec4-76e1-71d2-bf1e-9397b1b1785b`，实际消耗 40 积分。原始模型与候选工程保留；后续接入另存到 `Integration`，包括机械分件、Manny 武器骨架绑定、11 段 A762 动作及游戏目录接入。最终文件清单及交付状态见 `DELIVERY.json` 与 `Integration/DELIVERY.json`。按照用户规则，未进行游戏运行测试或视觉验收。


## 通用配件接入（Accessories05）

在用户认可的 Refinement04 基础上接入七类外观配件及现有通用枪管数值选项，拆分机瞄固定底座和可折叠上部，按导轨调整瞄具与 ADS。攻击及强化系数为 AKM 的 95%，基础后坐力为 75%，稳定性为 125%，射速 900 发／分钟。详见 Accessories05/README.md 和 DELIVERY.json；已完成导入保存；最终编译返回 NoChanges，当前源码无待编译项，未进行游戏测试。


## 瞄具材质补齐（OpticFinish06）

已按用户要求逐槽读取并补齐四种瞄具与倍率环的材质统一，直接使用 A762 上机匣的涂层参数，保留原始分区和光学通道。实际网格入口不变，材料与记录见 OpticFinish06/README.md。未运行游戏或渲染。


## 装备栏图标修复（InventoryIcon07）

补齐缺失的 A762 基础 PNG 与 ue_icon 引用，修正动态图／掉落展示把 Handguard 当作手臂隐藏的问题。已确认 UE 图片解码；未运行游戏测试。记录见 InventoryIcon07/README.md。
