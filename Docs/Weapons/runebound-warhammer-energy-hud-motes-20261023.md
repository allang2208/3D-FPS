# 符文战锤左侧能量条：漂浮光粒 V2

用户要求去除左侧符文能量条的菱形元素，用与原有风格相配的魔法漂浮粒子替换。

## 外观与动态

移除原材质程序绘制的七块悬浮菱形晶片，以及顶部圆环内的菱形核心、切面和直线刻纹。保留当前蓝色玻璃柱、能量液面、明灭火舌、刻度、双层圆环和环绕符带。

顶部改为柔和的魔力雾团和十颗圆形光粒。光粒沿略扁的轨道缓慢游移，轨道半径随呼吸轻微变化；柔光、短光尾和中心雾团共同表现聚能。两侧用二十二颗光尘替代硬质晶片，自下而上缓慢漂移并左右轻摆，按各自寿命平滑出现、消失，避免循环边界突然跳位。

新光粒随蓄能变亮，实际有效攻击带来短促亮度脉冲；符文苏醒时顶部光团轻微扩散并增亮，随后回到漂浮节奏。沿用原有蓝色、透明覆盖和 NoGamma 显示方式，不加入新的棱角图形。

原来的界面上下浮动、转身惯性、进场淡入和离场隐藏仍由 `UAzureDragonEnergyComponent` 驱动。充能次数、激活时长、伤害、符文改造数值和攻击命中效果不在本次修改范围。

## 接入

- 当前 HLSL 源：`SourceAssets/RuneboundWarhammer20261022/PassiveV1/RuneboundEnergyHud.hlsl`。原被动安装器和 V2 安装器读取同一源，后续重建不会重新生成七块晶片。
- 新运行材质：`/Game/Weapons/RuneboundWarhammer20261022/HudMotesV2/M_RuneboundEnergyHud`。
- 引用入口：`RuneboundHammerTuning.h::Hud`；仍通过符文战锤组件为已有能量条组件指定材质。
- 制作入口：`SourceAssets/RuneboundWarhammer20261022/HudMotesV2/author_isolated.py` → `install_assets.py`。独立后台作者项目只复制所需材质及五张现有纹理，保存一个新材质包后安装到新目录，不覆盖旧版和苍龙共享材质。
- 构建入口：同目录 `build.ps1`；先等待现有原生构建，Editor 构建前等待已运行的主工程后台 commandlet 释放模块，不关闭其他进程。

仍使用一个 Slate 材质四边形。新的明确漂浮光粒共三十二颗，使用固定的解析材质循环，不新增 UMG 控件、组件、Actor 或 Niagara 系统；保留原有轻量流光与稀疏细火星。

保存、安装、原生构建和交付状态分别记录于 `import_receipt.json`、`build_receipt.json`、`delivery_receipt.json`。源码或脚本存在本身不代表保存完成。没有运行游戏、截图、预览渲染或额外测试，实际观感与性能由用户确认。

## 已完成

独立材质 commandlet 正常退出 0，新版 UI 材质已保存并安装到正式 `Content/Weapons/RuneboundWarhammer20261022/HudMotesV2/`；保存文件摘要见导入回执。正式 `FPSGAME` 和 `FPSGAMEEditor` 构建均返回 `Result: Succeeded`，记录于 `build-FPSGAME-01.log`、`build-FPSGAMEEditor-01.log`。构建前自动等待已有原生任务，Editor 阶段等待主工程后台 commandlet 释放模块，没有关闭其他进程。

运行引用已切至 V2 新材质，交付回执已落盘；未启动编辑器界面或游戏进行验收。
