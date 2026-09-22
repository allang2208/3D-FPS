# 寒晶自带侵蚀与专属精神迸发

> 后续根据用户反馈，精神迸发的紫色硬线外观已调整为冰蓝晶光、圆润波纹与淡入淡出。当前材质制作源见 `../FrostSpiritBlend20260922/README.md`；以下保留初版记录，伤害与专属改造规则仍适用。

寒晶双手剑自带侵蚀效果：每次近战附加「智力×10%＋精神×10%」魔法伤害。剑身Ⅱ的普通侵蚀改造对寒晶移除，替换为仅寒晶可用的「精神迸发符文」，使自带侵蚀伤害乘 2，即「智力×20%＋精神×20%」。苍蓝符文剑保留普通侵蚀改造。

倍率只作用于自带侵蚀，不翻倍基础物理伤害、其他来源的附加伤害或全部魔法伤害。结果进入现有统一伤害分项，再应用攻击方式倍率、套装/导魔倍率与目标魔法防御。更换为共鸣、导魔或金色符文时，自带侵蚀伤害仍保留。

## 数据与接入

- `Content/ColdSteelData/items.json`：寒晶的 `innate_erosion_intelligence`、`innate_erosion_wisdom` 均为 0.1，更新物品描述。
- `Content/ColdSteelData/melee-gunsmith.json`：`erosion_rune` 限定苍蓝；新增 `spirit_burst_rune` 限定寒晶，`innate_erosion_mult=2`。
- `FMeleeModifiers::InnateErosionMultiplier` → `MeleeGunsmith` 读目录 → `GunsmithSystem::Calculate` 汇总 → `WeaponDamagePanel::Evaluate` 统一计算。改造预览、物品提示和实际攻击共用计算。
- 原装寒晶显示较克制的紫色侵蚀裂纹；精神迸发使用独立材质；其他选项显示对应纹样，自带伤害不因外观切换消失。
- `FrostSwordRunes.h` 统一旧选项兼容规则。`ColdSteelProfileRuntime::ReloadProfile` 在现有 A/B 存档事务内补充寒晶自带系数、更新描述，将旧 `erosion_rune` 转成 `spirit_burst_rune`。物品身份、位置、强化、附魔和其他改造不变。没有离线重写用户的 `.sav`；转换在用户下次正常加载档案时执行。
- 物品提示增加「武器自带效果·侵蚀」说明；改造总览显示自带侵蚀伤害倍率和统一计算的附加魔法伤害。

## 新材质

`/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit` 从当前共享符文表面材质复制，保留投射坐标、曝光补偿及原纹样采样，不重建或删除现用材质图。

在原侵蚀裂纹上增加三枚紫晶菱形节点：聚能后释放一对向外扩张的菱形波纹，随后恢复。紫罗兰为主色，小面积冰蓝内核呼应寒晶主体；节点有相位错开，发光保留颜色并限制峰值，避免白化。材质端表现为循环荧光，不新增范围伤害、额外攻击次数或命中触发机制。

原始裂纹遮罩：`/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_erosion_rune`。可编辑完整代码在 `spirit_burst.hlsl`；制作参数在 `production.json`。

## 专属图标与制作

使用内置 image_gen 生成，延续既有冷钢语义图标风格：紫晶核心、双重能量回响、银色倒角、主要尖端向左。提示词在 `icon_prompt.json`，生成原图为 `spirit_burst_generated.png`。交付图 `ue_frost_crystal_sword_blade_2_spirit_burst_rune.png` 为 1024×1024 RGBA，保留生成透明度，仅统一尺寸与留白。

`prepare_assets.py` 整理材质源和图标；`install_assets.py` 通过互斥 MCP 桥创建、编译、保存独立材质，并导入图标到 `Content/ColdSteelData/AttachmentIcons20260913`。`Before/` 保留相关代码与数据修改前副本。

## 完成记录

- `Tools/Build/Build-Editor.ps1` 常规 FPSGAMEEditor 构建成功，完成 198 个构建动作；编译涉及当前目标的依赖，不能解读为只编译本功能。日志：`Saved/BuildEditor/build-20260922-130041.log`，摘要在 `build_receipt.json`。
- 首次资产接入时无在线编辑器节点，随后一次排队超时未发送请求，另一次发现编辑器连接已断开。这些调用没有写入本轮材质或图标。
- 在没有编辑器进程时重新打开工程（`editor_launch.json`），最终经互斥桥成功完成独立材质和图标导入保存，记录为 `install-assets-result-04.txt`、`install_receipt.json`。
- 新编辑器在常规构建完成后启动并加载项目模块，保持 PIE 未启动；`editor_module_receipt.json` 只记录加载状态，用于判断重载需要，不是玩法测试。
- 未运行游戏、截图、效果验收或自动化测试，由用户自行测试。旧存档转换将在用户下一次正常加载档案时执行。
