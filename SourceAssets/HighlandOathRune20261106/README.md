# 誓约符文制作源

高地双手剑专属，剑身 II，特殊改造。原始设计为 `Concept/OathRuneAndJudgmentV1.png`。

## 正式行为

- 重击物理伤害 +15%，重击蓄力持续体力消耗 -20%；不减少出手体力费用。
- 首次达到实际 100% 后开启 `[满蓄时间, 满蓄时间 + 0.35s)` 裁决窗口，不重复开启。
- 窗口内释放：本次重击物理伤害再乘 1.35，韧性伤害再乘 1.5。
- 首次造成正伤害后返还本次出手实际支付体力的 25%，多目标只返还一次；未命中不返还。
- 强化突刺重击兼容；第三段、冲刺突刺、横扫、未经过实际蓄满的反击及衍生剑气不获得裁决增益。
- 取消、换武器、拆除符文、死亡清除动作状态。运行状态不保存；安装选择使用原有 `gunsmith_parts.blade_2` 存档。
- 体力返还使用累计回执 `OathStaminaRestored`，避免 RPC 和档案镜像乱序重复支付；旧存档缺少此字段时从 0 开始。

## 表现

金色剑形刻印和三道誓环。蓄力时从根部逐环亮起，临近蓄满收拢开口，窗口内和释放时提亮。原生刻纹与叠层共用金色，徽记保持宽高比；裁决剑气沿原空间扰动轨迹延长残留至0.82秒。当前入口为 `apply_gold.py`，改造图标保持灰阶。

准心外出现一次 0.06s 脉冲、四个金白括角及 0.35s 分段倒计时，透明中心保留瞄准点，提示横排「裁决就绪」。精准释放显示「裁决」，三道细光环沿实时刀身向剑尖移动。首次有效命中产生短促银金光屑。第三人称使用世界武器真实变换；HUD 仅持有者可见。

图标由内置 imagegen 生成，使用金属方框、四角铆钉、内圆边和灰阶浮雕。`Icons` 与 `Textures` 保留生成原件。提示音和命中金属音由 `author_audio.py` 原创合成，不依赖第三方录音许可。

当前图标恢复为认可的灰阶 V2：`IconV2/OathRune_Framed_V2.png`，`Icons` 及 `configure_runtime.py` 均引用 V2。用户纠正蓝色目标为剑身符文，误改的蓝色图标及制作文件归档到 `trash/HighlandOathBlueIconReverted20261106/`；V1 仍归档于 `trash/HighlandOathRuneIconV1_20261106/`。蓝色版本与旧回执已移入 `trash/HighlandSword20261107/SourceAssets/HighlandOathRune20261106/BladeBlueR1`。

## 制作与保存

- `configure_runtime.py`：精确接入目录、图标源和符文材质选择。
- `author_audio.py`：生成 48kHz 单声道 WAV。
- `oath_surface.hlsl`：刀身刻印及逐环蓄力参数。
- `install_assets.py`：后台导入 PNG/WAV、制作并保存表面与光带材质；`saved-assets.json` 记录实际保存结果。
- `build_and_save.ps1`：使用现有 UE 批次互斥，保留已打开编辑器；正式编译后执行无界面 Python commandlet。
- 日志目录：`D:/FPS3D/FPSGAME/Saved/HighlandOathRune20261106`。

2026-11-06 交付：`FPSGAMEEditor Win64 Development` 正式编译成功；后台 Python commandlet 已保存 9 项资产，保存回执 `complete: true`，导入日志已输出 `OATH_ASSETS_SAVED`。包含 7 项新资产，以及原刀身两份材质的可选银白刻纹参数。

源码、资产制作和构建属于交付；本批按用户规则不运行游戏、自动测试、联机测试或验收截图。实际表现与联机体验由用户测试。修改旧审计源中的重击 RPC 调用仅用于适配新增参数并完成编译，没有执行这些审计。


2026-11-07 后续金色修订、护手返体联动及已完成检查范围见工程 `Docs/Publication/HighlandSword20261107/README.md`。上文初次保存记录保留其原时间范围。
