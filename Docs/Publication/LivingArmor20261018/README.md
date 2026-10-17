# 生活区收集品、火甲、冰甲与持锤施法发布

本次整理对应同一对话已完成的制作及修复，目标 `https://github.com/allang2208/3D-FPS.git` 的 `main`。遵守 AGENTS.md 与 WORKFLOW.md 第 8 节：精确路径暂存、保留并行修改、普通推送。没有启动 UE、PIE、渲染或重新执行玩法测试。

## 发布范围

| 内容 | 本次交付 |
| --- | --- |
| 生活区收集品 | 香水 1×2、音乐播放器 1×2、相机 2×2、笔记本电脑 3×2；模型/材质原创制作脚本及四个非装备数据条目 |
| 容器 | 67 个生活区入口、8 个池；2 个排水工具箱复用 research_maintenance，首次固定一件 |
| 等级修复 | StageTraining 直接提交奖励后 State，避免 Snapshot 的旧 Level/AttributePoints 覆盖升级；保留并行经验 HUD 工作 |
| 灼锋焰甲 | 火球衍生武器火焰、连续足环 V5、取消上身火焰；挂点、飞行箭、CastId/退款/状态恢复/奖励归属等修复 |
| 坚冰铠甲 | 无杖防御魔法、技能卡片/修炼/快捷栏/网络接入；镜头头盔 V5、身体骨骼冰甲 V6 |
| 双手锤施法 | 胸腔基底与整条左臂方向修正；阶段/武器实例缓存、CastPalmProgressRate 复制与有限外推 |

完整混合工作区才是当前本机游戏。共享文件的修改保存在 `shared-integration.patch`，每个前置和结果的 UTF-8/LF SHA-256 见 `shared-prerequisites.json`；基线是当前宿主去掉本次修改后的精确文本，不是 Git HEAD。其他并行修改是这些补丁的前置，不在本次提交中公开。不能直接把这个源码切片当作干净检出可构建的整套游戏。

已公开的前期技能宿主参考 `../SkillMagic20261015/README.md`；该批补丁包括技能预加载、部分陨星/统一离场结算与审计宿主。当前补丁还依赖本机身体动画、库存/网络档案、装备和天气等宿主的后续增量。先按逐文件散列匹配前置，再合入对应补丁；散列不同应人工对照，不能盲目覆盖共享文件或连用 `--reject` 代替审查。源码路径直接提交的文件见 `source-manifest.json`，数据/配置采用从 HEAD 仅重放指定 ID 的索引内容，工作区其他条目原样保留。

## 资产恢复

### 收集品

`SourceAssets/StaffLivingCollectibles20261016/Scripts/` 保留模型、表面、图标、导入和安装配方。`setup.py` 生成设计参数及隔离导入宿主，复用本项目焚化区原创 geometry helper；当前完整 helper 副本也随本次发布。外部 Blender、字体、PBR 图像等依赖按脚本中的实际输入准备，未随 Git 打包。不要为发布重新运行渲染或安装脚本。

恢复次序为 setup → surfaces/models → 获授权后制作图标 → 独立导入宿主 → 主项目安装。相机现用 V2 网格及 V1 材质，V1 其他三件物品和共用材质仍保留。`integrate_gameplay.py` 是初次数据接入配方，需要 camera V2 保存回执和地牢 catalog；生产数据已在 Content/ColdSteelData，不要将旧接入脚本用于覆盖用户后来修改的表。

占格、回收价及每池概率见 `SourceAssets/StaffLivingCollectibles20261016/GAMEPLAY-INTEGRATION.txt`。排水两个 ID 和复用池见 `SourceAssets/DrainageToolboxLoot20261016/DELIVERY.txt`。不重置已生成、已取空或保存的容器；配置新进程生效，本次不自动重启。

### 火甲

保留 `Tools/Fluids/author_flame_armor_v2.py` 的共用函数；运行 `author_flame_armor_fireball_v3.py` 产生火球衍生 Weapon/Arrow，再由 `author_flame_armor_ring_v4.py` 读取 **FireRingV5/FireRing.hlsl** 制作足环，最后应用 `SourceAssets/FlameArmor20261017/RingAndWeaponOnly/install.py` 移除上身发射器。

最终仍使用 `/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmor{Body,Weapon,Arrow}V2` 和 `TorchV2/FireRingV4` 资源路径；旧名字不表示旧效果。SourceAssets/FireRingV4 作者旧稿已归档，Content 的 FireRingV4 不能移走。依赖既有火球、火把/Niagara 母版、插件和材质资源，本次不再分发这些二进制。

### 冰甲

先保留 CrystalV2 的 Chip、ChipMaterial、Condensation 及其制作输入。`author_ice_armor_v2.py` 仍可制作共用碎屑；`build_ice_armor_v2.py` 提供 V5/V6 使用的网格/骨架导入函数。这两个工具不是废案，重制后不得把旧 V2 外观重新接回。

第一人称：`author_ice_helmet_v5.py` → `import_ice_helmet_v5.py`，路径 HelmetV5，连续厚截面和真实中央孔洞。第三人称：`author_ice_armor_v6.py` → `import_ice_armor_v6.py`，路径 ThirdPersonV6，22 个蒙皮变体、4 个运行组件，复用 Jason 原生骨架及实际衣物包络。原生身体、头部和服装密集导出只在本机保留。

`restore_ice_armor_icon.py` 使用本地 `SourceAssets/IceArmor20261017/ice_armor_cold_steel.png` 恢复冷钢图标；图源未随源码发布。完整资源、模型、参考图和历史回执的路径/散列见 `local-inputs.json`。导入时有 PIE 或未保存资源不能覆盖；使用既有桥批次或适用后台 commandlet，脚本存在不等于已导入。

### 许可与本地依赖

本提交仅包含项目原创 C++、Python/PowerShell/HLSL 配方、数据、文字和散列清单，不包含 `.uasset`、`.umap`、Blender/FBX/GLB、贴图、音频、字体、插件或引擎。第三方 Jason/骨架/动作、既有火焰与冰纹理须由使用者在本机具有相应授权。允许商用不等于允许原始资源再分发。公开的资源路径和散列不授予素材许可。

## 废案归档

`archive-plan.json` 为逐文件原路径、目标路径、大小、SHA-256、原因和保留替代物；`archive-receipt.json` 为实际完成记录。125 份旧导入/外观稿、Before 快照和任务临时文件移入 `trash/living-armor-retired-20261018/`，无删除。移动前验证绝对路径及文件散列，移动后重新读回；脚本遇到两个位置同时有文件会停止，保留两份。

需要恢复历史稿时，先阅读清单，再显式运行 `py -3 Tools/Publication/archive_living_armor_20261018.py restore`。恢复只移动原文件，不修改当前运行引用或重新导入旧资产。不要再次执行已归档的一次性 integrate 脚本覆盖现行代码。

## 已有证据与未完成范围

- 最新冰甲/持锤网络修正：2026-10-18 00:54 的 FPSGAMEEditor 与 FPSGAME 构建返回 0；00:55 离线权威/副本夹具 20 项、0 失败；资源记录为 29 引用无缺失。原始记录保留于 `SourceAssets/WarhammerCastArm20261018/NetworkAudit/`。
- 火甲：2026-10-17 的 21 项权威检查及限定双进程 UDP/NullRHI，80ms 延迟与 2% 丢包。迟相关性、单次扣费/伤害、客人修炼和到期清理的结果见 `Docs/Skills/FlameArmor20261016/network-audit-20261017.txt`。最后热成像代理偏移修正仅完成构建，未重复该通信检查。
- 第一人称冰头盔与持锤方向获用户认可；这不等于之后网络字段修改已做双端视觉验收。冰甲真实主客机、重连、跨图、专用服务器、超过两端、互联网以及生活区双端取物仍没有本批验收结果。
- 生产铲独立铲面火焰尚未制作，脚下火环存在。原武器覆盖清单是当时 25 件加空手，不能用它宣称所有后来新增武器均逐件验收。
- 所有对端需使用包含新增反射/复制字段的同版构建。旧源码/历史构建回执不能证明旧进程已更新。
- 本次整理只进行用户要求的仓库/推送检查及归档完整性核对，没有重跑上述检查。不会把离线夹具结果写成真实联机通过。

## SKILL 沉淀

本机维护源和仓库对应 references 同步增加：第三人称施法臂基底、冰头盔/冰甲表现及网络结算、武器火焰与连续足环、生活区收集池、升级奖励镜像覆盖。各 SKILL.md 只追加对应问题入口，未覆盖其他未提交的技能修订。
