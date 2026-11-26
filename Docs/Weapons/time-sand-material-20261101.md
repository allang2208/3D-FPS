# 时砂秘金：符文长剑传说材质改造

2026-11-01 按用户接受的设计接入，用户明确要求回响也触发符文长剑原生的减魔法冷却被动。

## 玩家效果

- 适用武器：符文长剑 `ue_rune_sword`；材质栏 `blade_material`，选项 `time_sand_gold`，传说级。
- 剑刃有效命中后 0.6 秒，对该目标追加本次实际伤害的 30%。保留基础／附加、物理／魔法四路伤害比例，原命中的暴击与防御结果已包含其中，不再次暴击或重复扣防。
- 回响造成有效伤害后，再触发原生减冷却：魔法及 G 飞剑剩余冷却减少 0.5 秒；金色符文强化后为 1 秒。原命中和回响各自结算，同一挥的多个目标回响只额外结算一次。
- 攻击耐力消耗增加 15%。普通剑刃、连击、重击、突刺、上挑及旋风剑刃沿同一结算路径；配重锤、快速近战、剑气及 G 飞剑不产生回响。
- 回响不再生成回响，不触发其他命中附效，不重复削韧或打断。目标在延迟期间已死亡则不结算；攻击者死亡后未结算回响取消。

## 外观与资料

模式 7 当前使用香槟金基底、精抛刃缘、纵向细拉丝反光和稀疏缓慢流动的细砂亮点。V2 提高金属反射率、降低粗糙度，保持原结构法线；光泽来自金属反射，不叠加假高光或剑面自发光。剑身与剑根沿当前整段覆盖遮罩，保留原生符文、宝石、发光、湿润和 Substrate 链路。第一人称及观察者挥剑沿既有剑迹组件显示短金色残影。

命中剑痕随目标位置移动，0.6 秒后闪现并在 0.35 秒内化为砂粒消散。单组件使用最多 128 个实例呈现，资源异步加载，空闲时停止 Tick。

正式材质：

- `/Game/Weapons/AzureRunesword20260913/M_AzureRunesword`
- `/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold`
- `/Game/Weapons/AzureRunesword20260913/TimeSand20261101/M_TimeSandEcho`

灰阶改造图标由内置 image_gen 基于已认可的原厂剑刃图制作，保留原有轮廓、符纹、方框、铆钉和内环，仅改变材质表面。提示词保存在 `SourceAssets/TimeSandMaterial20261101/icon-prompt.json`，母图为同目录 `time_sand_gold.png`；正式 PNG／Texture2D 键为 `Content/ColdSteelData/AttachmentIcons20260913/ue_rune_sword_blade_material_time_sand_gold`。

## 运行接入

目录字段 `time_sand_echo_ratio`、`time_sand_echo_delay` 进入现有物品改造聚合，出手快照记录回响比例、延迟和本次减冷却值。`ApplySkillWeaponHit` 在权威剑刃伤害完成后提交实际伤害凭据，`UTimeSandEchoComponent` 延时结算。服务端重建远端快照时保留攻击序号，回响按武器实例与攻击序号去重减冷却。

回响使用已结算伤害凭据直达现有伤害接收链，避免再次进入武器命中附效。减冷却复用 `ReduceRuneSwordHitCooldowns`，包含服务端影子档案和拥有者客户端反馈。命中剑痕状态复制给相关客户端，伤害数字仅发给攻击者。近期攻击去重记录上限 128，避免较长攻击的早期剑痕消失后再次获得回响减冷却。

V2 的追加命中在 `ClientEchoDamage` 收到权威回执后，向攻击者播放现有近战确认音 `S_Player_MonsterHit`。预载沿用现有异步资源句柄，接触时不做同步加载。没有实际命中不播放；致命回响即使伤害接收器返回 0，或目标在回执到达前消失，仍保留声音反馈。这里不调用带金刚符文命中钩子的 `NotifyConfirmedWeaponHit`，不新增回响或其他攻击附效。

选项仍使用现有 `gunsmith_parts` 存档合同；外观沿用已复制的 `BladeFinishMode`，没有更改存档格式。新资源位于已有 Cook 目录。

## 制作入口与交付状态

作者目录 `SourceAssets/TimeSandMaterial20261101`：

- `install_catalog.py` 仅合并本选项，保留寒晶 50% 配置及其余改造。
- `install_materials.py` 在当前整段剑身／寒晶材质图上添加模式 7，实际编译并保存两套主材质、回响材质和图标；按当前完整材质图重建后再运行本脚本。
- `echo.hlsl` 为剑痕及消散效果。
- `run_asset_task.ps1` 沿现有互斥使用后台 commandlet；`build.ps1` 完成必要原生构建。

目录已落盘，材质与图标已实际导入保存。FPSGAMEEditor 后台构建成功（797 项任务，`UnrealEditor-FPSGAME.dll` 已链接），记录在同目录 `build-receipt.json` 与 `build-editor-20261101-145859.log`。本次未启动 UE 编辑器界面、游戏、测试、截图或画面验收，由用户进行游戏测试。

## V2 金属精抛与回响确认音（2026-11-01）

作者入口为 `SourceAssets/TimeSandPolish20261101/install_materials.py`，在当前两套母材质上只替换模式 7，并扩展该模式的各向异性／切线。普通、金色和银色原生符文沿原母材质继承。旧 V1 初始化脚本保留；从源重建时在陨铁 V2 接入之后执行本精抛脚本。

主要制作值：香槟金反射色 `(0.74, 0.49, 0.22)`、金属度 `0.98`、剑面粗糙度约 `0.195`、刃缘 `0.11`、纵向各向异性 `0.38`（刃缘减弱）。细砂有像素导数过滤，模式 7 不再向原法线叠加动态凸点。伤害比例、延迟、减冷却、耐力代价和限定品质保持既定设置。

本轮保存与构建状态分别记录在该作者目录的 `material-receipt.json`、`build-receipt.json`；没有追加游戏、联机、截图或试听测试。

V2 已完成落盘：两套母材质编译并保存成功；`FPSGAMEEditor Win64 Development` 常规构建成功，4 项任务包含 `TimeSandEchoComponent.cpp` 和基础 `UnrealEditor-FPSGAME.dll` 链接。构建日志为 `build-editor-20261101-202202.log`。用户结束播放并关闭编辑器后通过后台完成，没有重新启动编辑器。
