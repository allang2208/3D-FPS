# SUPER90 普通空仓：Cransh 枪机释放动作

用户指定参考 Cransh 的 [FPS Benelli M4 Animations](https://sketchfab.com/3d-models/fps-benelli-m4-animations-225a62190f6043ca975eaa2798ab7e2c)。本次恢复其原生普通空仓收尾中的短促释放动作，替换后来拼接的左手反手拉柄段。

原动画作者 Cransh；原枪模型署名 haoliu95，原手套模型署名 teenjust500。项目原始获取回执记录为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，本次属于基于原作的游戏适配，保持原署名及许可记录；使用当前项目 V7 裸手。

## 动作与接触

- 当前普通空仓第 0–360 帧逐发装弹原样保留，包括每发提交、少量补弹与提前结束循环使用的边界。
- 第 361–424 帧采用拼接改动前的 Cransh 原生轨道：右手完成短促释放与回握，左手继续支撑前端。移除普通空仓中先右手回握、再左手跨枪拉柄的两段拼接。
- 来源为 `SourceAssets/Super90NativeEmptyBolt20261010/inputs.json` 中保存的原 424 帧普通空仓采样；原作者 FBX 与来源回执仍保存在 `SourceAssets/BenelliM4Super9020261006/`。
- 四类握把只重写普通空仓对应条目。前 360 帧保留当前安装的数据；释放尾段保留最新成组手指姿势，以枪身空间握点适配完整左臂。原生骨长、当前 V7 手模及蒙皮不变。
- 此次按指定参考保留“逐发装填、尾段释放”的原动画结构，没有另外制作抛壳口首发装填分支；不能把它宣称为重新制作了一套完整实操流程。

## 时钟与作用范围

源动画恢复为 424/60 秒。原作者枪机在第 370 帧开始明显闭合，第 374 帧抵达前止点；闭栓音效和上膛完成统一使用 `374/60` 源秒。

普通空仓沿用原逐发倍率，取消仅为反手拉栓拼接设置的 2.16 秒尾段重定时，并去掉该分支的后拉音效。少量装填、提前结束循环与握把差量继续读取相同源时间；音效通过现有 `ReloadRuntimeTime` 反向映射。

快速装填器及中断后仅补拉栓的独立 cycle 本次不改。其旧拉柄、释放、上膛事件已与普通空仓的释放事件拆开，避免缩短原生尾段后串用事件帧。

## 制作与保存

- 制作目录：`SourceAssets/Super90CranshRelease20261012/`。
- 可编辑源：`Super90_CranshRelease_Editable.blend`，包含基础动作和 vertical、canted、prism、angled 四种握把动作。
- 制作脚本：`author_release.py`；UE 写入脚本：`save_assets.py`；输入：本次编辑器读取的 `inputs.json`。
- 保存资产：`/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_reload_full` 及 `/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_{vertical,canted,prism,angled}`。
- 源码：`FPSGAMECharacterSuper90.cpp`、`Weapons/Super90WeaponAssets.h`。仅调整普通空仓尾段、对应事件及独立 cycle 的事件命名，保留散布、挂件和其他并行改动。
- 本次开始时的源码和五项资产备份在 `Before/`；动作保存回执为 `save_receipt.json`。其他 Profile 条目保留。

必要构建记录以此制作目录中的构建日志及 `delivery.json` 为准。本轮没有运行游戏、制作验收截图或执行回归；动作自然度和最终游戏内接触由用户体验。
