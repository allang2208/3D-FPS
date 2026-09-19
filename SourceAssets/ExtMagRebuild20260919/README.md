# 三枪扩容弹匣修订（2026-09-19）

本轮由用户反馈 M4、AKM、QBZ-191 的外形/材质和 M4 抓握不达标而开展。

## 排查依据

- 前版 M4/QBZ 弧管脚本按角度排序切环顶点，未沿真实边连接；多环或凹轮廓会产生错误连接。旧回执还记录 M4 42 条、QBZ 58 条非流形边，不能用其人为构造的 seam_gap=0 认定整个网格无问题。
- 前版新增管面没有写 UV，绑定宿主图集无法自动补出合理纹理；AKM 仍是旧的渐入拉伸版本。
- 源动作 M4 普通换弹帧 76 的左手在弹匣侧面，末节骨点距表面约 21–25 mm。骨点距离仅是定位依据，不是手套表面接触判定。排查图为 diagnosis_grip_*.png。
- 底板/肋纹的顶点密度会偏置中心线拟合；新脚本用真实水平截面边交点的外轮廓中心拟合，并保留原厂每个角点的法线。

## 制作与接入

- build_magazines.py：从三枪自己的 FBX 提取弹匣。保留真实切边连接，沿曲线共享边生成延长段；AKM 延续纵向加强筋，聚合物件延续纵向轮廓并补浅横肋。保留上段/插接段、原厂 UV 和法线，新增面采样原厂局部 UV；处理退化的 UV 条带。
- 三枪的 FBX 与可编辑源分别位于 FBX/、M4_ExtMag_Editable.blend、AKM_ExtMag_Editable.blend、QBZ_ExtMag_Editable.blend。切点、延长量见 build_receipt.json。
- author_m4_grip.py：从现用普通/空仓源动作制作扩容弹匣专用动作，保留武器、弹匣、手指原有轨道关系与源时长；在取新匣/插入窗口内调整整手位置，用肩肘腕两段链解算衔接前臂。非扩容与弹鼓动作不换。
- install_assets.py：沿用各枪当前 SkeletalMesh 弹匣槽的材质，导入到 /Game/Weapons/ExtMagRebuild20260919/Release。使用传统 FBX 导入器并指定宿主骨架，避免默认 Interchange 创建另一副骨架。共享编辑器时优先在编辑器内执行；外部进程不覆盖被编辑器加载的包。
- FPSGAMECharacter.cpp 按 ext_mag 选择 A_M4_ExtMagGrip_reload / reload_empty；M4DrumVisual.cpp 选择三把枪各自的 Release 网格，保持原厂弹匣骨骼挂接和座位变换。
- make_icons.py 用当前实际网格生成三枪各自的 UI 图标；图标采用中性展示材质，不充当 UE 材质验收图。
- gunsmith.json 描述按枪型分别注明聚合物/钢制，不再声称三枪都有观察窗。保留 +10 发、reload_mult=1.25、ads_percent=0.05。物品 ID 与存档字段不变。
- DefaultGame.ini 增加修订资产目录的打包包含项。

## 来源与交付边界

模型沿用 M4HK416Replica20260910 和 PhantomRearGripIntegration20260913 的各枪原厂弹匣；手臂与动作沿用 M4TacticalToss20260910 / M4SlapImpact20260910。复用既有来源许可，未新增第三方模型或公开发布源资产。

本轮排查包括源几何/代码读取及针对 M4 抓握的源模型画面。安装回执、必要编译结果和游戏验收分别记录。未运行 PIE、实机换弹、存档回归或打包测试；实机外形、材质与手部接触仍交由用户测试，不能用制作/导入回执宣称视觉验收通过。原生改动需由重启后的编辑器加载。

旧版 ExtMagUniversal20260917 以及本目录 Release 之外的中间导入资产不是当前交付引用，保留以便回溯，不恢复为正式源。

## 本轮交付记录

- 三个 Release 网格和两段宿主骨架换弹动画已导入并保存，见 install_receipt.json。主项目命令行启动遇到 AutoFootstep 默认对象类冲突，故使用 Saved/ExtMagAuthoringHost 仅启用资产制作插件、通过 Content 目录联接完成导入；没有修改 AutoFootstep 或关闭用户编辑器。
- 最终运行时引用已切换到 Release；必要原生编译成功，见 build_editor_final.log（FPSGAMECharacter.cpp、M4DrumVisual.cpp）。
- 导入记录仍提示 QBZ 网格存在部分近零切线/副法线（容差 1E-4）。资产已保存，但此项可能影响局部法线贴图表现，不能宣称材质视觉已全部达标。
- 未进行游戏测试或实机验收。用户重启 UE 后自行测试三枪扩容弹匣与 M4 普通/空仓换弹。