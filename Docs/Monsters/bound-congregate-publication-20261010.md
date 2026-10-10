# 缚群 M-88：V20–V34 整理与源码发布

用户要求将废案移入 trash、沉淀 SKILL 并发布到 `https://github.com/allang2208/3D-FPS.git`。本次遵循根目录 `WORKFLOW.md` 第 4–8 节，在 `D:/FPS3D/FPSGAME` 直接整理和提交，精确选取本怪物及必要共享接入的改动。

## 当前有效内容

- 活体为 `TentacleReachV29/SK_BoundCongregate_TentacleReachV29`，衣物采用 V25 扩大的后背／下缘，保留 V24 的贴身蒙皮、自由破边模拟与覆盖区裁面结构。用户认可 V24 不再穿模；不把这一反馈扩大成全部衣物动态验收。
- V28 拍击已获用户认可：四前肢错峰拍地、主体承重摆动、各落掌范围伤害、慢蓄力和快速下砸。保留原五次接触时刻与伤害去重。
- 触手最远 3000 cm，拖动 195 cm/s、移动 240 cm/s、转向 100 度/s。被缠时禁止移动、施法与技能，枪械与快速近战可用。一次快速近战真实接触或枪击耗尽触手独立 300 生命可挣脱；拖近后解除并接撕咬。
- V33 撕咬起手 350 cm、嘴部判定延伸 235 cm，在 0.54–0.65 s 窗口内允许漏空后继续接触，只结算一次；成功伤害附加三层流血及五秒致残。
- V34 死亡从致命打击时的显示姿态交接，取消水平初速度和短暂撑脚，解除全部肢体的压缩支撑；保留主体体积、接触及防拉伸。V32 死亡表现被否定，其尸体几何仍被 V34 复用。V34 已实际保存，尚未游戏体验验收。

正式蓝图仍为 `/Game/Monsters/BoundCongregate/BP_BoundCongregate`，F6 稳定 ID 仍为 `BoundCongregate`，显示名为「缚群 M-88」。

## 归档

308 个文件、334,796,183 字节（约 319.28 MiB）已移到 `trash/bound-congregate-publication-20261010/`。逐项原路径、目标、大小、SHA-256、原因与替代物见 [归档清单](bound-congregate-retirement-20261010.json)。移动前解析绝对路径，移动后读回大小与散列；没有永久删除。

- 衣物 V20／V21／V23 的失败制作输出和专属工具。
- 被 V28 替代的 V22／V26／V27 拍击制作输出、审阅图及专属工具。V28 直接读取 V25 母版，不读取这些旧输出。
- 本怪物旧 before 快照、Blender 自动备份、已结束的桥接重试记录、一次性停止／关闭／编译辅助脚本和 Python 字节码。

保留全部 `Content/Monsters/BoundCongregate` 本机包：其中仍有骨架、物理资产、材质与导入模板依赖，不能因版本号旧就外部移动。保留 V24 有限认可参考、V25 衣物源、V28 动作源、V29 触手源、V32 尸体作者数据、V34 配置、原始模型／PBR，以及各最终构建日志和保存收据。此前 [2026-10-08 的 618 项归档](bound-congregate-retirement-20261008.json)继续保留。

恢复归档项时按清单校对 SHA-256，再复制到空闲的原路径；有现存文件先处理版本冲突。旧文档中的原路径属于历史位置。恢复候选不代表可以重跑旧安装器覆盖当前蓝图。

## 公开与本机恢复边界

公开范围为 `BoundCongregate*` 原生代码、M14 连续尸体的本次扩展、必要的输入／状态／部位伤害接入、保留的原创作者工具、V28 小型动作合同与原始数值配方、说明和 SKILL。共享文件中其他武器、技能、热成像、UI 和角色工作保持未提交，不发布。

Meshy 原模型及其派生网格、PBR、Blend/FBX、动画采样、几何／蒙皮／尸体嵌入、UE 包、插件、日志、二进制和 trash 留本机。没有新增原始资产再分发许可。此前已发布的原创 `BoundCongregateWhipMotion.inl` 编译期常量、BSD-3-Clause 参考许可及来源说明继续保留；王室幽魂仅作招式结构参考，未提取其游戏动画。

完整恢复首先需要本机 Content 与 SourceAssets 备份。只克隆 Git 不能得到可运行的完整怪物。重建链按以下顺序理解，不默认执行：

1. 早期完整身体、RigV3、触手、V14／V18／V19 混合母版继续保留。V19 衣物不合格，但 `author_garment_v25.py` 仍从其完整身体／骨架出发；V20／V21／V23 无需回到制作目录。
2. `author_garment_v25.py` → `materials_garment_v25.py` 与 `import_garment_v25.py`，后者复用 `import_garment_drape_v18.py` 的分阶段导入。V24 Content 模板与 V25 作者输出的 `collision_recipe.json` 是本机依赖。
3. `author_combat_v28.py` 从 V25 制作两段攻击，读取公开的 `CombatV28/motion_contract.json`；`import_combat_v28.py` 使用 `before_values.json` 的固定基准，避免重复叠加百分比。之后制作／导入 V29 模型，再用 `import_capture_v30.py` 恢复最终移动、拖速和触手生命。
4. `prepare_death_v32.py` → `author_death_v32.py` → `install_death_v32.py` 制作独立尸体；最后 `install_death_v34.py` 复制其数据并设置无支撑节点、保存新配置与活体绑定。V32 的 `authoring.json`、`surface.bin.skin.json`、`cage.json`、`embedding.bin` 为本机恢复输入，不归档、不公开。
5. 最后应用 `save_bite_v33.py` 的绝对判定配置。重建从早期阶段开始才按序应用；不要在已经是 V33/V34 的资产上直接重跑会回写早期数值的安装器。

常规构建和后台保存入口为 `build_death_v34.ps1` 等当前脚本。已经运行的编辑器仍走现有桥的批次互斥；不得为整理推送启动 UE、PIE 或执行旧 review/render 脚本。

## SKILL 与检查边界

个人和工程 `ue5-monster-workflow` 同步：入口指向最新 M-88 状态，专用参考维护衣物覆盖结构、全身发力、触手距离／显示／判定同步、真实束缚状态、接触窗口去重与无支撑死亡。非人形死亡参考增加相应适配入口。失败候选、用户有限认可、成功保存和未测试状态分别记载。

本次仅做用户要求的整理／推送检查：依赖保留、归档散列、精确暂存、完整变更范围、空白、文件大小、敏感信息、公开许可、上游提交及推送后远端 SHA。没有重新构建或运行游戏、模拟、渲染。V34 先前 Editor/Game 构建成功与实际保存记录仍在本机；这些记录不等于对本次精确发布子集重新编译或视觉验收。
