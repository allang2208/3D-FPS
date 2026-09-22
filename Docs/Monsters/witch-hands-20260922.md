# 巫婆 Hands08：双手握持方向

用户反馈两只手的细节反向。本次沿用 Seams07 / Drape07 的网格和衣物，只调整握持手指及道具挂点。

## 原因与修改

- 原右手抓握用了与解剖掌心相反的弯曲符号；原运行时左右手统一取负叉积，又把右手药瓶置于手背侧。按左右手参考骨架分别定义掌心，并处理 FBX 的 Y 反射。
- 左手法杖以实际导出 FBX 的握持截面制作手指弯曲。拇指使用跟随掌指骨的局部关节轴，不再与其余四指共用世界弯曲轴；调整拇指对掌与小指接触。
- 右手以瓶肩截面制作抓握；分别拟合五指，不再用一组角度强行包住粗细不同的瓶口和瓶身。同步修改道具在手骨上的挂点。
- 只重写 30 根手指骨的旋转轨道。手腕、肘部、身体动作、原有单位比例、网格、权重、材质和布料保持原输入。投掷维持错开的松指/收指及 0.75 秒脱手合同。

握持作者坐标以 wrist→middle MCP 为 Along、pinky MCP→index MCP 为 Across。Blender 左掌为 +Cross，右掌为 -Cross；UE 中符号相反。运行时沿手掌偏移 8.5 cm；左掌外偏 5.0 cm、法杖握持高度 92 cm，右掌外偏 6.7 cm、瓶肩握持高度 11.8 cm。

## 交付

- 作者脚本：`Tools/WitchRebuilt/author_hands08.py`。
- 导入脚本：`Tools/WitchRebuilt/import_hands08.py`，仅导入八个动作，不重建模型或布料。
- 可编辑源：`SourceAssets/WitchRebuilt20260921/Authoring/WitchRebuilt_<Role>.blend`。
- 导出：同目录树 `Delivery/A_WitchRebuilt_<Role>.fbx`。
- 引擎目标：`/Game/Monsters/WitchRebuilt/Animations/A_WitchRebuilt_<Role>`。
- 修改前源、FBX、动画资产及挂点源码：`SourceAssets/WitchRebuilt20260921/Revision08/Before/`。
- 作者拟合参数：`Revision08/hands_authoring.json`。指骨与简化截面的距离用于制作，不代表蒙皮接触或实机画面验收。

Idle、Walk、CastPoison、Hit、TurnLeft、TurnRight、ThrowPoisonBottle、DeathBackward 均使用同一修订抓握。

## 接入状态

常规 Editor 构建成功：`Saved/BuildEditor/build-20260922-171248.log`。已正常重开 UE，八个动作均已导入并保存；调用记录为 `Revision08/import08_01.txt`，保存回执位于 `Revision08/ue_asset_result.json`。编辑器保持打开。

遵照用户规则，本次不启动 PIE、不新增渲染或运行验收。完成接入后由用户在 F6 原巫婆入口重新生成，观察两手、走路与投掷过程。
