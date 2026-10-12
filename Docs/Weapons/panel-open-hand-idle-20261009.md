# 打开面板保留装备手部待机（2026-10-09）

用户要求：逐类排查打开背包后手部待机消失的问题，打开任何面板都保留已装备的手部与武器。

## 源码定位与调整

| 家族 | 实际显示入口 | 本次处理 |
| --- | --- | --- |
| 符文剑及共用剑类改造 | `RuneSwordComponent` | 拆分 `CanPresent` / `CanUse`，装备刷新与每帧显示走前者；输入被面板占用时取消动作，继续采样 Idle，并恢复普通持剑位置。 |
| 弓及弓体改造 | `BowWeaponComponent` | 弓体、弦、箭和手臂按展示条件显示；面板中只推进待机与姿态衔接时钟。取消拉弓后保留 Ready 与已搭箭，关闭面板不重播装备。 |
| 斧、镐、铲及共用采集工具 | `ProductionToolComponent` / `ProductionToolMotion` | 展示条件与采集条件分开；停止挥击和采集接触后继续更新手部待机。 |
| 副手法书 | `SpellbookComponent::OwnsLeftHand` | 面板输入锁不再释放左手展示所有权；法书和握持手臂继续显示。快速近战单独保留输入锁判断。 |
| 主手步枪、霰弹枪、单手手枪与左轮 | `FPSGAMECharacterProfile` | 已按真实装备与翻越状态显示，没有将面板输入锁作为隐藏条件，保留该路径。 |
| 双持手枪、独立副手枪 | `PistolDualWieldComponent::Advance/UpdateHand` | 输入不可用时取消输入，仍更新各手显示与姿态，保留该路径。 |
| 法杖 | `StaffWeaponComponent` | 面板取消攻击后仍采样装备手臂，保留当前法杖与待机资产。 |
| 空手／仅副手法书时的右手 | `FPSUnarmedIdleComponent` | 展示条件不依赖面板输入锁，保留呼吸待机路径。 |

覆盖共享背包／属性／仓库界面，以及枪匠、强化、出征、木工、天气、建造抽屉和暂停菜单的输入接管。建造抽屉打开时显示持物；关闭抽屉进入放置操作仍保留原有收起规则。死亡、卸装、翻越、实际动作占手及资源尚未加载不属于面板待机。

`SuspendWeaponForMenu` 补齐采集与快速近战中断；原有 `FireReleased` 已负责剑、法杖与弓的取消，继续沿用其不发射箭矢的语义。法书推击的动作时钟另外检查 `BlocksOngoingActions`，不能通过保留法书显示而继续打击。

暂停菜单继续遵守游戏暂停：当前手部画面保留，动画时钟随世界暂停；普通不暂停的面板继续播放待机。

## 交付边界

本次完成源码排查与修改，不替换手模、武器资产或动画。`Tools/Build/Build-Editor.ps1` 后台 Editor 构建成功，普通 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘；构建日志为 `Saved/BuildEditor/build-20261009-225250.log`（`Result: Succeeded`）。未启动编辑器、PIE、截图、渲染或游戏回归；运行表现由用户测试。
