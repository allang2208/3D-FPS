# 201 枪身表面及接头重整（SurfaceReform42）

用户本轮反馈：脚架顶部衔接不自然，枪身左右两侧的平面、槽口和倒角仍有明显毛躁起伏，扳机护圈需要再按参考调整。

## 依据与修正范围

读取 `ue5-weapon-workflow`、`asset-model-workflow` 及其 `generated-rifle-refinement` / `weapon-finish` 等经验。H39 的局部拟合保留了原凹槽边缘，而用户截图与旧制作图中仍可见边缘扭曲；S41 的金属反射使这类不平更明显。调整粗糙度不足以替代拓扑修整。

本轮依据两张已有用户参考 `Surface32/References/User_Left.png`、`User_Right.png`。左右侧结构不同，不做镜像复制：一侧为两处上矩形凹槽及下方折线凹槽，另一侧为上矩形凹槽和两道平直加强筋。

1. 机匣外侧粗糙区域作有限范围裁切，保留原中心主体及接口，重建对应外板、凹槽槽壁、有底内面、规则螺钉和小倒角；前肩与护木交界同样整理。重建表面采用自己的 UV 与角点法线，材料直接复用当前 S41 金属基准，避免把旧凹凸图重新叠回新面。
2. 扳机护圈由厚矩形改为倾斜前缘、轻微弧形底部、较窄后回边。连接座继续进入已有机匣腹部；扳机为连续弧线并与原生根部相接。仍在 idle 下制作再逆变换，保留原动作轨道和扳机槽名。
3. 脚架底座使用圆角鞍座及连续轴部外形。支腿上端按各自局部原点制作轴眼和过渡套，替换粗糙头部，保留下段与脚掌。没有整体移动、缩放脚架，也没有改变部署转轴。

## 制作与保存

所有文件位于 `SourceAssets/LMG20120260927/SurfaceReform42`。编辑源为 `LMG201_SurfaceReform42.blend`，制作脚本 `model.py`，导入保存脚本 `install.py`。`capture.json` 是修改前资产记录，`Before` 保存本轮覆盖目标的原始字节，`delivery.json` 记录实际落盘结果。

2026-09-29 后台保存完成：`delivery.json.status` 为 `current_s42_saved`，四个目标保存回执齐全，commandlet 退出码 0。完整保存资产的 FBX 已输出到 `Exports/After_*.fbx`。本次在用户明确授权关闭仍运行的游戏窗口后执行；未自动重启编辑器或游戏。

四个目标：

- `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`
- `/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodBase`
- `/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegA`
- `/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegB`

重建零件随完整 S41 局部组件集合替换，避免共享 A40 材质槽的其它底座、导轨及接头丢失。F37_Interior 在当前编辑源中只用于 Receiver；本轮一并替换该接收器内面槽，避免历史重导入叠加同一内面。其它零件及活动盖保留实际运行资产内容。

静态件关闭本件导入与构建的 `remove_degenerates`，避免先前 H39 出现的微小有效倒角丢面；保留法线、重建切线，材质绑定按名称映射。新表面沿用已有 S41 材质，因此无需重写整套湿润表或创建共享材质。

## 交付边界

后台制作与导入，不启动 UE 编辑器或游戏。源文件保存、FBX 导出与正式资产保存分开记录；只有 `delivery.json.status == current_s42_saved` 才代表本轮四个目标均已保存。

本轮不追加渲染、自测或实机验收，未取得用户外观认可。几何形状依据可见参考作局部优化，不宣称整枪 1:1 还原或所有历史问题已通过验收。
