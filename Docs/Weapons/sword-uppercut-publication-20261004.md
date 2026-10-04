# 上挑与四枚技能图标：整理发布与恢复

2026-10-04。本轮发布本对话的上挑技能、判定、成长、消耗、图标恢复配方和经验文档。共享工作目录内其他任务的腾云游龙普通第三段、固定削韧、门与怪物等增量不纳入本次提交；公共上挑代码保留独立技能入口。它们的本地文件不回退。

## 当前版本

- 动画：GripRecoveryV15，标准和长握距均为 2.05 秒。运行包仍名为 `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard` 和 `/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip`。V1 是资产路径，不能据此判断姿态版本。
- V16 镜头幅度扩大、前踏 150 cm；V17 接入普通攻击空间扰动、突刺型单目标扫掠、同级重击完整倍率的 70%、独立修炼；V18 实际释放消耗 25 体力、基础 CD 8 秒，存档版本 21；V19 基础判定扩大 25%，距离再按每级 1% 成长。
- V20 将主动上挑的 150 cm 前踏集中于 1.000–1.050 秒，刀刃扫掠使用实际碰撞约束后的位移；不再等到 1.160 秒才走完前踏。接触窗仍为 1.000–1.125 秒。距离公式不是额外前移采样原点，受阻也不虚构位移。
- 冲刺攻击与重击的专项源码对照：冲刺地面前踏在接触前完成，判定随角色当前位置；重击没有自动前踏，使用逐帧瞄准坐标。这些是源码结论，尚无本轮运行测试结论。
- 四枚采用图标：上挑、重击、冲刺攻击、旋风。统一圆角银色方框、暗色无脸练功人物与浅色剑光。当前为二维生成图，未建立统一三维人物母版。

## 本机恢复顺序

1. 恢复合法的 V7 手臂／骨架、标准及长握柄剑和既有普通攻击音效、空间扰动资产。母版包括 `SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend`。
2. 保留 `SourceAssets/SwordUppercut20261003/GripRecoveryV15`：`SourceV14/{Standard,LongGrip}/editable_keys.json` 是冻结输入，不是废案；`inputs.json`、当前两套关键帧、Blend、FBX 仍在本机。作者入口 `author_uppercut_v15.py`，辅助模块为同目录 `author_common.py`、`arm_support.py`。
3. 在具备上述输入后制作两套导出，再执行 `install_uppercut_v15.py` 实际导入保存。默认不读回姿态、不触发测试；只有显式传入 `READ_SAVED_POSE=True` 才执行附加读回。不能只提交脚本就声称重新安装成功。
4. 四图源分别是 `SourceAssets/SkillIconRoundedSquare20261004/UppercutSilhouetteV5/sword_uppercut_silhouette_v5.png`、`MartialSilhouetteFamilyV1/{heavy_strike,dash_attack,whirlwind}_silhouette_v1.png`。既有 `DeploymentV1/deploy_martial_icons.py` 和 `Tools/UI/prepare_cold_steel_skill_icons.py` 记录制作与正式映射。
5. 正式纹理在 `Content/ColdSteelData/Skills/{sword_uppercut_cold_steel,heavy_strike_cold_steel,dash_attack,whirlwind_cold_steel}`，保留 PNG 和 UE 包。历史部署回执 `DeploymentV1/deployment_result.json` 记录四图保存，本次整理未重新生成或导入。
6. 编译当前源码可使用 `SourceAssets/SwordUppercut20261004/LungeContactV20/build_uppercut.ps1`；不因此启动编辑器或游戏。

## 归档与公开边界

已将 414 个废案文件、共 621173963 字节移至 `trash/sword-uppercut-retired-20261004/`，保留相对路径。包括 V1–V14 旧作者目录、旧图标样稿、PreviousAssets/PreviousIcons、废弃节奏头文件和被 V20 替代的构建包装脚本。归档前后 SHA-256 一致。

详见 [逐文件归档清单](../../SourceAssets/SwordUppercutPublication20261004/archive-manifest.json)、[归档计划](../../SourceAssets/SwordUppercutPublication20261004/archive-plan.json) 和 [执行脚本](../../SourceAssets/SwordUppercutPublication20261004/archive_retired.ps1)。当前动作输入、正式 Content 和独立预览地图保持本机。旧文档中的 V1–V14 作者路径现位于上述 trash 前缀下；历史构建回执同理。

公开原创 C++、数据配置、作者脚本、少量参数、提示词、文档和 SKILL。没有采用付费动画；动作根据用户自有参考重新制作。用户聊天视频不公开；Epic/Manny 相关骨架与完整姿态、第三方音效、二进制资产、图像、Blend/FBX、密集采样、日志、机器回执及 trash 均留本机。此次对已追踪的密集采样和机器回执停止追踪，保留仍有用的本地文件；没有改写或清除 Git 历史。

因此克隆源码不能自动恢复完整可运行项目，必须先恢复本机合法内容依赖。图标完整提示词和选定风格配方可公开，生成图片本轮按源码仓库规则不额外加入白名单。

## 构建与测试状态

V20 制作时，本机共享工作树的 Game 和 Editor Development 后台构建均成功，回执在 `SourceAssets/SwordUppercut20261004/LungeContactV20/build_receipt.json`。该证据包含当时共享工作树，不能作为本次拆分发布快照单独构建成功的证明。

本轮仅进行用户要求的仓库整理与推送检查，没有重新编译、运行游戏、打开编辑器或追加测试。动作与命中体验由用户测试。
