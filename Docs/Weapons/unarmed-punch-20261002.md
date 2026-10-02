# 空手左右交替挥拳 · 2026-10-02

空手主副槽都没有装备、且没有生产工具时，左键发动普通挥拳。第一次右拳，之后左、右交替；按住左键连续出拳，每次完成收拳才开始下一拳。真实松手只停止续拳，当前一拳继续完成；切武器、菜单、优先动作、死亡、翻越、滑铲或闪避会取消未完成攻击。取消不退还已经消费的体力。普通挥拳不要求学习快速进战，也不消费或训练该技能。

## 作者动作与运行采样

复用法杖 `StaffQuickCombat20261001` 左拳中间六个完整肩、肘、腕姿态，接触为 `0.1716666667s`、全长 `0.5516666667s`。右拳通过相机 Y 镜像、左右原生掌语义迁移，并按右侧原生骨长与肘铰链重建。起止来自当前 `UnarmedLocomotion20261001` 双闭拳待机；四指及外侧拇指保持认可的 V7 拳形，腕关节、蒙皮、绑定和辅助骨关系保留。

运行直接消费 `UnarmedAuthoredPunch20261002.h` 的两个完整局部姿态表；无需导入 UE AnimSequence。第一段混合本次进入的真实局部姿态，恢复段从 `0.2916666667s` 交回当帧的呼吸/走跑基础。下臂先插值肘 Flex 与前臂 Roll 标量，再组装原生铰链四元数，随后全链 FK。另一拳仍消费当前待机和步态；衣袖、手套继续跟随同一视模。

`UFPSUnarmedIdleComponent` 拥有空手判定、左右顺序及按住续拳。`UFPSQuickCombatComponent::UnarmedPunch` 共用接触、音效、镜头、钝器伤害及命中反馈，使用独立普通拳击规则；角色相机更新前只推进一次动作时钟。跨越命中帧时先固定到精确接触时间，刷新出拳手的 `middle_01_l/r` 指节探针，再进行一次共享单目标接触查询。身体表现发布实际左右侧及同一动作进度。

## 体力与伤害

- `Content/ColdSteelData/stamina.json` 的 `punchCost=8` 控制基础每拳消耗，剑的 `meleeCost=15` 保持原值。
- 在攻击成功开始时通过 `SpendStamina` 扣一次，挥空照扣；不足时提示并停止续拳。装备的近战体力系数及现有临时近战体力系数作用在同一份拳击消耗上。
- HUD 的空手可攻击次数使用实际拳击费用，恢复延迟沿用现有体力系统。
- 基础拳伤害为 `8 + 当前物理攻击 atk`，扫掠从实际指节向瞄准方向延伸 `90cm`、半径 `14cm`，沿用低位小手怪接触补充、玻璃及钝器削韧处理。拳击不带枪械弹药、法杖符文或持械专精快战伤害。
- 联机使用空物品声明加保留语义 `AttackMeta=0x08`。服务器要求当前主副槽及工具均空，并按影子档案复算同一拳伤害；不借用快速进战的 `0x80` 面板结算。

## 已保存制作源

`SourceAssets/UnarmedPunch20261002/` 已保存 `author_punch.py`、完整 `full-pose.json`、作者参数、运行头以及可编辑 `Unarmed_V7_AlternatingPunch_20261002.blend`。Blender 源包含右拳和左拳两个 take，120 Hz 曲线及精确作者时刻；实际源保存记录见 `editable-source.json`。

构建产物状态单独记录于该目录的 `integration-completion.json`。本次未启动 UE、运行游戏、渲染或进行测试/验收，效果由用户自行测试。

初次交付构建记录：`FPSGAME` Win64 Development 已后台链接成功，`Binaries/Win64/FPSGAME.exe` 已保存。Editor 复用包含当前原生改动的成功共享构建，普通 `UnrealEditor-FPSGAME.dll` 已于 `2026-10-02 22:07:01 +08:00` 保存。对应成功日志保存于 `Saved/BuildUnarmedPunch20261002/shared-editor-base.log`、`shared-editor-final.log`；当时 UE 随后被重新打开，本任务没有关闭或重启它；该句记录初次交付时点。制作源、两个可编辑 take 和原生运行产物均已落盘，未做运行或视觉验收。

必要构建修正：为原生空手组件添加角色友元，以沿用现有退出冲刺入口；`TransitLoadingSubsystem.cpp` 的现有地址筛选使用了不存在的单参数 `FString::FindChar` 重载，改为等义的 `!Contains(":")`，保持过滤含冒号地址的行为。没有改动地址筛选范围或联机连接逻辑。

后续用户关闭 UE 后，0.25 秒撞门调整的 Editor／Game 正式后台构建已完成并包含当前空手拳击。最新日志为 `Saved/BuildEditor/build-20261002-234440.log` 与 `Saved/DoorPushHold250ms20261002/FPSGAME-20261002-234533.log`；源码发布边界及生成表恢复见 [本轮整理发布](weapon-arms-publication-20261003.md)。未运行游戏或追加测试。
