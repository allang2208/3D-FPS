# 木工工作台优化开发记录

日期：2026-10-12。对应[优化方案](woodworking-overhaul-plan-20261012.md)。用户已授权开发，并明确正式产出优先接弓臂。

最新状态（2026-10-12 22:02，北京时间）：**编译阻塞已解除，木工版本源码、配置、图标及对应 Game/Editor 产物已落盘。** 本轮 Game 增量构建成功；Editor 使用已包含这版木工源码的既有成功链接产物。详细收尾见文末，未运行游戏或测试。

## 本轮已落盘

### 面板

- 新项目页：模式选择、项目目录、等比例木料/目标预览、加工步骤、完成条件、制作材料和固定确认区。
- 宽屏三栏；紧凑窗口目录与上下详情；窄窗项目列表与详情切换。
- 实景页固定开始/完成与急停，次级操作换行，移除原横向滚动操作条。
- 成功/失败切换独立复盘区域，显示实际工件、质量与分项失败原因。准备阶段不显示旧版起始 67.5 分。
- 静态材料和报价由档案变更事件标脏；文字相同不重复 SetText。布局保留共享冷钢主题。

### 操控与判定

- 拖动记录木板局部抓取点，单次输入按有界步长完整处理，不丢弃超过旧上限的位移；松手后没有积压进料。
- 被刀口阻挡的方向重新锚定，避免退料后突然补上之前积压的横向位移。
- 横移和旋转扫掠依据剩余木料，已经删除的废料不再形成隐形阻挡。
- 相机按木板、锯片与上下/侧边 UI 净区域取景；窗口变化和复位时重新拟合，普通拖动不追镜。
- 木板世界比例独立配置为 0.22cm/遮罩格；刀口接触长度由同一设备几何推导，不再通过改刀口参数缩放整块木板。

### 实景反馈

- 真实切削采样驱动世界空间木屑，最多 32 片，短寿命回收。
- 纯废料连通块剥离时显示一次有界分离动画，脱离体仅参与表现，不重复参与碰撞、切割或评分。
- 复盘使用红色缺损和金色残余废料覆盖，保留原有目标轮廓。
- 新增程序合成的空载电机/接触切削声：单声部、有界缓冲、按真实电机和接触状态启停。现有可选授权 CuttingSound 软引用仍保留。
- 合成声不是实录台锯音；废料是短暂显示动画，不是独立刚体物理。本轮未替换 V4 桌体或原有木板材质资产。

### 图样与模式

| 图样 | 自由练习 | 挑战/制作时限 | 清除要求 | 最大损伤 |
| --- | --- | --- | --- | --- |
| 直边毛坯 · 入门 | 不限时，无消耗/产出 | 120 秒（挑战） | 95% | 10% |
| 弓臂毛坯 | 不限时，无消耗/产出 | 150 秒 | 97% | 8% |
| 法杖木芯毛坯 | 不限时，无消耗/产出 | 120 秒（挑战） | 97.5% | 6% |

撤销沿用 3 次，不返还挑战/制作时间。自由练习评分排除速度权重，限时模式保留速度小权重。以上是本轮初始设计值，尚未进行游戏难度测试。

## 弓臂生产和实际用途

1. E 打开木工工作台 → 弓臂毛坯 → 正式制作。
2. 配方 `woodwork_bow_limb`：**2 木材 → 1 木制弓臂**。材料范围为背包、材料隔层与主仓库，随现有 Craft 事务。
3. 开始前判断材料和容量；达标后领取才原子扣料并发放。失败、取消和退出不扣材料；领取成功后不能重复领取。
4. 新物品 `woodworked_bow_limb`：1×3 格、最多堆叠 20。使用由实际图样轮廓生成的透明木纹图标；库存与存档复用现有通用物品流程。
5. 弓改造台 → 弓体 → **手制磐木弓体**（`woodcrafted_heavy`）：使用 2 件木制弓臂。
6. 该选项复用已有磐木弓体的 ElasticV15 Heavy 模型、变形参数和全部现有属性。工艺评分不额外增加伤害或装备稀有度。
7. 换下手制磐木弓体时返还 2 件弓臂至背包。扣除、返还、武器 `gunsmith_parts` 变更和保存使用同一快照事务；缺材料、背包放不下返件或保存失败均不提交。
8. 现有原装/免费改造选项保留原规则。本轮新建的是独立手制选项，没有把既有磐木弓体改成收费。

木工配方放在 `woodworking-recipes.json` 的专用目录，仅用于 Find/木工领取，不出现在普通工作台的直接制造列表，避免绕过加工直接制造弓臂。

尚未领取的工件仍不持久化；退出提示会清除结果。未新增预付、退款任务存档或品质属性迁移。

## 修改范围

- 木工 UI：`ColdSteelWoodworkingWidget.*`，新增 `WoodworkingPanel.inl`。
- 木工玩法与世界表现：`WoodworkingSystem.*`、`WoodworkingMask.*`、`WoodworkingWorldView.*`、`WoodworkingSaw.h`。
- 专用制作目录：`CraftingSystem.*`、`woodworking-recipes.json`。
- 弓臂装配：`GunsmithSystem.*`、`BowGunsmith.cpp`、`bow-gunsmith.json`。
- 内容：`woodworking.json`、`items.json` 新增弓臂条目、`Icons/woodworked_bow_limb.png`。
- 图标源与来源：`SourceAssets/WoodworkingOverhaul20261012/create_limb_icon.py`、`provenance.json`。程序制作，不使用外部参考图或受限素材。
- 修改前文件：`Saved/WoodworkingOverhaul20261012/Before`。不清理、回退、暂存或提交并行修改。

## 首轮构建与交付边界（历史阻塞记录）

本轮只执行必要后台构建，没有启动 UE、游戏、PIE、运行测试、截图或验收渲染。开发期间检测到用户已有 UE 编辑器进程，保持运行，未关闭或热补丁修改其已加载实例。

本轮 Game 构建退出码 1，`Result: Failed (OtherCompilationError)`，耗时 297.03 秒，记录：`Saved/WoodworkingOverhaul20261012/Game-build.log`。木工 Widget、System、Mask、WorldView、CraftingSystem、BowGunsmith 和 GunsmithSystem 均有成功完成编译动作的记录，没有本轮修改文件的编译错误；全项目链接未完成，没有交付新版 EXE。

首轮失败包含 `FPSBlizzardZone.h` 反射类声明、`FPSDodgeMovement.cpp` const 调用，以及当时尚未同步的近战突进接口。等待已有构建释放后读取了与本轮产物相关的后续构建输出：

- `Saved/BuildEditor/shotgun-models-wheel-final.log`：Editor 目标失败，木工相关文件已编译，剩余错误为 `FPSDodgeMovement.cpp:44/69` 在 const 方法中调用非 const `GetRootMotionSourceByID`。
- `Saved/BuildEditor/multiplayer-actions-20261012.log`：Game 目标失败；除上述两处外，`FPSCharacterMovementComponent.cpp:57/76/154` 访问 `AFPSGAMECharacter` 私有滑铲成员报错。

这些并行修改仍在变化，收尾时已有后续 Editor 构建运行。本轮不抢占构建锁、不联系其他对话，也不改写相关移动/技能源文件。上述后续日志不是本轮发起的新构建，不作为本轮成功产物凭据。**当前交付为源码、配置和图标落盘；新版 Game/Editor 基础产物尚未由本轮成功构建交付，需先解除项目级编译阻塞。**

源码落盘、单文件编译、Game 可执行文件、Editor 基础 DLL 和实际游戏体验分别记录。当前不能以源码已写好或某个源文件已编译，宣称新版本已经在正在运行的编辑器中生效。

## 编译阻塞解除与落盘（2026-10-12 22:02）

用户要求继续处理编译阻塞，保留并行修改，不打开 UE、不运行测试。恢复工作时，现有源码已包含闪避只读查询的兼容修正，以及移动组件/保存移动对角色滑铲状态的友元访问；相关近战接口也已同步。本轮无需再次修改这些源码。

等待已有构建释放后，本轮执行 `FPSGAME Win64 Development` 后台增量构建，退出码 **0**，`Result: Succeeded`，4 个动作、19.56 秒，完成 EXE 链接和目标元数据写入。日志：[Game-final.log](../../Saved/WoodworkingOverhaul20261012/Game-final.log)，执行结果：[Game-final-result.json](../../Saved/WoodworkingOverhaul20261012/Game-final-result.json)。编译保留一条冶炼 `Station` 变量的既有 C4701 警告，不影响成功结果；本轮未扩展修改冶炼源码。

| 产物 | 当前落盘时间（北京时间） | 大小 | 构建依据 |
| --- | --- | --- | --- |
| `Binaries/Win64/FPSGAME.exe` | 2026-10-12 22:02:30 | 360,731,648 字节 | 本轮 Game 成功链接 |
| `Binaries/Win64/UnrealEditor-FPSGAME.dll` | 2026-10-12 21:51:11 | 28,373,504 字节 | 既有 `shotgun-models-wheel-final.log` 成功链接；随后 `build-20261012-215119.log` 为 Succeeded / up to date |

木工任务涉及的原生文件均早于上述 Editor DLL 落盘时间。Editor 产物来自已有共享工作区的成功构建，本轮未重复启动 Editor 构建或覆盖已加载 DLL；不把它记成本轮重新链接。当前已运行的编辑器保持不动，未打开、关闭、重启或热补丁，也未运行游戏、PIE、测试、截图或验收。

最新文件大小、时间、SHA-256 与木工文件清单记在 [delivery.json](../../Saved/WoodworkingOverhaul20261012/delivery.json)；旧失败状态保存在 `delivery-blocked.json`，首轮失败日志继续保留。本轮只新增构建日志/回执并更新交付记录，未回退、暂存、提交或推送其他并行修改。实际面板、手感与正式制作体验仍由用户测试。
