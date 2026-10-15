# M66 手部尖刺修正 V08

2026-10-14 用户反馈横扫时手部被拉出尖刺。沿用怪物工作流，针对原 V05 网格和 V06 横扫读取实际权重、骨链与变形输入，没有截图、渲染或启动游戏。

## 定位与修正

1. 部分指面顶点混入 `Bone_016/017` 腿部权重，另有少量掌部顶点混入躯干权重。读取原动作时发现，一条静态约 1.98 cm 的指面边在抬手姿态被拉到约 134.6 cm。相邻顶点中一个仍受腿部驱动、另一个只随手指，形成长三角尖片。
2. V06 按真实腕部重做臂链时，漏掉 `Bone_024 → Bone_035 → Bone_034` 的辅助分支。旧动画中 `Bone_035` 出现米级局部平移补偿，63 个以 `Bone_034` 为主权重的顶点没有跟随前臂。

V08 仅处理右手/远端前臂中已定位的污染权重：移除腿部和躯干影响，按原有臂/指权重比例归一化，并同步重合 UV 接缝。共修改 19 个顶点，保留几何、UV、材质、全部 95 根骨骼、V05 口部修复和眼珠控制。

复制 V06 横扫，仅将两根辅助骨恢复为原待机局部姿态，让它们正常继承前臂。主肩肘腕轨迹、躯干节奏、2.6 秒总长与 1.00～1.35 秒接触窗口不变。保留 V07 死亡物理和表面回退所需的 CPU access。

## 制作与接入

- `read_deformation.py` / `Records/deformation_inputs.json`：本次错误的输入定位记录。
- `author_hand.py`：从 V06 可编辑源继续制作，输出 `Authoring/M66_hand_continuity_v08.blend`、修正版模型 FBX 与横扫 FBX。
- `import_skin.py`、`import_motion.py`、`install_character.py`：导入到 `/Game/Monsters/IncineratorBossM66/HandContinuityV08/`，保存原角色的网格、攻击动画及命中采样。
- 既有编辑器用工程互斥桥执行 `install_editor.py`；后台窗口用 `run_headless_install.ps1`。旧版本资产保留。

首次导入在 CPU access 属性接口处停止，已改用 UE 的 `SkeletalMeshEditorSubsystem.set_allow_cpu_access`。恢复批次只允许本次已创建的 V08 网格与其原骨架脏包继续保存，仍保护其他未保存的 M66 资产。

2026-10-14 已完成模型、动画和原角色绑定保存。编辑器关闭后，后台批次 `Records/install-20261014-231405/` 正常退出（退出码 0）；`Records/skin_import.json`、`motion_import.json`、`character_install.json` 为保存回执。当前原角色使用 `SK_M66_HandContinuity_V08` 和 `A_M66_ClawSweep_V08`，V07 物理与 CPU access 保留，22 帧 × 17 点命中采样同步保存。本次未修改 C++ 或 DLL 接口。

未进行修复后的运行或联机测试，实际外观由用户体验；重新生成的 M66 使用新网格和动画。
