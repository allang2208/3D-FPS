# 缚群衣物暂停、归档与源码发布

2026-10-08 用户反馈整体衣物仍不合格，要求暂停、归档废案、沉淀 SKILL 并允许推送到 `allang2208/3D-FPS`。本次停止制作；V18、V19 都不作为合格服装模板。下文记录保留现场和公开恢复边界，不是新一轮游戏验收。

## 保留现场

- 最近已保存蓝图：`/Game/Monsters/BoundCongregate/BP_BoundCongregate`；其 V19 保存回执记录 VisualMesh 为 `GarmentRebuildV19/SK_BoundCongregate_GarmentRebuildV19`，匹配尸体网格和软体数据在该版本 `Corpse/`。本次未修改 UE 资产或游戏数值。
- 保留全套 `Content/Monsters/BoundCongregate` 本机包。旧网格／骨架还作为兼容骨架、物理资产、材质及导入模板存在，不能依据版本号直接挪走；本次没有对正在使用的 Content 做外部移动。
- 保留用户提供的 Meshy GLB、概念图、PBR、RigV3、原动作、V17 撕咬／连拍以及身体、触手、衣物混合母版。V14 被 V17 动作脚本读取；V18 被 V19 作者脚本读取，因此保留是恢复需求，并非认可旧衣物。
- 暂停前配置：移动 120 cm/s、动画源速度 50、加速度 300、制动 480、转向 50 度/秒；触手 CD 20 秒、前方 120 度、F 三次快速近战挣脱与提示、保留第一人称手持显示。
- 用户曾认可触手抽打主体。衣物贴合、拉扯、破碎、尖刺与动态效果仍未完成；V19 的成功构建／保存不能覆盖这项反馈。

## 本次归档

618 个文件，436,382,443 字节（约 416.17 MiB），移到本机 `trash/bound-congregate-paused-20261008/`，保留原相对目录。逐文件记录在 [归档清单](bound-congregate-retirement-20261008.json)，移动前后大小和 SHA-256 已读回匹配。

归档包括旧 `.blend1` 和 before 快照、被 V17 替代的 V16 作者输出及三个脚本、未采用的甩鞭模拟试验、历史渲染／诊断图片、执行日志、一次性重试脚本和会再次乘二的旧移速脚本。日志与预览属于已结束阶段的过程资料，存入归档不等于否定其全部历史结论。

仍作为制作输入的模型、几何采样、权重、分区、参数和当前回执保留原路径。历史文档提到的已归档证据按清单的 `source → destination` 找回；不要为了复现旧试验直接覆盖当前游戏包。

恢复归档项：按清单选取明确需要的文件，先比对 SHA-256，再复制回 `source`；若目标已存在，先处理版本冲突，不覆盖。trash 不进入 Git。

## 源码发布与许可

本次仅发布 `BoundCongregate*` 原生代码、必要共享接入片段、保留的 `Tools/BoundCongregate` 脚本、少量作者配方、历史记录、暂停记录、归档元数据及对应 SKILL。共享文件中其他武器、怪物、UI 和角色工作的改动不包含在本提交中。

`BoundCongregateWhipMotion.inl` 是原创 MuJoCo 制作脚本生成的编译期运动常量，作为本怪物原生编译依赖随源码发布；模型顶点／完整蒙皮、原始姿态转储、软体嵌入和其他大体积制作输出不发布。甩鞭参考源码只用于研究，原 BSD-3-Clause 许可和来源说明随小型参考目录发布，原始参考源码只留本机：MosesAndLily/whip-project-targeting，commit `8025f9f156bf3cf591afbedca18eaa03e3846d4a`。参考算法不是《艾尔登法环》的动画资产，本怪物动作没有提取该游戏文件。

用户提供 Meshy 模型的原始再分发条件未在此批准。GLB／FBX／Blend、纹理、概念图、UE 包、二进制、工具运行环境、日志和 trash 都留本机。仓库源码不能单独恢复完整可运行怪物。

## 本机恢复入口

1. 优先恢复完整本机 `Content/Monsters/BoundCongregate` 与 `SourceAssets/BoundCongregateMeshy20261006` 备份。公共 Git 不提供这些资产。
2. 从原始 GLB 制作时，`assess_source.py → prepare_rig.py → author_fabric.py → author_model.py` 为早期源链，随后通过 RigV3、触手分区 V2、V3、V4、DynamicsV6、ClothV7/V8/V9、FullWhipV10、SurfaceFitV12、GarmentContinuityV14、GarmentDrapeV18 到 GarmentRebuildV19。旧衣物部分仅用于重现当前失败现场，不建议作为新衣物方案直接采用。
3. V17 攻击从 V14 母版独立制作，配方为 `MeleeV17/motion_contract.json`；`import_melee_v17.py` 保存攻击片段及引用。身体／步态与攻击绑定不能因衣物暂停被替换。
4. V19 `import_garment_rebuild_v19.py` 复用 `import_garment_drape_v18.py`，先 prepare，再由 `author_soft_corpse.py --garment-v19` 生成匹配嵌入，再 finish 保存；脚本参数以文件为准。导入依赖先前模板骨架、物理资产、材质和共享 M14 连续软体管线。仅恢复代码不等于已导入。
5. 最后按 `fix_move_response_20261008.py`、`set_turn_speed_20261008.py`、`set_tentacle_cooldown_20s.py` 的绝对数值恢复最新配置，避免旧安装脚本重新写回早期移速或 2 秒 CD。当前暂停不执行以上制作／导入流程。

## SKILL 与本轮检查边界

经验同步到个人与工程镜像 `ue5-monster-workflow/references/bound-congregate.md`：失败状态、巫婆机制复用边界、解剖支撑、单位尺度、顶点色解码、凸包 CCD 历史开销、分段发力、速度分母与混合输入保留。

本轮仅进行用户要求的仓库／推送整理检查：归档散列、精确暂存范围、完整差异、空白错误、体积、敏感信息与许可、上游差异以及推送后远端 SHA。未重建原生模块，未运行游戏、PIE、渲染或验收测试；衣物问题保持未解决状态，由用户决定何时继续。
