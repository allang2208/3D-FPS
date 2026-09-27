# 棱脊穿甲刃：收窄剑根 V2

2026-09-27，用户反馈棱脊穿甲刃靠近握柄/护手的衔接部分过宽，要求继续优化。本轮只修改该剑身的根部过渡及其菜单图标，已导入保存。

## 造型修改

原版从 V5 原装刃复制了整个 Z≤10.5 cm 区域，之后再用 7.5 cm 距离缓慢收窄，因此根部约 6.3 cm 的宽肩一直延伸到约 Z=12 cm，而主体只有约 3.8 cm 宽。

V2 按真实 V 形安装面 `z=.058+.95*abs(x)` 控制过渡，仅保留接口及沿 Z 方向 1.5 mm 的支承带；其外用 2.5 cm 过渡尽早收窄，外缘约 Z=11.5 cm 完成收肩，替代原版到 Z=18 cm 才完成的长宽肩。目标半宽在 Z=9.5/11/18 cm 分别为 2.0/1.95/1.9 cm，沿剑身继续渐收至原长尖。

保留实际接口位置与面角属性、原 UV/PBR、12 mm 中脊厚度、剑尖位置和攻击采样合同。护手、整颗蓝宝石、握柄和配重均沿用现有资产。由最终表面生成角度加权法线，安装带使用原法线；UE 保留作者法线并重建 MikkTSpace 切线。

第三段突刺伤害 +40%、第三段突刺韧性伤害 +40%、物理防御穿透 +10%、基础伤害 −10% 均未修改；本轮没有写入玩法目录、模块目录或 C++。

## 保存范围

- 可编辑源：`Highland_RidgePiercer_RootV2_Editable.blend`。
- 图标源：`Highland_RidgePiercer_RootV2_MenuIcon_Editable.blend`。
- 制作脚本：`author_ridge_piercer_root_v2.py`，制作参数 `authoring.json`。
- FBX：`Export/SM_Highland_Blade_RidgePiercer_V1.fbx`，保留原对象名称以维持运行引用。
- 原位更新 UE 资产：`/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/SM_Highland_Blade_RidgePiercer_V1`。
- 重做实际新模型的 1024×1024 透明左向菜单图标，保存运行 PNG 与同名 UE Texture。
- 导入入口：`import_ridge_piercer_root_v2.py`；原资产与图标保存在 `Before/<时间>/`。

通过现有编辑器互斥桥接入，首次因 PIE 中无法保存而停止，随后结束游玩并完成重导入；完成标记 `HIGHLAND_RIDGE_PIERCER_ROOT_V2_INSTALLED` 见 `import-editor-03.txt`，逐资产保存回执为 `import_receipt.json`。没有打开第二个编辑器、关闭或重启编辑器，也没有重新启动游戏。本次无需原生编译，未运行测试或验收渲染，由用户测试。

初版来源与许可沿用 [棱脊穿甲刃记录](../RidgePiercer20260927/README.md)。初版作者/导入脚本为历史版本；后续维护以本目录为当前剑身几何入口。
