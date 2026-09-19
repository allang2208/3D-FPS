# 弹匣口、普通 M4 抓握与材质绑定修复

## 本轮用户反馈与处理

1. AKM 所指缺口在弹匣口，上一轮下段补面没有解决此处。原 FBX 的弹匣对象只有一个有面的材质槽，没有因槽筛选漏掉的口部零件；原口部为开放薄壳。本轮沿实际非对称口缘补 1 mm 内收边、11 mm 下沉内壁及托弹板，保留上端原有外轮廓、下段曲率、纹路、UV0 和安装坐标。没有把口部做成平盖。源 `AKM_ExtMag_Mouth_Editable.blend`，重建入口 `author_mouth.py`。
2. M4 普通弹匣与扩容弹匣共用未改变的上段接触面。`ReloadPressed` 将两者都接到当前 `ExtMagContact20260919` 的 M4 普通/空仓包握动作。保留甩匣、取弹、插入和空仓拍击时序；弹鼓仍用独立动作，QBZ/AKM 不进入 M4 分支。可编辑动作源仍在 `ExtMagContact20260919/A_M4_ExtContact_reload*.blend`。
3. 三枪扩容弹匣实际均绑定 `/Engine/EngineMaterials/WorldGridMaterial`，见 `current_bindings.json`。旧脚本把 UE 结构数组元素当作引用写入，修改未落到数组，旧回执却记录了计划目标材质。修复为取出槽结构、修改、写回数组、设置资源并保存；同步修正两套旧作者导入脚本，避免重建时复发。

## 当前资源

统一目录 `/Game/Weapons/MagazineMouthFinish20260919`，已切换 `M4DrumVisual.cpp` 并加入打包目录：

- `SM_ExtMag_M440`：实际绑定 M4 的 `Magazine_Light_001`。
- `SM_ExtMag_QBZ40`：实际绑定 QBZ 的 `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`。
- `SM_ExtMag_AKM40_Mouth`：原壳实际绑定 AKM `M_AKM_Soviet_PBR`；新增口部用其独立副本 `M_AKM_MagazineMouth`，仅取钢质图块，新增面不用无关的结构法线/AO 图块。

M4/QBZ 几何沿用上一轮导出；AKM 仅补口部。未更改共享枪身材料。`install.py` 是本轮导入入口；`install_receipt.json` 记录资源实际槽值而非目标变量。

`prepare_finish.py`、`finish_profiles.json` 是排查过程的调色候选，**未应用**。发现默认材质绑定错误后撤销调色方向，优先恢复正确 PBR 材质，不能把候选参数当作本轮实际效果。

个人及工程镜像的 `weapon-finish.md`、`extmag-lengthening.md` 已同步修正：原槽只说明来源；实际绑定、UV/通道对应与视觉匹配分别判断。撤销历史“天然统一/定稿”结论，并记录口部问题与普通/扩容抓握的适用范围。

## 交付范围

完成源模型排查、制作、导出、UE 导入和必要 C++ 构建。构建成功记录在 `build.log`；未启动 PIE、游戏回归或验收渲染。`mouth_before.png` 仅为定位原口部缺失的源模型诊断图，不是修改后效果证明。用户重启编辑器加载新模块后自行测试。
