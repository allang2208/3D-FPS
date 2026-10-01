# G18 全自动手枪接入

制作开始于 2026-09-29，2026-09-30 后台导入落盘。项目为 `D:/FPS3D/FPSGAME`，物品 ID 为 `ue_g18`。

## 交付状态

- 已制作可编辑 Blender 源、FBX、PBR 贴图、音频和目录图标。
- 已通过离屏 Python commandlet 导入、保存 3 套骨架主体、59 段动作和 10 个配件网格，以及材质、音频和图标；记录为 `SourceAssets/G18Integration20260929/import_receipt.json`，终态 `imported_and_saved`。
- 物品、枪匠和模块化手部装备目录已写入实际 JSON；新增目录已加入 Cook 配置。
- G18 接入源码已落盘，先前构建阻塞已消除。2026-09-30 的正常后台构建返回 `Result: Succeeded`／`Target is up to date`，当前游戏模块已是最新。
- 扩容弹匣壳体和全息／全景红点底座已根据用户反馈修复、重导入保存；对应图标与瞄具光学材质同步，详见 [配件修复](g18-attachment-repair-20260930.md)。
- 镭射和手电已统一前移 25 mm，修整导轨接触面并同步发射插座及图标，已后台导入保存，详见 [战术配件挂位](g18-tactical-fit-20260930.md)。
- 未打开 UE 编辑器，未运行 PIE、游戏、自测、回归、试听或视觉验收。手指接触、附件观感、动画与实机手感由用户测试；制作参数与保存记录不等于验收结果。

## 游戏定义

| 项目 | 当前配置 |
| --- | --- |
| 开火方式 | 全自动，按住持续射击 |
| 弹药 | `ammo_9`，9 mm |
| 弹匣 | 原厂 17 发；扩容 33 发 |
| 基础间隔 | 0.05 s，1200 发/分钟 |
| 稳控扳机 | 间隔 ×1.2；后坐 ×0.9；仍为全自动 |
| 基础伤害 | 18，继续参与现有伤害、技能、附魔和衰减计算 |
| 基础弹速／有效距离 | 375 m/s／40 m |
| 普通／空仓换弹 | 1.75 s／2.25 s，读取实际动作时长 |
| 扩容代价 | 换弹 ×1.1，ADS 耗时增加 5% |
| 物品形态 | 单手手枪，背包占用 3×2；支持双持与法杖副手 |
| 获取入口 | 现有初始军械领取流程新增一次性 G18 与 170 发 9 mm 弹药；标记保存在原领取集合 |

这些是游戏平衡参数。物品短文参考 [GLOCK Full Auto](https://eu.glock.com/en/Technology/Full-Auto)，不是对实枪操作的说明。

## 主体、手臂和机械

用户提供 `C:/Users/allan/Downloads/g18.zip`。原 FBX 分为枪体、弹匣和弹头，共 13,298 个三角面；保留原 UV、分件、权重和 4K PBR。源包没有动画。

枪械被注册到既有手枪骨架的枪根空间，按原模型部件建立套筒、枪管、弹匣、扳机、选择器和弹头身份。G18 选择器属于套筒侧部，因此随套筒移动。枪口、抛壳口和前后瞄具标记使用 G18 模型测量位置。发射周期为 0.05 s：套筒后坐行程 33 mm，枪管短退／倾斜，末发保持套筒后定。

单持和左右双持均安装当前 `BarePalmV7` 原生手臂，保持解剖学左右和各骨骼绑定。沿既有 M1911 动作意图重映射 G18 机械，调整整手握位与弹匣接触，不缩放整套手臂。模块化衣袖、手套继续使用 M1911／M1911_r／M1911_l 的衣物骨架配置，新主体自身为裸手默认。

片段覆盖待机、ADS、发射、末发、空仓、拔枪、普通与空仓换弹、检视、冲刺以及单持／双持近战分支。单持换弹沿用当前已缩尾动作；双持源动作整体重定时为同样的 1.75／2.25 s，运行时再乘既有双持 1.33 惩罚及角色／配件倍率。

换弹源时间接触点为退匣 0.3167 s、插入 1.05 s、压实 1.0667 s、空仓套筒释放 1.6 s；结算继续使用现有换弹事务、动作时钟与中断恢复阶段。

## 运行接入

- `G18WeaponAssets.h` 集中管理独立网格、动作、附件、声音和湿润表路径。
- `bUseM1911` 作为现有可换弹匣手枪的表现分支复用，G18 的实际身份、资源与扳机行为由 `ue_g18` 单独选择。
- 单持绕过半自动触发门；双持和副手使用各手自己的弹药、按住状态、发射截止时间与换弹。双持每帧最多补处理四发过期调度，避免无限追赶。
- 沿用装备状态的开火打断、切枪输入交接、菜单／翻越／施法门、空仓换弹、取消音效队列和存档所有权。其余半自动枪不改为连射。
- 发射使用现有弹道、准星散布、枪口遮挡、伤害、抛壳、火光／烟气、后坐和听觉事件。配件出口存在 `Muzzle` 插座时读取实际出口。
- 四个普通和四个消音声变体避免紧邻重复；单持及双持 G18 走角色的有限枪声池。音效是基于项目 CC0 瞬态的游戏音效设计，未试听，不声称 G18 实枪录音。

## 枪匠、显示和材质

保留通用改装选项 ID 与事务。新增 G18 自己的全息、全景红点、普通消音器、战术消音器、制退器、激光、手电、扩容弹匣和贴合握把覆盖层。短／长枪管与稳控扳机为数值改造。瞄具的底座改为 G18 平面承托；主体与光学部件沿用现有手枪级尺寸。战术件挂位取 G18 导轨表面；弹匣保留上端插接口，沿原弹匣方向向下延伸。

枪体保留原始 BaseColor／Metallic／Roughness／DirectX Normal。附件主体按本枪深色钢材建立私有材料；玻璃、分划、橡胶、聚合物和内腔保留对应源材料。新增主体与私有金属材料加入 `DA_G18_WetMaterials`；复用材料继续由现有雨水目录管理。

当前持枪、枪匠、背包独立预览、动态图标、掉落／拾取共用既有装配入口。静态目录图和各选项／左栏类别图也已落盘，目录图由实际 G18 几何离线制作，没有用其他枪的图片代替。

2026-09-30 收尾已更新三款通用枪口的 G18 转接段与出口挂点，并将装备栏基础图、21 张改装选项图和 7 张分类图升级为 1024 透明贴图，纠正原厂／数值选项使用整枪图的情况。钛金制退器按用户要求排除。当前制作来源和后台保存记录见 [枪口与图标收尾](g18-muzzle-and-icons-20260930.md)。

## 路径

| 用途 | 路径 |
| --- | --- |
| UE 资产根 | `/Game/Weapons/G18/Integrated20260929` |
| 单持主体 | `Single/SK_G18_Manny` |
| 双持主体 | `Dual/r/SK_Dual_G18_r`、`Dual/l/SK_Dual_G18_l` |
| 制作源 | `SourceAssets/G18Integration20260929` |
| 单持可编辑源 | `Single/G18_single_Editable.blend` |
| 左右手可编辑源 | `Dual/r/G18_r_Editable.blend`、`Dual/l/G18_l_Editable.blend` |
| 配件可编辑源 | `Attachments/SM_G18_*_Editable.blend` |
| 物品目录 | `Content/ColdSteelData/items.json` |
| 枪匠目录 | `Content/ColdSteelData/gunsmith.json` |
| 衣物适配表 | `Content/ColdSteelData/modular_outfits.json` |
| 图标 | `Content/ColdSteelData/Icons/ue_g18.png`、`AttachmentIcons20260913/ue_g18_*.png` |

## 构建

使用正常 `FPSGAMEEditor Win64 Development` 目标，保留依赖图重建；不使用 Live Coding 或带临时后缀的 DLL。构建过程保留现场，没有启动或关闭其他编辑器，没有向其他对话发送消息。

首次构建完成 G18 相关 C++ 编译，在最终链接时遇到树木采集模块的 `StumpHealthRatio`、`TreeSaplingOffset`、`TreeStumpOffset` 缺失符号。当前源码已有这些实现，同时存在并行写入／构建；未修改该系统。首次日志保留为 `build_first_stdout.log`／`build_first_ubt.log`。

修正本次三个 C++ 文件的首头文件顺序后，再次构建曾被 `Source/FPSGAME/Weapons/FPSMeleeLightningComponent.cpp` 的以下接口问题阻断：

- 第 141 行调用 `AFPSLightningArc::InitializeArc` 使用 6 个参数，当前声明接收 5 个。
- 第 149 行使用不存在的 `FColdSteelItem::Id`。
- 第 164／166 行引用当前工具／剑组件没有声明的 `GetEnchantmentBladeFrame`。
- 第 169／177 行引用雷电类尚无声明的 `FollowBlade`／`InitializeBladeArc`。

该次错误日志保留为 `SourceAssets/G18Integration20260929/build_blocked_stdout.log` 和 `build_blocked_ubt.log`，退出码 6。

用户要求继续完成后，当前雷电与近战接口已落盘。本次仅将 `RefreshEquipment` 中错误的 `Item->Id` 修正为物品实例字段 `Item->InstanceId`，其余实现保留。修改前文本保存在 `CodeBefore/FPSMeleeLightningComponent-before-build-fix.cpp`。

修正字段后，构建入口一度检测到运行中的编辑器，按用户规则停止提交，没有结束该进程。随后用户反馈配件几何问题，本任务继续完成三件配件修复和后台保存。

编辑器退出后重新提交正常后台构建，`build_stdout.log` 返回 `Target is up to date`、`Result: Succeeded`、`G18_BUILD_COMPLETE`，退出码 0。当前 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 的写入时间为 2026-09-30 01:22:23（本地时间），目标无待构建动作。本次未重启编辑器，未运行游戏测试。
