# PKM 换弹手部精修 10

本轮依据用户指定视频 BV1jHeA6sEmj 的本地参考，重新制作普通与空仓换弹手部动作。参考取样和遮挡适配说明见 `reference_notes.md`。

## 动作调整

- 左手开盖前张指、接触盖尾后抬盖，松握退让，再用拇指和食指捏取余链。
- 左手回到前方支撑后，右手才离开握把；肩、肘、前臂随目标联动，腕部独立转向。
- 弹箱移动晚于右手接触，安装后先松指、侧退，再上抬捏链；配合当前手臂可达范围调整箱体路径。
- 链头随指尖持握路径移动，余链离座后保持侧挂；链节继续使用 Belt08 的定长约束和离线惯性运动。
- 放链、松手、抬掌、压盖分成不同阶段；空仓版关盖后另接拉机柄和回握。
- 手型按开手、开盖、捏链、握箱、掌压和拉柄分别制作，拇指与其他手指采用不同关节姿态。

## 交付文件

- `PKM_ReloadHands_Editable.blend`：可编辑源，保留原动作，新增 `PKM_Reload_Normal_HandReload10`、`PKM_Reload_Empty_HandReload10`。
- `Exports/A_PKM_reload.fbx`、`Exports/A_PKM_reload_empty.fbx`：60 Hz 骨骼动画，分别为 6.5 秒、7.5 秒。
- `author_reload.py`：本轮制作脚本；`authoring.json`：导出信息。
- `import_motion.py`：仅替换 `/Game/Weapons/PKMLowpoly20260922/Animations/` 内同名的两个动作；导入完成后生成 `motion_import.json`。
- `reference_detail_1.jpg`、`reference_detail_2.jpg`：用户参考视频的本地关键帧图，只作制作参考。

## 接入范围

沿用当前 PKM 私有骨架、Belt08 几何和 SectionFix09 材质映射。本轮不重新导入网格，不改静止骨架、蒙皮权重、枪体材质、待机、射击、配件及玩法结算。保持既有音效时间点和新旧弹箱切换时点。

两个动作已通过现有编辑器桥导入并保存，接入回执为 `motion_import.json`，桥输出为 `Saved/pkm10-import-02.txt`。没有执行原生编译，本轮仅更新动画资产。

视频遮挡的弹箱路径按当前模型进行三维适配。没有运行新的模型预览渲染或游戏测试；手部遮挡、抓握观感和穿插情况由用户实际试用后确认。
