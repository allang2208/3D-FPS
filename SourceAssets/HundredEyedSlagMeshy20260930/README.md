# 百目炉渣 — Meshy 制作候选 V2

2026-09-30。目标宿主为 D:/FPS3D/FPSGAME。用户要求先出三视图，采用 Meshy 管线构建；随后否决 V1 的恐怖感和扭曲程度，要求重新生成参考图。

## 当前交付

当前使用 **SmokeVisibilityFixV21**：烟雾改用百目炉渣专属持续浓烟材质，纠正 UE 5.8 发射插值字段，CPU 发射器改为动态包围盒；运行烟迹边界按 Niagara 组件坐标换算。保持 50% 扩散扩大、8 秒浓烟保留和 1.5 秒渐散、世界空间上浮、每秒 8 粒及雾内目盲。新材质与 Niagara 已保存，Editor 玩法模块已常规构建；未在游戏中测试。详见 `Docs/Monsters/hundred-eyed-slag-smoke-visibility-v21-20261002.md`。

2026-10-02 覆盖修订：烟雾扩散幅度、单团线性尺寸和浓烟目盲核心半径同步乘以 1.5，默认 Radius 输入 260 → 390 cm；同一 Niagara 资产通过运行参数驱动，8 秒保留、1.5 秒渐散与每秒 8 粒沿用。Editor 玩法模块常规构建完成，未运行测试。

上一轮 **BodySmokeV20**：黑烟从背壳和两侧肩背随骨骼运动的三个位置产生，出生位置与漂移在世界空间固定，离体后缓慢升空并翻卷扩散。烟团保留 8 秒，再用 1.5 秒渐散，最长总寿命 9.5 秒；每秒 8 粒，约最多 76 粒。目盲沿用 V19 的浓烟内糊屏和离开即清除，三种攻击、伤害、竖劈眩晕、模型、动画和布娃娃保持现有配置。新 Niagara 资产已保存，Editor 玩法模块常规构建完成，未运行测试。详见 `Docs/Monsters/hundred-eyed-slag-body-smoke-v20-20261002.md`。

上一轮 **WorldSmokeV19**：尾烟改为世界空间，保存出生位置与漂移，旧烟自行上浮扩散、3.6 秒消散，怪物移动转向只影响新发射。目盲仅在烟迹的浓烟核心内触发，离开立即解除；取消雾外看向烟球的屏幕压黑，改为雾内全屏失焦、轻微扭曲与烟灰污膜。两项新资产已通过无界面 commandlet 保存，Editor 玩法模块常规构建成功。竖劈 2 秒眩晕、激光倍率 0.8、横扫倍率 1.25、模型、动画与布娃娃沿用；未运行测试。详见 `Docs/Monsters/hundred-eyed-slag-world-smoke-v19-20261002.md`。以下保留历次制作记录，V19 的“离开即清除”覆盖旧目盲延时规则。

**BlackMistFixV18**：解决黑烟系统和视野材质未保存导致的缺失，V17 三项资产已通过后台 commandlet 实际保存；原生组件补充缺失模板首次激活解析。竖劈实际命中附加 **2 秒眩晕**，每次攻击同一玩家只触发一次，复用既有免疫、输入锁、移动封锁及恢复流程。Editor 玩法模块常规构建成功，目标已是最新；未运行游戏测试。详见 `Docs/Monsters/hundred-eyed-slag-black-mist-fix-v18-20261001.md`。

V17 黑雾已随 V18 完成落盘与接入：背部半径 2.6 米黑色翻卷浓雾，进入后持续刷新 2 秒目盲，离开后保留 2 秒；视野在 0.8–2.5 米间渐暗。激光倍率翻倍，默认每跳 28、完整命中基础合计 140；普通横扫倍率 1.25，默认基础 52.5。详见 `Docs/Monsters/hundred-eyed-slag-black-mist-v17-20261001.md`。

**RagdollGroundV16** 已包含在当前基础 DLL：死亡下沉定位到带 100 倍单位缩放的 Armature 缺少物理根节点，以及死亡姿势/速度交接。独立 PA 已实际保存，17 刚体、16 约束，源码补充即时姿势同步、非碰撞容器根和一致速度交接；正式网格、蒙皮、材质及攻击动画沿用。未运行游戏测试。详见 `Docs/Monsters/hundred-eyed-slag-ragdoll-ground-v16-20261001.md`。以下保留历次制作记录。

历史阶段 **LaserSustainV15**：激光存续期间每 **0.13 秒**造成一次魔法伤害，默认 **0.65 秒共 5 次、每次基础 14、完整命中基础合计 70**（实际扣血经过原魔防与状态公式）。固定攻击时钟、每跳去重、当前遮挡过滤、打断／死亡／结束后停止伤害；V14 贴眼凝聚效果沿用，仍只有横扫／下劈／激光。Editor 玩法模块基础 DLL 已常规构建落盘，未运行测试。详见 `Docs/Monsters/hundred-eyed-slag-laser-sustain-v15-20261001.md`。以下保留制作历史。

历史阶段 **EyeChargeV14**，普通横扫实际判定加长到 **320 cm**、查询半径为 **90 cm**，约 **250 cm** 即开始前摇；下劈维持 300 cm。眼部凝聚复用已有 MayuOrbs 红色能量材质、旋涡贴图与 ElectricMagic 蓄能粒子结构，改成贴眼核心、向内光丝和缩圈，取消悬浮汇聚球。六个新资产已后台保存，Editor 玩法模块基础 DLL 已常规构建；激光仍为待机、眼区轻微颤动、至少 1.5 秒蓄能，无提前量，仅横扫／下劈／激光三种攻击。未测试，由用户试玩。详见 `Docs/Monsters/hundred-eyed-slag-eye-charge-v14-20261001.md`。以下保留制作历史。

历史阶段 **ThreeAttacksV13**，只有 **横扫、下劈、眼部激光** 三种攻击。横扫／下劈前方判定分别扩展到 260／300 cm；激光保持待机、只轻微颤动眼区，1.5 秒红色粒子汇聚后发射，不计算提前量。三段激光动画与曝光补偿的红色柔光材质已保存，Editor 玩法模块基础 DLL 已常规构建；未测试，由用户试玩。跃砸已取消，下面保留历史记录。详见 `Docs/Monsters/hundred-eyed-slag-three-attacks-v13-20261001.md`。

历史阶段 **ArticulationV12**：三条支撑肢重新蒙皮；跃砸加入屈膝蓄力、伸腿起跳、空中收腿、按离地高度伸展和落地压缩；聚眼激光增加大手抬起、32 个内聚粒子与至少 1.5 秒蓄力，不计算提前量。新网格（三档 LOD）和八条特殊攻击片段已保存，Editor 玩法模块基础 DLL 已常规构建；未测试，由用户试玩。横扫 V8 与下劈 V9 保留。详见 `Docs/Monsters/hundred-eyed-slag-articulation-v12-20261001.md`。下面保留历次制作记录。

历史阶段 **EyeLaserJumpV11**：冲锋替换为原地聚眼激光（魔法伤害），灰烬爆发替换为低伏、竖直跃起下砸（物理伤害）。八条动画、专用激光材质已导入保存，基础 Editor DLL 已常规构建，未测试；横扫 V8、巨臂下劈 V9 和网格/蒙皮 V8 保留。旧 ChargeV10 已退役，下面保留历史制作记录。详见 `Docs/Monsters/hundred-eyed-slag-eye-laser-jump-v11-20261001.md`。

已取消并归档的 `ChargeV10` 预测巨臂冲撞：蓄势结束按目标速度预测并锁定直线方向；巨臂前顶、三肢推进、碰撞回震与制动收势四段动画，配套灰烬/余烬、冲击环、碎屑、音效和短震屏。命中使用物攻 ×1.6，实际伤害生效后附带 110 cm 推退和 0.45 秒眩晕。基础 Editor DLL 已常规构建，四动画已导入保存；未构建独立游戏可执行文件，未运行测试。详见 `Docs/Monsters/hundred-eyed-slag-charge-v10-20261001.md`。

V8/V9 阶段运行组合为 `RampageV8` 网格、蒙皮与横扫，配合 `RampageRecoverV9` 下劈。用户已认可 V8 的横扫、下劈攻击主体，同时指出下劈 recover 大右手仍扭曲；这次仅修订下劈收势，新收势尚待用户体验。

V9 复制 V8 下劈动作，保留第 1–32 帧（0–1.033 秒）的原始动画键，重写第 33–55 帧的收势。继续使用实际 Epic Rampage `Ability_GroundSmash_End` 的回撤轨迹，将肩肘腕作为连续的固定长度臂链回到既有待机姿态；肘平面、上臂与前臂的扭转辅助骨、肘腕体积支撑同步回位。末段躯干与其他三肢支撑由源 End 连续过渡到 Idle，取消 1.55 秒时突然更换源姿态的处理。

已在原 `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSlam_R` 路径导入并保存。未重新导入横扫或网格，未重做蒙皮、LOD、材质或物理资产；攻击总时长 1.8 秒、伤害窗口 0.84–1.00 秒及 F6 百目炉渣入口沿用现有配置，无需 C++ 构建。

制作与保存记录见 `RampageRecoverV9/authoring_receipt.json`、`installation_complete.json` 和工程 `Docs/Monsters/hundred-eyed-slag-rampage-recovery-v9-20261001.md`。未启动游戏、PIE、渲染或测试，新收势效果由用户测试。

- References/V2/hundred_eyed_slag_turnaround_v2.png：新版正面、右侧、背面参考原图。
- References/V2/prompt.txt：实际 imagegen 内置工具提示词。
- Inputs/body/front.png、right.png、back.png：拆分后的 Meshy 多图输入，顺序固定为正面优先。
- 被否决的首版已移至 `trash/hundred-eyed-slag-20261002/SourceAssets/HundredEyedSlagMeshy20260930/References/RejectedV1/`，不进入构建输入。
- meshy_settings.json、meshy_pipeline.py、run_meshy.ps1：真实多图 API 的可续跑构建入口。

## 造型
焦黑焚化残留物与扭曲有机组织融合；躯干偏斜，四条不对称支撑肢，焦皮裂缝中的大小眼球和局部烧白骨质。眼球与炭化外壳形成干湿对比。设计尺度为长约 2.2 m、宽约 1.9 m、高约 1.2 m；这是造型意图，尚未转换成模型实际尺寸。遮挡部分由三维生成重建。

## Meshy 构建
采用 Meshy 7.1 多图生成、2K 几何、4K 纹理、PBR、原始高模输出，不主动减面。三张独立图也作为多视角纹理参考。任务已成功生成并完成下载，实际消耗 35 积分，余额 1793 → 1758。

用户已提供本次进程凭据并授权继续生成 V2 模型。Meshy 多图任务已提交，ID 为 01a0f0ba-cf66-72c4-8d8e-61c55a3480d8。凭据仅在生成进程内使用；后续在本机环境配置凭据后可续跑：

    .\run_meshy.ps1 build

脚本从 Process/User/Machine 环境读取凭据，不把密钥写入文件；记录请求摘要、任务 ID、状态、下载与积分，剥离预签名 URL 查询串。已有 task.json 时复用同一任务；请求已有记录但没有任务 ID 时保留现场，避免重复付费。完成后立即下载模型与贴图到 Meshy/body/downloads。

资料：https://docs.meshy.ai/en/api/multi-image-to-3d 与 https://docs.meshy.ai/en/api/pricing。

Meshy 已返回 SUCCEEDED，8 个模型与贴图文件已下载到 Meshy/body/downloads。完整清单及 SHA-256 见 Meshy/body/downloads.json；状态和积分见 production_status.json。已完成专用绑骨、16 条原创动画以及 FBX/GLB 导出，文件位于 DeliveryV1。模型、PBR、物理资产与 16 条动画已实际导入 UE 并保存。F6 怪物生成目录与独立角色类已完成接入，常规 FPSGAMEEditor 后台构建成功；下次打开项目后从 F6 → 怪物生成 → 百目炉渣生成。阶段见 production_status.json。未运行游戏或验收渲染，未测试，交由用户测试。



## 已生成的下载文件
- Meshy\body\downloads\model_urls_glb.glb (115944368 bytes)
- Meshy\body\downloads\model_urls_fbx.fbx (169294364 bytes)
- Meshy\body\downloads\model_urls_obj.obj (307704329 bytes)
- Meshy\body\downloads\model_urls_mtl.mtl (228 bytes)
- Meshy\body\downloads\texture_urls_0_base_color.png (28689275 bytes)
- Meshy\body\downloads\texture_urls_0_metallic.png (246874 bytes)
- Meshy\body\downloads\texture_urls_0_roughness.png (2637011 bytes)
- Meshy\body\downloads\texture_urls_0_normal.png (23434263 bytes)


## 专用骨架与动画交付
已保存 37 骨、33 变形骨的蒙皮母版和 16 条基础动作。可编辑 Blender、带骨模型 FBX、单独动画 FBX、PBR 贴图和动作合同位于 DeliveryV1；制作脚本位于 AuthoringV1。使用方式及未测试范围见 DeliveryV1/README.md。


## 2026-10-02 整理与源码发布

193 份退役参考、冲锋制作包、旧烟雾修订、快照／自动备份和无数据诊断尝试已归档到 `trash/hundred-eyed-slag-20261002`。原路径、目标、大小和 SHA-256 见 `Publication20261002/archive-manifest.json`。V18／V20 的历史制作源及回执可由该清单恢复；当前作者为 V21。有效模型输入、已采用动作、材质和授权供体仍在本机，不随源码上传。公开范围、恢复链和未测试状态见工程 `Docs/Monsters/hundred-eyed-slag-publication-20261002.md`。
