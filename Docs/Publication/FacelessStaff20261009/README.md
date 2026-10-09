# M-03／M-04／M-05 源码发布与本机归档

2026-10-09。目标仓库为 `https://github.com/allang2208/3D-FPS.git`，主线 `main`；宿主为 `D:/FPS3D/FPSGAME`。本次整理三名无面职员及安保帽子修订，没有重制其他怪物或变更战斗数值。

## 当前恢复入口

| 角色 | 保留的生产组合 | 制作与接入 |
| --- | --- | --- |
| 安保员 M-03 | `SK_FacelessSecurity_V13` / `_Clothing_V13`，完整身体 V09；帽 `Accessories/SM_SecurityServiceCap_V14`；V06 待机/移动、V10 攻击、V12 特殊状态 | `Tools/FacelessSecurity/repair_sleeve_skin_v13.py` → V13 outfit/clothing 导入；`repair_hat_join_v14.py` → `import_hat_join_v14.py`；原 `BP_FacelessSecurity` |
| 接待员 M-04 | V05 穿衣/衣物，V04 三段核心动作，V05 五段特殊状态；181 个衣物形态 | `Tools/FacelessStaffStates20261009/author_receptionist.py` → `import_states.py`；原 `BP_FacelessReceptionist` |
| 研究员 M-05 | V05 穿衣/衣物，V01 完整身体，V04 四段核心动作，V05 倒地/两种起身/眩晕；231 个衣物形态 | `Tools/FacelessResearcher/tailor_states_v05.py` → `import_states_v05.py` 及分批网格导入、`apply_states_v05.py`；原 `BP_FacelessResearcher` |

这些是恢复入口而非可直接批量执行的全自动安装器。先恢复下列本机输入与基础资产，再按各版本 README 的顺序执行；老导入脚本会覆盖原蓝图引用，不能扫目录全部运行。

## 必须保留的本机输入

- Meshy 原 GLB：女接待员 `Meshy_AI_Faceless_Mannequin_in_1007155702_texture.glb`、男安保 `Meshy_AI_Faceless_Athletic_Man_1008070333_texture.glb`、女研究员 `Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb`。原始来源、贴图及完整身体母版保留。
- 合法本地 Nurse/女僵尸动作与 ZombieAnimationPack（男安保 Idle_A、Walk_B、Attack_D 等），对应 UE 骨架、PhysicsAsset、材料和纹理。动作 FBX、密集曲线、NPZ、绑定采样不在公开载荷中。
- 安保 V13 读取 V11 作者源；V14 读取 V11 帽子解剖源与 V14 `Diagnosis/hat_before.json`。V12 状态保留 V06 Motion 和共用状态输入，V10 攻击保留 V06 Motion。V09 及更早作者脚本间存在依赖，原生绑定、完整身体、主 `.blend`、Inputs/Native/Motion 全部保留。
- 接待 V05 读取 V04 作者源、V04 作者/导出函数和共用状态输入；V04 又读取 V03 作者源、纹理、动作采样。研究员 V05 读取 V04 作者源与函数，V04 读取 V01 作者源及动作输入，早期 export receipt 还用于清理旧曲线。历史 JSON 不因版本早而删除。
- `SourceAssets/FacelessStaffStates20261009` 的 `source.json` 与 Motion，M05 的 state source 与 Motion，以及各阶段保存回执均留本机。密集 JSON 也属于资产派生物，不因是文本便公开。

## 归档

102 个文件、3,054,216,182 字节已移到 `trash/faceless-staff-retired-20261009/`，保留原相对目录。包含 71 个已被替代的衣物/穿衣模型或帽子导出、15 个 Blender 自动备份、6 个旧服装预览和 10 个修改前快照。移动前核对范围和散列，移动后逐文件读回 SHA-256；这是转移保存，不是删除或释放磁盘空间。

[逐文件清单](archive-manifest.json) 记录原路径、目标、大小、SHA-256、原因和保留替代物。历史 README 的旧 Delivery、Before、SourceBackup 与预览路径按该清单到本机 trash 查找。恢复旧版本时先回填所需文件；不要将 C++ `.before` 整文件覆盖到已有后续改动的工作区。

最新 V13/V14、两个 V05 导出，所有完整身体导出、主作者文件、动作、纹理、输入、原始参考图和来源均保留。旧 Content 包仍作为本机恢复资产保留，未绕过 UE 引用管理直接搬动。过程日志和排查证据也保留，不进入 Git。

## 本次公开范围

- 四个安保帽子 C++ 文件，三名角色的 F6/血条名称，以及 Nurse 角色过渡与 FR 衣物快照曲线的所属修改。
- 三名角色及共用状态的原创制作/导入脚本、历史说明、当前恢复说明与归档元数据。
- 对应怪物 SKILL 参考和衣物表面入口，个人技能与工程镜像同步。

模型、UE `.uasset`、贴图、三视图、动画 FBX、Blend、密集形态/蒙皮 JSON/NPZ、日志、构建产物及 trash 均不公开；本次没有核准这些来源的再分发许可。只克隆 Git 无法还原完整角色。工具所需 Blender 5.1、UE 5.8.2、Python/NumPy 与现有 UE 桥也须由恢复环境提供。

并行工作区中 APS 寻路、热成像、其他怪物和武器改动不属于本次发布；共享文件按所属差异暂存，工作区原内容保留。

## 实际状态

源与 UE 资产的保存、此前 Editor/Game 构建见三名角色的制作记录。M05 V04 曾获用户“基本合格”，不扩大为所有后续状态或其他角色已验收。

此前用户要求的安保复查覆盖 V13 的 1083 个动作帧及 925 个覆盖皮肤顶点，未发现超过 0.8 mm 的袖部穿出；V14 连接厚壳无开放/非流形/零面积面，当前引用与两凸体碰撞已读回。它不能替代实机过渡、布娃娃或帽子击落测试。

本次仅做归档读回和用户要求的推送检查；没有启动 UE、游戏、渲染或重新构建。公开源码切片未在独立克隆中编译，游戏表现仍由用户测试。
