# 玩家全身模型与双套动画

2026-09-21。宿主：`D:/FPS3D/FPSGAME`。用户批准保留当前第一人称动画，以 UE 默认角色和独立简化动作制作世界中的玩家身体，为后续联机与换装提供基础。

## 已接入的范围

- `AFPSGAMECharacter` 创建 `PlayerBody` 默认组件，使用继承的 `GetMesh()` 显示由 `SKM_Manny_Simple` 复制的 `SKM_Manny_PlayerSkin`（全身皮肤材质）。沿用原胶囊体、摄像机、输入、移动和战斗计算。
- 第一人称网格仍由原系统驱动；相机下面的视模与配件仅拥有者可见。全身身体、世界武器和衣物对拥有者隐藏，可投射全身影子。预览场景中的武器图标/枪匠作者角色不会初始化全身组件。
- 独立原生动画图包含 Unarmed/Rifle/Pistol 的待机、八方向走路与慢跑、起跳/下落/落地、步枪/手枪装备和换弹、死亡动作。蹲伏采用骨盆下降与腿部 IK；持械左手按照实际武器握距跟随。
- 第一、第三人称共用既有动作状态、持续时间与阶段。第三人称使用显式动画采样，不执行动画通知、不增加伤害或弹药结算。上半身换弹不打断下半身移动，换弹退出保留末态再淡出。
- 近战/双手采集工具使用独立简化手臂 IK 轨迹；左手施法与攀爬提供辨识姿态。它们没有复制第一人称精细接触，也没有声称完成所有技能的第三人称动画。
- 世界武器单独采样当前武器的待机握持姿态，隐藏手臂材质区，把枪体与当前可见配件挂到身体手骨。不会逐帧复制镜头空间的开火、甩匣、抖动或动作骨骼。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `Source/FPSGAME/Characters/FPSPlayerBodyComponent.*` | 生命周期、读取现有动作状态、自己/他人可见性、状态复制入口 |
| `Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.*` | 独立第三人称动画图、移动混合、上身动作和 IK |
| `Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp` | 世界武器及配件、服装、第一人称材质映射 |
| `Source/FPSGAME/Characters/FPSPlayerBodyTypes.h` | 网络表现状态、装备配方和外观 ID |
| `Content/ColdSteelData/player_body.json` | 身体、动作资源和服装映射 |
| `Tools/PlayerBody/prepare_manny_assets.py` | 从本机 UE 5.8 模板补齐缺少的动作，不覆盖现有资源 |
| `Tools/PlayerBody/import_manny_assets.py` | 通过现有编辑器桥登记资源、记录源动画时长与帧数 |
| `SourceAssets/PlayerBody20260921/` | 模板来源清单和动作元数据 |

## 后续换装

当前保持 Manny 的网格和骨架，使用独立全身皮肤材质，没有新增装备或服装资产。`outfits` 表按现有装备物品的 Definition ID 配置；装备栏中的实例及位置继续由原存档保存。脱下、切换装备、读档和新角色初始化会重新计算外观。

以下为配置格式示例，不是已存在资源：

```json
{
  "outfits": {
    "your_armor_definition": {
      "world_mesh": "/Game/YourClothing/SK_Armor.SK_Armor",
      "hide_body_materials": [0],
      "body_materials": {
        "1": "/Game/YourClothing/MI_Body.MI_Body"
      },
      "first_person_materials": {
        "actual_material_slot_name": "/Game/YourClothing/MI_Sleeve.MI_Sleeve"
      }
    }
  }
}
```

- `world_mesh` 必须与 Manny 骨架结构兼容，采用 Leader Pose 跟随全身动作，不跟随第一人称动画。
- `first_person_materials` 的键是现用手模真实材质槽名。只替换组件上的材质引用，不改共享材质资产。
- `hide_body_materials` 是身体材质区索引，不是任意身体分区。默认 Manny 只有既有材质分区；精细上衣/裤子/鞋自由组合需要分区人体或专用遮罩，不能把隐藏整块材质当成已实现精细遮挡。
- 全身衣物与第一人称袖子/手套可以使用不同精度和独立网格。当前运行接口覆盖材质替换和全身服装；真实厚袖口、独立第一人称几何、裙摆/披风布料、多体型和捏人仍需对应资产与扩展。
- 原始手臂材质按网格资产分别缓存，换枪后不会把上一把枪的材质槽恢复到新模型。

## 全身皮肤材质（2026-09-21）

用户要求全身材质换成皮肤，同时检索 Fab 免费头部。已通过当前编辑器创建并保存以下独立资产，`Content/ColdSteelData/player_body.json` 的 `body_mesh` 已切换：

- 网格：`/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin`。
- 材质实例：`/Game/Characters/Mannequins/PlayerBodySkin/MI_PlayerBodySkin`。
- 父材质：`/Game/Characters/Mannequins/PlayerBodySkin/M_PlayerBodySkin`。
- 散射配置：`/Game/Characters/Mannequins/PlayerBodySkin/SSP_PlayerBodySkin`。

身体的 `M_HeadLegs` 和 `M_Torso` 两个槽全部使用新皮肤材质。基础肤色沿用现有第一人称露肤的线性 RGB `(0.36, 0.235, 0.185)`，新增细微肤色变化、毛孔法线、非金属粗糙度与 Subsurface Profile。没有复用原 mannequin 的金属色、服装贴图或硬表面法线；网格上的几何拼缝和硬质轮廓仍然保留，此次没有重做人形裸模。

在材质实例中可调 `SkinTint`、`SkinRoughness`、`SkinSpecular`、`SkinScatterStrength`、`SkinDetailStrength`、`PoreTiling` 和 `ToneVariation`。这些参数只影响第三人称身体。第一人称手臂/衣袖/手套资产及动画均未修改，原 Manny 资产也保留。

作者源：`SourceAssets/PlayerBody20260921/body_skin.hlsl`；接入脚本：`Tools/PlayerBody/install_body_skin.py`；保存回执：`SourceAssets/PlayerBody20260921/body_skin_install.json`。皮肤为本地程序材质，无新增下载贴图。新资产位于已有 Manny cook 目录内，不增加另一条打包目录。

新建玩家身体时读取该配置；已有游戏实例需下一次生成角色才读取。未启动 PIE、截图或渲染，视觉效果由用户测试。

Fab 候选和来源记录见 `SourceAssets/PlayerBody20260921/fab-head-candidates.md`。当前只完成检索，没有下载或替换头部。

## 用户反馈修复（2026-09-21 晚）

用户明确要求排查待机浮空、奔跑僵硬且步频过快、第三人称无枪和全身皮肤未生效。本节覆盖前文初次交付中的材质与验证状态描述。

- **浮空**：运行时初始 mesh Z 是 `-96 cm`，但角色类默认 mesh Z 为 `0`。UE 的 `ACharacter::OnStartCrouch/OnEndCrouch` 从类默认值恢复偏移，蹲伏或滑铲结束会把身体抬高一个胶囊半高。现将 `-96 cm` 和 Manny 的 `-90°` 朝向写入角色构造默认值，保持原胶囊和移动合同。重启后读回类默认值为 `-96`；实际蹲伏时 mesh 相对 Z 为 `-72`、世界根部 Z 仍为 `2.216 cm`，没有随胶囊半高悬空。完整站起序列未完成复查。
- **步频与僵硬**：旧代码把整段片段按最多 `2.5 次/秒` 循环；步枪前跑源动作实际含 3 轮步态，等效播放率达 `3.83 倍`。现在按 `L/R` 接触标记同步每轮步态，依据源时长与步数换算速率，300/600 cm/s 为源步行/跑步速度参考，倍率封顶 `1.25`；700 cm/s 奔跑对应约 `1.17`。速度、方向与移动混合平滑过渡。步枪四条斜向片段没有同步标记，其脚部轨迹与前/后源动作一致，复用对应时序。原模板中 1–4 轮步态均保留，源动画资产不改写。
- **世界枪械**：实际 A762 世界实例的缩放为 `0.01`；导入手骨有 `100` 缩放，直接求握枪骨逆变换把整把武器压缩了。现只反转握枪骨的位置/旋转，左手 IK 的相对握点也去除骨骼缩放。材质屏蔽不再把名称中的 `Handguard` 当作手臂，保留护木及已有枪匠配件。
- **皮肤**：原脚本修改的是 UE 材质槽结构体数组的迭代副本，没有写回数组。已补 `materials[index] = item`，重新保存独立身体网格；两个资产材质槽和本次 PIE 角色实际材质均读回为 `MI_PlayerBodySkin`。原 Manny 与第一人称材质不修改。

诊断记录在 `Saved/PlayerBodyFix20260921/`：`snapshot-192131.json` 为旧材质，`snapshot-192437.json` 为皮肤生效后的实际角色与 0.01 倍世界枪，`snapshot-194033.json` 记录类默认 mesh Z 为 0，`source-poses.json` 记录 48 条移动动画的时长、标记和相关源骨骼轨迹。

当前接入状态：用户关闭编辑器后，常规 `FPSGAMEEditor Win64 Development` 构建成功（144 个动作，`Saved/BuildEditor/build-20260921-194459.log`），不是仅有 Live Coding 补丁。重新启动编辑器，在 `L_Dungeon_Prototype` 的实际玩家上通过原 F6 会话选项切换第三人称；`snapshot-194832.json` 确认身体与世界枪均对拥有者可见，第一人称手模隐藏，A762 世界实例缩放从 `0.01` 恢复为 `1`，左右握枪骨位置分别与全身左右手重合，身体两个材质槽仍使用皮肤实例。

诊断期间的 Python 蹲起辅助脚本曾因 `uncrouch` 方法名错误停在蹲伏，已改为实际接口 `un_crouch`。补查站起前编辑器正常退出，故完整蹲起序列、奔跑视觉流畅度和其他枪型的实机外观不标记通过，交由用户复测。没有修改玩法移动速度或已认可的第一人称动作；没有执行无关回归。

## 蹲走腿脚调整（2026-09-21 续）

用户反馈蹲下移动时腿脚姿态错误。原实现仅把骨盆压低 40 cm，仍按速度混入站立 Jog，并用随脚移动的膝盖极向量与第二次蹲伏权重混合来解腿部 IK。

本次在 `FPSPlayerBodyAnimInstance.cpp` 内调整第三人称表现：

- 蹲走逐渐退出 Jog，完全蹲伏只取已有 Walk 的左右脚接触时序；不改移动速度、碰撞和第一人称动作。
- 增加独立待机参考采样，用当前武器家族的真实待机落脚位置作为步幅中心。蹲走水平步幅为 72%，抬脚幅度为 45%，脚掌和脚趾向该待机姿态回收 75%，减少高抬脚和站立步行的明显蹬脚动作。
- 步频参考速度同步乘以 72%，保持缩短后的步幅与现有 250 cm/s 蹲走速度相配。
- 骨盆后移 6 cm 并下移 40 cm，上身前倾 6°以平衡。膝盖目标从原动画膝位平滑转向各自髋部前方、略向外侧的位置，不随脚在前后/横移时跨过髋部。
- 骨盆与脚部目标只应用一次蹲伏过渡权重；腿部 IK 完整到达混合后的目标，修正起蹲过渡时脚底未补偿完全的问题。

当前接入状态（2026-09-22 更新）：蹲走修改已进入后续常规 Editor 构建；`Saved/BuildEditor/build-20260922-083740.log` 记录该动画源文件编译成功，动作映射后续调整的最终构建见 `build-20260922-175139.log`。没有为此启动 PIE、截图或运行回归；蹲走实际观感由用户测试。新增动作适配见 [第三人称动作映射调整](player-body-action-adjustments-20260922.md)。

## 联机边界

`FFPSBodyState` 包含武器类型、动作、服务端时间基准、持续时间、接触比例、瞄准角、奔跑/蹲伏/滑铲等表现状态。装备配方和服装 ID 独立复制。没有骨骼逐帧广播。

- 单机/本地玩家自动读取当前游戏状态；服务器可调用 `SetAuthoritativeState` 和 `SetAuthoritativeEquipment` 发布其他玩家的权威表现，客户端 RepNotify 重建网格。
- 这些入口不是客户端 RPC，不把客户端本地存档变成服务端装备授权。完整联机时，由服务器战斗/装备系统接入这两个入口。
- 当前武器、库存及部分移动技能仍有单机实现，未在本任务中整体改成服务器权威；远端玩家攻击请求、弹药与伤害确认、特殊移动预测、重连持久化均不因此完成。
- 本次保留原胶囊碰撞合同，身体模型不新增爆头/肢体命中框或布娃娃同步。
- 身体缓存其初始网格偏移，供 ACharacter 的蹲伏和网络平滑使用。专用服务器不创建额外世界表现资源。

## 当前简化表现与后续资产工作

- 步枪/手枪使用通用第三人称换弹，全枪机械件和弹匣仍保持握持模型；没有第三人称逐枪甩匣或机械动作。
- 双持可显示两把世界武器，基础上身仍为通用手枪动作，双持专用动作和左手武器朝向需要后续精修。
- 剑/工具为简化握持与攻击轨迹；旋风、多段特殊攻击、蓄力、格挡反应、镜头检视等不是完整逐动作适配。
- 施法只接手势辨识，不额外生成一份飞行体或伤害；世界施法特效后续由技能联网工作接入。
- 没有手臂网格的旧静态采集工具还需要独立第三人称握持配置。
- F6 → 基本调参 → 玩家视角可切换第一／第三人称。第三人称镜头沿瞄准轴后移 300cm，带墙壁扫掠；全身、世界武器与衣物对拥有者显示，第一人称网格隐藏。门窗与建造保持从角色眼部计算操作距离。未制作第一人称低头可见腿部的显示方案；开发开关默认仅用于当前单机会话，全部关闭恢复第一人称，不写入存档。具体说明见 `Docs/UI/development-view-toggle-plan-20260921.md`。

## 资源来源与制作记录

59 条动作来自本机安装的 UE 5.8 `Templates/TemplateResources/High/Characters/Content/Mannequins/Anims`。本次补入缺少的 57 条文件，保留工程已存在的两个动作以及 Manny 网格、骨架和材质。

资源受其原 Unreal Engine 模板许可约束；这里只在本机工程使用，不把原始模板二进制公开提交。`Config/DefaultGame.ini` 已补 Manny 内容目录的 cook 引用，JSON 沿用项目 `Content/ColdSteelData` 的打包路径。

按用户规则，未运行 PIE、游戏回归、联网测试、截图或验收渲染。必要的 Editor 原生构建属于开发接入；动画外观、武器朝向和多人表现仍由用户测试。

构建记录：常规 `FPSGAMEEditor Win64 Development` 构建已完成。中途曾因编辑器占用 DLL 出现 LNK1104；当时编辑器有不属于本任务的未保存包 `/Game/ColdSteelData/Icons/ue_a762`，已按用户规则保留现场。

用户关闭前台窗口后，后台 UE 进程 `31536` 曾继续占用 DLL。用户随后授权处理残留进程；实际执行时该进程已自行退出，没有执行强制终止。最后一次常规构建返回 `Result: Succeeded`、`Target is up to date`（0 个待构建动作），最终模块已是最新，无待完成链接。日志：`Saved/Logs/PlayerBodyBuild20260921-complete.log`。没有启动编辑器、PIE 或游戏测试。

最终构建命令（不运行游戏）：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE
```
