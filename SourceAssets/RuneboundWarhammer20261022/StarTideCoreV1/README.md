# 星潮之核

用户已批准 `../EverflowOrbConceptV1/everflow_blue_orb_design_01.png` 的造型，并将正式名称改为“星潮之核”。本修订为符文战锤独占特殊改造，保存身份 `pommel / star_tide_core`。

## 精细模型与材质

两片反向弯月护架采用有背面和侧壁的实体截面，银色外缘与下沉的深蓝珐琅面分层。斜向符文环轨包含实体刻槽、32 个蓝晶嵌窗及独立宝石卡座。六辐底托保持真实镂空和厚度，上端使用分层六角接座、凹面符文板与微型紧固件。保留原装上端 2 mm 接口、局部原点和 `(0,0,-8.5)` cm 安装偏移。

紫色款的纵向护爪未复用到新外形。蓝晶球直径 81 mm，表面使用独立光学材质。主要轮廓、台阶、倒角、刻槽与镂空均为几何；4096×4096 BaseColor、ORM 和切线法线保存表面差异及金属微纹。ORM 为 AO/Roughness/Metallic；OpenGL 法线在 UE 导入时翻转绿色通道。

球内包括 24 步局部体积能量云、4 条组成双螺旋的实体光流、脉动核心和 48 颗实体光点。`RuneAwake` 和 `RuneImpact` 驱动蓝色亮度，固定蓝色不随其他锤头的 `EnergyTint` 变色。像素体积坐标采用 `LocalPosition / Component / Exclude Material Shader Offsets`；顶点位移使用独立顶点坐标，避免上一款球体的像素编译错误。

## 持续时间效果

符文唤醒已激活时，每次实际伤及目标的武器命中增加 0.5 秒剩余时间，无上限。命中回调位于服务器成功伤害结算之后；加时位于蓄能的攻击序号去重之前，因此同次群攻命中多个目标、旋风的后续有效接触均各自计入。原有非唤醒蓄能仍按一次攻击累计一次，不因新配重改变。

| 通道 | 现有汇入路径 | 新效果位置 |
| --- | --- | --- |
| 普通、重击与冲刺钝击 | `ProductionAxeContact`、`WarhammerShockwave` 进入 `ColdSteelSkills::ApplyHit` | 成功伤害后的 `RecordRuneboundHit` |
| 镇魂钟两段重击 | 两个独立攻击序号的钝击结算 | 每段实际命中计入 |
| 上挑 | `ProductionBluntUppercut.cpp` 中的 `ApplyHit` | 每个成功命中的目标计入 |
| 旋风 | `SweepBluntWhirlwind` 中的 `ApplyHit` | 不受蓄能攻击序号去重影响 |
| 快速近战 | `WarhammerQuickCombat` 中的 `ApplyHit` | 每个成功命中的目标计入 |

沿用已复制的双精度到期时刻，由服务器累加并通知客户端。HUD 将延时作为命中脉冲，不重复播放整条唤醒入场闪光。原有死亡、切换与自然到期处理保持不变。配重基础唤醒时间仍为 20 秒，不继承紫色球的固定 +10 秒。

## 生产与接入文件

- `author_model.py`、`StarTideCore_Construction.blend`、`StarTideCore_Editable.blend`：精确建模与可编辑源。
- `Export/SM_Runebound_StarTideCore_V1.fbx`、`Textures/`：实际导出与 PBR。
- `derive_pipeline.py`、`import_assets.py`、`nebula.ush`：从已修复的材质合同派生蓝色材质。背景导入显式使用 D3D12/SM6，完成各材质 GPU 编译后才发布。
- `author_icon_input.py`、`star_tide_actual_gray.png`、`icon_prompt.txt`：由实际模型制作的灰阶图标输入和内置 imagegen 提示词。灰阶仅用于改造图标，游戏模型保留蓝色。
- `build_receipt.json`、`import_receipt.json`、`published.json`：分别记录必要构建、资产保存/着色器编译与目录接入结果。

未启动游戏、截图、运行自测或视觉验收。生产烘焙与实际模型图标渲染属于资产制作；最终实机外观和手感由用户确认。

本次生产已完成：Editor/Game 构建成功；8 种材质在 D3D12/SM6 后台作者进程中生成了实际像素着色器；模型、材质、纹理和图标保存后，运行目录与作者镜像均已加入 `star_tide_core`。具体结果保存在上述三类回执中。
