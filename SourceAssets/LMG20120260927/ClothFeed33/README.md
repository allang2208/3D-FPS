# 201 布料弹药箱接入：ClothFeed33

**当前外观修订（2026-09-30）：** 上部几何、织物过渡、接口和图标已由 [ClothTop45](../ClothTop45/README.md) 局部替换并保存。此目录继续提供原有动画与供弹身份；以下为最初接入记录，不要重跑旧整枪安装器覆盖 C45／J44。

本轮按用户要求重新启用**新模型的布料弹箱**，原装 30 发弹匣继续保留。新选项是 `lmg201_cloth_box`；此前退役的金属弹箱 `lmg201_ammo_box` 及其存档清理逻辑不恢复。

## 已制作内容

- `Install30/LMG201_R30_NativeFit.blend` 中的 AmmoBag、AmmoBelt 原本已拆分，且已作为独立静态资产导入。此前它们仅作为储存件，不参与玩法。
- 复用这两件现有几何、UV 和织物贴图，绑定到现有旧箱／新箱及弹链骨骼；不新建武器骨架，不覆盖原生 V7 手臂，不重做枪体外壳。
- 布袋使用 Install30 的织物、缝线／法线与湿润材质。可见的六段弹链分别绑定，窄连接带进行邻段过渡，不将整条弹链作为一个刚体旋转。
- 新、旧弹箱在明确时点切换材质分区显示，不缩放至零。枪匠预览、背包图标与掉落物沿用现有角色装配和分区复制路径。
- 枪匠「弹匣」新增「125 发布料弹药箱」。125 发来自用户参考视频界面，作为本项目游戏配置；基础换弹 6.2 秒。切回原厂恢复 30 发及 Magazine24 动作。

## 动作来源与适配方法

参考视频：`C:/Users/allan/Videos/NVIDIA/Delta Force/Delta Force 2026.09.28 - 22.36.59.03.mp4`。使用已提取的 Video26 参考帧读取开盖、旧箱退出、新箱装入、铺链、合盖及回握的可见顺序。视频未展示清楚的接触面属于三维适配，不能声称逐帧还原。

重新从当前 UE 读取 `PKMLowpoly20260922/Animations/A_PKM_reload_empty`，快照、散列和元数据见 `inputs.json`、`motion.json`。该来源包含 ArmJoint49、RightReload51、RightHand52 等当前修订；没有使用旧 201 弹箱动画作为手部目标。

新 201 弹链侧与 PKM 不同：开盖使用原生左臂完整 FK 链，装箱／铺链／合盖段将 PKM 的工作臂**整链镜像到左臂**，包括肩、肘、前臂、twist、手腕及手指。镜像按左右原生参考骨架转换；接触通过整链平移适配新部件，交接按局部 FK 混合。未运行双骨 IK、单独反转手腕、重新分摊 twist 或缩放骨段。

右手在动作内保持源 PKM 的完整持枪形态。动作入口和末尾分别交给当前 201 原装／vertical／canted／prism／angled 的待机；五类各保存普通、空仓两个片段。两类换弹共用视频所示装箱流程，通过是否有余弹决定旧弹链显示；没有额外拼入视频中未显示的 PKM 换弹末尾拉栓段。

| 源动画秒 | 接触／状态 |
| --- | --- |
| 0.715 | 开盖 |
| 1.870 | 旧箱离位 |
| 2.530 | 旧箱退出显示 |
| 2.915 | 新箱进入显示 |
| 3.795 | 新箱装入，提交弹药，保留待合盖状态 |
| 4.620 | 铺链到位 |
| 5.302 | 合盖，解除待完成状态 |
| 5.450–6.200 | 回握并恢复镜头相对位置 |

音效直接引用 `PKMReloadAudio::LoadContact` 解析到的现用 PKM 分段 SoundWave，不重新导入旧 WAV。动作、显示切换、音效和弹药提交均消费 `ReloadSourceTime`。合盖前中断保留现有存档中的 pending-cycle 状态，可从装箱后续接。

## 制作与接入入口

- `collect.py`：读取现用骨架、动作和来源元数据。
- `author_props.py`：既有布袋与弹链绑定、FBX 和可编辑模型。
- `author_motion.py`：五套完整 FK 动作键；普通／空仓分别接入。
- `author_scene.py`：将五套动作保存为可编辑 Blender Action。
- `author_icon.py`：制作必需的枪匠布料弹箱选项图标；不是验收渲染。
- `integrate.py`：先完成上轮 Surface32 原模型表面平整与降反光，再运行本轮 `install.py`。
- `install.py`：备份当前装配、合入布料弹箱分区、保存十条动画与图标，再仅发布 201 的枪匠选项。
- `run_headless.ps1`：编辑器关闭后，使用现有批次互斥启动无界面 commandlet。

UE 保存结果以 `delivery.json` 为准；源码构建以 `Saved/BuildEditor` 中本轮日志为准。**本轮未主动启动游戏、未做实机动画／穿模验收，由用户测试。** 尚无保存回执时，仅代表制作源和接入源码已完成，不能视为已进入当前游戏。

## 已落盘交付（2026-09-29）

- 正式模块构建成功：`Saved/BuildEditor/build-20260929-121835.log`，已写入常规模块 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。
- Surface32 枪体、前后瞄具、低反光材质与湿润绑定已保存；随后合入 ClothFeed33 布料弹箱和弹链，现用入口仍为 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。
- 十条换弹动画、布袋选项图标及 201 枪匠配置已保存，回执为 `delivery.json`；完整组装 FBX 位于 `Exports/SK_LMG201_Cloth33_Installed.fbx`。
- 导入日志：`commandlet-20260929-122210.log`，执行成功。原先 NullRHI 模式在整枪 FBX 导出时触发 UE 的 MeshObject 断言，已改为 `-AllowCommandletRendering -RenderOffscreen` 后台导出，未启动编辑器窗口或游戏。
- 旧资产保存在 Surface32/Previous、ClothFeed33/Previous 和各制作目录的 Before 下。未实机测试，不将保存／构建成功视为动作或穿模验收通过。
