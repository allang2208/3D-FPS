# 线圈：雷神之锤专属特殊握柄

## 身份与数值

- 武器 `ue_thunder_god_hammer`，握柄槽 `grip`，改造 ID `coil_grip`，特殊改造 `special`。
- 重击蓄力速度+15%，攻击速度+10%；通过现有配件数值聚合，不另写人物属性乘算。
- 与静电场同属握柄槽，两者互斥，不改变静电场配置或外观。

## 放电路径

| 场景 | 触发 |
| --- | --- |
| 蓄满普通重击释放 | 玩家位置半径30米，随机敌人，1道闪电 |
| 贯雷投出 | 场上锤子位置半径30米，立即1次，然后每6秒1次 |
| 疾雷落雷 | 实际落点半径10米，两道独立随机闪电 |
| 疾雷+震霆 | 原始及每道后续落雷分别触发两道闪电，沿原0.25秒间隔 |
| 贯雷切换当前武器 | 装备栏中保留该武器则驻场继续 |
| 贯雷开始召回、移出装备栏、销毁、换图、玩家死亡 | 停止新的定时放电 |

所有选敌沿用敌对过滤和场景遮挡规则；多个碰撞组件不会增加某个目标的抽中权重。无有效目标时不产生空击。疾雷的两道闪电独立选敌，可以命中同一个仍存活的敌人；第一道击杀后，第二道重新从存活目标中选取。

在重击提交时，以 `max(10, LightningProgress().Level)` 调用现有 `LightningStats(..., false)` 并保存快照；不修改玩家原技能等级。初次搜索半径由握柄规定，后续传导沿用该等级闪电的目标数、传导距离与衰减。延时落雷与驻场沿用该次释放锁定的武器数值和符文，不借用切换后的其他武器。

复用武器自动闪电组件：不扣额外魔法，不占主动闪电冷却/动作，不训练主动闪电；正常结算击杀收益。雷神之锤原生雷击规则为2层感电，叠加雷鸣的概率额外层数、回响的过载规则及雷吸的魔法激励。放电不再生成锤击波，因此不会递归触发更多线圈或震霆。

## 模型与材质

- 三视设计：`Design/Coil_ThreeViews.png`；草稿源 `Coil_DesignDraft.blend`。
- 图像生成服务因 violence 分类拒绝了游戏配件概念请求；未尝试规避或调用其他图像 API。设计图由 Blender 按真实尺寸直接制作，不是游戏截图。
- 结构：六段绝缘握持、连续铜绕组、闭合钛合金保护肋、嵌入式导光槽和铜接点。
- 约490mm总长；握持区约31mm直径，原装两端连接面、面角法线和UV直接保留；运行偏移继续为原厂+40.5cm。
- 游戏源导出 **101,804 三角形**；无百万面游戏高模。`Coil_Design.blend` 为可编辑分件源，`Coil_Editable.blend` 同时保存运行时合并网格；FBX与GLB在 `Export/`。
- Rubber / Titanium / Copper 三组2048² PBR，共9张图；另保留16位高度源。实际微纹、拉丝和细划痕生成切线空间法线，UE使用Normalmap压缩、关闭sRGB并翻转绿通道。
- 纳米几何启用；回退目标为15%。正式UE几何和保存数量以 `import_receipt.json` 为准。
- 独立灰阶制作场景 `Coil_Icon.blend`；生产图标 `coil_grip_framed.png`，运行键 `ue_thunder_god_hammer_grip_coil_grip`，按实际模型制作并保存Texture2D。

## 源码入口

- `Production/ThunderHammerCoil.*`：限定身份、等级与武器快照、释放入口。
- `ProductionBluntAuthority.cpp` / `ProductionToolComponent.cpp`：服务器与单机蓄满重击提交。
- `WarhammerShockwave.cpp`：疾雷实际落点，包括震霆派生波。
- `ThunderHammerThrown.*` / `ThunderHammerRecall.cpp`：6秒定时器与召回生命周期。
- `Weapons/FPSMeleeLightningComponent.*`：复用自动闪电结算，线圈独立随机初次选敌及有限技能传导。
- `GunsmithModificationTier.h`：特殊改造分类。

## 制作与交付边界

作者脚本、贴图、导出、图标、必要后台编译与资产接入属于本次开发。`build_receipt.json`、`import_receipt.json`、`publication_receipt.json` 分别记录编译、保存资产与配置发布，不能互相代替。

未启动UE编辑器、游戏、性能测试或联机验收；游戏内外观、选敌及数值交由用户测试。三视图属于用户明确请求的设计交付。
