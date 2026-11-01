# 雷鸣／回响专属符文（2026-10-30）

两款均为雷神之锤专属特殊改造，使用现有 `rune` 槽，互相替换，不与同槽其他符文叠装。用户明确确认回响也限定雷神之锤。

## 外观

- 雷鸣 `lei_ming_rune`：中央折雷、两侧相向编结及收束菱印，蓝白流光。
- 回响 `hui_xiang_rune`：双回环、中央菱形主印与两枚留存印记，冰青流光。
- 作者源为可编辑矢量路径，1024×4096 遮罩、16位高度图、DirectX 法线和粗糙度图。笔画倒角与内槽真实参与法线着色；沿雷神之锤裸柄33.5厘米有效区双面等比例环绕，不换掉原木柄材质或增加钢条模型。
- 灰白浮雕图标使用 imagegen，以矢量主印及已认可金属框为参考，每款一张独立母图。源文件位于 `SourceAssets/ThunderGodHammer20261028/ExclusiveRunesV1/`。

## 玩法

雷鸣：每次有效命中目标独立进行50%判定，成功追加1层感电。普通三连、重击、冲刺、上挑、旋风、快速近战、贯雷投掷落地／召回和疾雷使用共用权威命中入口。普通武器攻击与原生落雷共用去重回执；落雷原有2层与概率追加层合并结算，不分两次越过阈值。附魔放电和电系施法的感电入口也携带符文概率。符文本身产生的次级过载伤害不反过来无限触发自身。

回响：以此符文武器触发5层感电过载时，过载眩晕延长0.25秒；原基准1.2秒变为1.45秒。过载后保留2层及当前感电计时，在同一状态事务中刷新图标。保留阈值5层，后续再累计3层即可再次过载。重击独立的1.5秒控制仍走原控制规则，与过载控制按既有最长时间口径处理，不相加。

攻击快照固定实际来源武器的符文；投掷、召回及附魔队列不从命中时别的手持武器借用效果。电系技能按施法时持有武器保存配置。其他武器／无回响时仍清空感电，其他概率和伤害公式不改。

## 接入

- `ThunderHammerRunes`：源武器配置、概率叠层及原生锤雷过载。
- `ColdSteelSkillRules / ColdSteelSkillModel`：捕获并消费权威命中快照。
- `LightningTypes / ColdSteelLightningModel`：电系技能与附魔链的概率、保留层数和过载时长快照。
- `CombatStatusFormula::AddElectrified`：默认保留0层；回响源指定2层。
- `WarhammerShockwave`：落雷只标记原生2层，交给共用命中入口合并符文判定。
- `FrostSwordRunes / ModularSwordVisual / MeleeRuneVisual`：专属兼容性、异步资源收集、持握／预览／远端／掉落的语义材质重建。
- 图标实际读取键为 `ue_thunder_god_hammer_blade_2_<id>`。目录选项只在资产导入保存后发布。

本批不执行自测、实战或双端联机验收；后台构建和实际资产保存不代表用户视觉验收。最终构建及导入回执保存在作者目录。

## 已落盘交付

- FPSGAMEEditor 后台构建完成，542 个构建动作，结果为 Succeeded。
- 无界面导入完成：两款符文各自的遮罩、法线、粗糙度、高度及正式图标，加上专用受光材质，共11个资产已保存；导入命令完成，0 errors。
- `thunder-god-hammer-gunsmith.json` 已登记两款特殊改造，限定雷神之锤，沿用符文槽互斥关系。
- 回执：`SourceAssets/ThunderGodHammer20261028/ExclusiveRunesV1/import_receipt.json`，`complete: true`，`runtime_tested: false`。
- 未启动编辑器窗口或游戏；外观、手持表现和实战效果交由用户测试。

## 雷鸣精修 V2（用户认可设计后接入）

用户认可 `SourceAssets/ThunderGodHammer20261028/LeiMingConceptV2/lei_ming_rune_design_v2.png`。雷鸣现行制作入口改为 `SourceAssets/ThunderGodHammer20261028/LeiMingRefineV2/`；回响继续沿用 ExclusiveRunesV1。早期雷鸣图标和制作源是历史版本，不再作为现行纹样导入源。

- 按定稿制作纵向折雷、菱形节点、双侧北欧编结、连续双股尾饰与尖端收束。可编辑 SVG 和路径作者源共同生成刻纹，交叉位置交替让出缝隙，避免交汇成平面色块。
- 1024×4096 长幅贴图，16位高度作者图；以厘米高度场生成 DirectX 法线，银边等效浅浮雕高度0.35毫米，内槽另刻低0.13毫米。高度表示表面法线制作口径，没有新增凸起钢板或额外高面数装饰网格。
- 按原柄局部厘米坐标双面贴合，横纵等比例。整枚纹样保留长宽比及留白，不为填满33.5厘米裸柄区域而拉长符号；原木纹与原厂端箍沿用原材质。
- 专用受光材质 `M_SilverRuneSurface_LeiMingRefineV2`。`RuneTexture` 的 R/G/B 分别保存覆盖、细槽流光、银纹；`RuneRoughness` 的 R/G/B/A 保存粗糙度、银面明度、金属度及细槽遮蔽。银纹覆盖恒定，蓝白能量只沿内槽流动，保留倒角反光和暗槽。
- 雷鸣独立选择新材质；回响与通用符文不进入新图案或材质分支。沿用既有异步资源配方与持握／预览／远端／掉落的统一材质选择入口。
- 已用 imagegen 更新正式金属框图标；输入为认可设计图与原图标框架，提示词保存为 `LeiMingRefineV2/icon_prompt.txt`。实际图标键仍为 `ue_thunder_god_hammer_blade_2_lei_ming_rune`。
- 后台导入已保存4张表面纹理、正式图标和专用材质，共6个资产；旧资产按精确路径复制保存在 `LeiMingRefineV2/PreviousAssets/`，未删除历史作者源。

本轮只修改雷鸣外观与图标，50%概率追加1层感电、5层过载和原生落雷规则保持当前实现。未执行游戏、截图或联机测试；构建结果另见本目录中的本轮回执。

本轮实际后台构建已完成：`LeiMingRefineV2/build-20261030-105152-receipt.json`，exit_code为0，20个构建动作，`UnrealEditor-FPSGAME.dll` 已链接。导入回执 `LeiMingRefineV2/import_receipt.json` 为 complete=true，共6个资产已保存。材质图重建过程中旧节点暂时断开的编译提示属于连接阶段；最终新根连接后执行材质重编译并保存，未追加运行验收。
