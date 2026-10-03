# 突变体-3：飞扑掌心向下与局部下挥（2026-10-02）

> 用户已判定本版不合格：起跳时没有及时形成完整手型。当前修订为 [起跳手型 V2](Mutant3PounceTakeoffHandsV2_20261002.md)，三段正式动画已由 V2 保存覆盖。以下保留前版制作历史，不作为认可模板。

用户要求保留整体飞扑姿势，主要调整手和手腕，使飞扑过程中掌心向下并做向下挥舞。前序身体动作、肩肘配合与接地继续使用现有版本。三段正式动画已由后台 commandlet 导入手部旋转并保存；保存回执见作者目录 `install_state.json`，未进行游戏测试或视觉验收。

## 本次制作

旧 `pounce_impact_20260923` 补丁使用末节指骨方向向重力偏转，并将腕部修正限制在 55°。指尖朝下与掌心朝下是不同约束，不能用指尖方向定义掌面。

本次从 `pounce_arm_refine/Mutant3_Pounce_ReferenceRake.blend` 的原身体动作重新制作，避免在旧手部补丁上叠加翻腕。根据实际腕骨与食指、中指、小指根骨建立掌面法线，转换到各自腕骨局部空间；使用掌面法线指向下方的最短四元数旋转，不设置独立肘位、肩位或额外手掌偏航。

- 蓄力 0.20–0.60 秒渐进调整双腕，到起跳时已经朝下，避免腾空首帧突然翻掌。
- 腾空全段保持掌面朝下，腕部从轻微后仰 6°过渡到下压 12°；0.32–0.60 秒配合原身体下挥，增加小幅压腕和指爪下抓。
- 保留指根外展与拇指开口；四指额外卷曲 3°/10°/6°，拇指 1°/4°/3°，形成下抓而非握拳。
- 落地前 0.12 秒延续压腕，到 16°；0.16–0.64 秒平滑释放腕部与手指修正，回到原收势。

三段时长仍为 0.60、0.65、0.80 秒，60 fps。蓄力仅写入左右 Hand 两根骨的旋转；腾空与落地各写入双腕及 30 根指骨的旋转。安装时从正式资产复制并保留这些骨的原位移和缩放，不重导入正式完整动画，也不写入肩、上臂、前臂、躯干、骨盆、腿部或其他骨骼轨道。模型、蒙皮、骨架、材质、飞行、伤害和落地混合沿用原实现。

## 制作与安装文件

`SourceAssets/Mutant3Khaimera20260923/pounce_palm_down_20261002/`：

- `read_authoring_basis.py`、`authoring_basis.json`：原姿势读取及左右掌面局部基准。
- `author_palm_down.py`、`Mutant3_Pounce_PalmDown.blend`：可重建脚本和可编辑源。
- `animations/`：蓄力、腾空、落地三个 FBX；安装时仅作为临时动画输入，不导入模型、贴图或材质。
- `animation_contract.json`：时序、修改骨骼范围和正式资产制作前散列。
- `install_palm_down.py`、`production_hand_keys.json`：旋转轨安装脚本和按正式资产保留位移/缩放后的局部轨道。
- `before_content/`：本次正式三段动画的覆盖前本机恢复副本。
- `install_state.json`、`install-06.log`：实际保存回执与完成安装的后台 commandlet 日志。

目标资产为 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_Pounce{Windup,Flight,Land}`。只保存这三个正式动画包，不保存临时输入或替换 Skeleton。复用已有 UE Python 数据控制器，无需修改或重编译原生 C++。

本次安装完成标记为 `MUTANT3_PALM_DOWN_INSTALL_COMPLETE 3 production clips`，commandlet 退出码为 0。启动参数使用 `-unattended -multiprocess -nullrhi -nosound`；`-multiprocess` 跳过资产操作不需要的全平台 SDK 启动检测。早期失败发生在正式资产写入前，保留对应日志作为制作记录。此退出码和保存回执只说明安装落盘，未将其作为动画观感或运行测试结果。

上述 FBX、Blend、uasset 和密集轨道数据继续作为本机合法素材保存，不随源码公开。后台安装不启动交互式 UE 编辑器、PIE、渲染或额外测试；实际腕部形变和飞扑观感由用户测试，本次尚未获得视觉认可。
