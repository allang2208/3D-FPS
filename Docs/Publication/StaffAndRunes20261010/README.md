# 法杖与近战配件整理发布

本次公开法杖动作占用、施法者强化归属和服务端施法快照、动态预览时钟、配件介绍标准，以及此前寒晶精神迸发、专属配重、延锋刃和急速符文的原创代码与制作配方。

## 回查与补漏

- 食水／药剂使用期间，法杖组件拒绝新施法和挥击；照明开关不抢占使用动作。
- 八个法术数据入口以档案绑定的施法者读取强化。服务器保存本次扣费快照，再消耗旧链式强化；释放和取消与本地口径一致，陨星成功释放也获得下一次强化。
- 法杖预览世界由控件推进时间，关闭引擎自动推进；动态法杖使用 30 Hz 捕获上限。未测量实际帧率。
- 法杖 20 款配件使用直接属性和 `special_effects`，共享详情／总览／浮窗字段。此次回查补去近战浮窗残留的分段、重击和附加伤害拆分；原生法杖不再重复显示旧介绍。
- V41 安装器不再依赖被否定的 V40 回执，旧材质入口不再自动恢复磨损方案。
- 长杖目录生成器清除旧合同中的装备稀有度字段，避免重建目录时恢复已取消的稀有度。

## 当前恢复链

- 白水晶：`QuartzPolishV41`，制作仍需本机 `QuartzOpticsV36` 作者模型及其 V35 几何来源。稳定世界路径为 `QuartzAimV22/Materials/M_Staff_QuartzDenseV22`，UI 路径为 `/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`。
- 元素晶体：`ElementPolishV42` 的表面配方；冰、熔岩、风暴沿 `ElementHeadsV38`，翠灵沿 `ElementHeadsV37`。V37/V38 并非废案。
- 杖冠、符纹、握柄／尾饰分别恢复 `CrownRefinement20261009`、`RuneRefinement20261009`、`GripTailRefinement20261009`；恢复 `staff-tail-dynamics.json` 后使用同一装配入口。
- 全杖重导入口 `BarkRebuildV21/import_model.py` 保留各活动部件；先恢复合法本机输入并按分支作者、安装器生成有效回执，再执行旧整杖入口。不能把缺失本机回执的公共目录视为已恢复资产。
- 急速符文保持攻击速度 +10% 与黄色三维光效。现用符文图标母图在本机 `RuneSymbolIcons20261009/Masters`；生成图、PNG 和 UE 贴图不在公开仓库。此前带剑刃的黄色图标方案已归档。
- 近战文案遵守 [统一详情标准](../../../skills/ue5-weapon-workflow/references/attachment-detail-presentation.md)；法杖文案源为 `SourceAssets/ApprenticeStaff20260927/attachment_copy.py`。

## 归档边界

[逐文件清单](archive-manifest.json) 记录 162 份文件的原路径、trash 路径、大小与 SHA-256：否定的 V39 轮廓方案、V40 磨损方案、已替换的带剑刃急速图标方案及旧符文图标备份。全部位于本机 `trash/staff-runes-retired-20261010/`，不公开原始资产。

现有编辑器的远程执行桥未连接，无法确认包的加载和外部引用状态，因此 [47 个旧 UE 包](retained-packages.json) 保留原位，未强移或删除。不得据本次源文件归档声称这些包已清除；待编辑器关闭或桥恢复后，应先确认正式资产无依赖，再按同一清单归档。

## 公开范围与验证

只提交明确归属本次的原创 C++、JSON 配置、Python／PowerShell 配方、HLSL／SVG 和说明。网格、贴图、Blend/FBX、密集采样、素材包、导入回执、构建产物和未审核再分发许可的原始资源留本机。混合了其他工作区改动的 C++ 文件按差异块提交，保留其他修改。

此前 Editor 构建成功；本次补漏后的 `FPSGAME Win64 Development` 也构建成功，日志位于本机 `Saved/StaffPublication20261010/build-game.log`。完成源码／配置、归档散列和暂存内容检查，不启动游戏、PIE 或视觉验收。公共源码切片依赖项目既有合法本机资产及生成数据，不声称远端是完整可运行资源包。
