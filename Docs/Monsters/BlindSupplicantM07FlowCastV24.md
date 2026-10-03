# M-07 V24：联动施法与前移蓄积位置

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

用户反馈施法发射动作僵硬，蓄积火球、冰锥靠身体太近，容易穿模。本轮重新制作两段施法动作，并将火球／冰锥的蓄积中心沿怪物正前方前移 65 cm，发射采用同一位置。当前资产已后台导入并保存；未运行游戏、截图、渲染或测试，效果交由用户体验。

## 动作制作

- `MagicGather` 1.10 秒：骨盆沉身与侧向承重先行，胸廓／肩带随后转动；肘弯曲引导手掌沿外侧弧线抬起，手腕渐转成托举姿态，手指依次围拢。右臂配合托举和躯干平衡。
- `MagicRelease` 从原 0.80 秒改为 1.10 秒：轻微回蓄后，髋、胸肩、肘依次前送；掌面转向前方，手指错时展开。保留 0.30 秒的发射时刻，前送继续到 0.34 秒，随后小幅卸力；0.43–1.10 秒沿外侧弧线回收，接回当前 V20 待机。
- 使用原骨架真实肩—肘—腕构成的解剖链，继承 V23 的有符号肘轴、左右镜像掌面定义；前臂承担掌面旋转，腕部保留受限的屈伸和余量。
- 同一蓄积终态同时作为 Gather 末帧和 Release 首帧。起手／结束使用当前 `A_M07_Idle_PalmArmV20` 的姿态，避免继续回到旧 V13 待机。脚踝目标保留原位置，骨盆与腿部通过小幅屈伸传递重量；背膜仅叠加释放后的轻微跟随。
- 不改模型几何、UV、权重、参考骨架和布料。V23 慢走／追击及 42／86 cm/s 速度保持原值，待机、近战和死亡引用保留。

## 特效与发射位置

`BlindSupplicantCombatMagic.cpp` 中保留原掌骨位置函数，新增 `CastingSpellPosition()`：火球和冰锥从左手 `middle_metacarpal_l` 的世界位置沿 Actor Forward 偏移 65 cm；即时闪电保留零偏移。

偏移沿角色朝向计算，腕部翻转不再带着整个偏移量绕回身体。蓄积组件使用绝对世界变换，在骨骼最终变换回调中更新位置与朝向，同时更新冰锥 Niagara 的 PreviousPosition／CurrentPosition 和方向参数；不新增 Tick 或逐帧强制骨骼刷新。结束／打断时解除回调并销毁蓄积组件。

`ReleaseMagic()` 从同一 `CastingSpellPosition()` 发射，并从该点计算目标提前量。发射瞬间不会先回到旧掌骨位置。`MagicChargeForwardOffsetCm` 追加为 M07 魔法属性，现有 AI/F6 蓝图已保存为 65 cm。共享玩家特效资产及技能伤害、射程、CD 未修改；动作总时长由现有战斗时钟读取新片段长度。

## 产物与接入

- 作者脚本：`Tools/BlindSupplicantM07/author_flow_cast_v24.py`。
- 导入脚本：`Tools/BlindSupplicantM07/import_flow_cast_v24.py`。
- 可编辑源：`SourceAssets/BlindSupplicantM07Meshy20261001/FlowCastV24/Motion/M07_Original_FlowCast_V24.blend`。
- FBX：同目录 `A_M07_MagicGather.fbx`、`A_M07_MagicRelease.fbx`，30 fps，每段 34 帧；帧 0 仅供参考绑定、不参与导出，制作／导出使用 POSE 模式。
- UE 资产：`/Game/Monsters/BlindSupplicantM07/AnimationsFlowCastV24/A_M07_MagicGather` 与 `A_M07_MagicRelease`。
- 实际蓝图：`/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07`；仍由原 AI/F6 入口使用。
- 导入前蓝图文件备份：`FlowCastV24/Before/BP_BlindSupplicantM07.uasset`。
- 保存回执：`FlowCastV24/ue_flow_cast_delivery_v24.json`，记录 `saved=true`、两段动画与蓝图、0.30 秒出手和 65 cm 偏移。

## 必要构建与保存状态

Editor 构建完成：`Saved/BuildEditor/m07-FPSGAMEEditor-20261003-120951.log`。首次构建被共享 `M10Mawcrawler.h` 一行多变量 `static constexpr float` 声明的 MSVC C2487 阻塞；本轮仅拆成四条声明，常量数值及行为未改，随后构建成功。

Game 构建请求完成：`Saved/BuildEditor/m07-FPSGAME-20261003-121229.log`，工具返回 `Target is up to date` / `Succeeded`。

后台真实导入／保存日志：`Saved/Logs/M07Import-20261003-121321.log`。未打开或重启交互式编辑器，未自动运行游戏或执行验收。编译／包保存只说明产物已落盘，不代表穿模、动作自然度或性能已通过测试。
