# 赛博朋克卧室升级试点

> **已正式接入现有公寓，独立试点已退役。** 当前入口为 `open /Game/GameMaps/L_CyberpunkApartment`；下文保留当时的制作记录。正式接入记录见 `Docs/CyberpunkBedroom-Integration-20261024.md`。

当前迭代为 **V3 灯具、近景结构与材质修订**，详见
[卧室试点 V3 逐项记录](CyberpunkBedroom-PilotV3-20261024.md)。下文为 V1 历史记录；
当前模型、材质及用户要求的检查以 V3 记录为准，地图入口保持相同。

## V1 制作记录

已在 2026-10-24 12:20（UTC+8）完成后台制作、材质编译、资产导入及试点地图保存。
以当前公寓 V20 的靠客厅卧室 Bed2 为试点，原公寓保持原样。

本轮新增床头吸音饰面与通风格栅、供电脊和两盏暖色阅读灯；增加床尾搭毯、地毯、拖鞋、床头托盘与书杯、窗边软包凳、折叠布料、编织收纳篮、壁架以及书桌生活陈设。
灰黑主体搭配烟熏木、低饱和织物、铜色收边和少量青色指示灯。

共导入 16 个模型，装配 17 组静态陈设；新建 14 类独立 PBR 材质并复用项目纹理来源。
新阅读灯接入 `ApartmentAtmosphere` 的 Bed2 调度，保留原房间主灯；沿用现有床的模型、变换、碰撞与休息接触，以及储物柜、房门和电脑设备配置。

开发游戏控制台进入试点，出生点位于卧室内：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

返回原公寓：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

制作源：`SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/`。
可编辑模型源为 `BedroomPilot_Source.blend`；配置及作者链见同目录 `README.md`。
资产位于 `/Game/Props/CyberpunkBedroomPilot20261024`。
实际保存回执为 `assets_saved.json`、`installed.json`、`completed.json`，完成批次为 `assets-02` 与 `map-02`。

本轮未启动交互编辑器、游戏或 PIE，未生成预览渲染、截图或执行测试。
试点未加入默认地图、正式公寓重建链或打包烹饪清单；由用户体验后决定是否接入原公寓。
