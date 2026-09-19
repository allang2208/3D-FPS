# 后握把接入与逐枪材质统一（2026-09-13）

M4 均衡后握把的后续衔接件修订位于 [BalancedRearGripM4Seam20260914](../BalancedRearGripM4Seam20260914/README.md)，本文件下文保留此前制作记录。当前 M4 修订的导入、编译状态以该目录为准。

用户认可均衡后握把 A（seed 91703），随后要求检查游戏接入及按照最新 SKILL 与枪身统一材质。

## 完成内容

- 均衡 A 接入 M4、AKM、QBZ-191 的 reargrip 选项，ID `balanced_reargrip`，`recoil_mult=0.9`、`shake_mult=0.9`。没有额外 ADS 或腰射惩罚。
- 同时修正此前幻影后握把跨枪共用生成材质、连接件共用常量材质的问题。
- 六个运行网格位于 `/Game/Weapons/RearGripFinish20260913/<family>/<balanced|phantom>/SM_<Balanced|Phantom>RearGrip`。旧资产保留。
- `PhantomRearGripVisual.cpp` 的共同装配入口已切换新路径，角色、独立展示、图标和掉落沿用该入口；保留并行任务的稳固防滑后握把分支。打包目录已添加。
- 均衡握把按各枪原厂安装头定位，并保留专用连接件；幻影沿用此前 ReceiverFit 几何。

## 材质依据

| 枪型 | 当前枪身参考 | 制作方式 |
| --- | --- | --- |
| M4 | M4InfimaV3/Body_001 | 机匣干净区域贴图，12×5 cm 涂层 UV 尺度，保留 sRGB Shininess、SpecularColor=.2 与 MF_PhongToMetalRoughness 转换 |
| AKM | AKMIntegration/SovietFab/M_AKM_Soviet_PBR | Soviet 机匣金属区域的 BaseColor/Metallic/Roughness，12×2.5 cm 尺度 |
| QBZ191 | Attachments20260913/Materials/M_QBZ191_Unified_M_QBZ191_Wear_Body_metal | 复用当前机匣程序化涂层与磨损，在配件自身 UV1 烘焙 BaseColor/ORM，保留 .32 涂层混合与 .42 粗糙度输入 |

不把整枪 UV 图集套到新网格。UV0 保留原结构纹理，UV1 用于金属涂层；禁止自动光照 UV，导入角点色遮罩与原法线/切线。均衡实心握持面、幻影前缘防滑区保留聚合物；金属框架和连接件按枪型处理。原生成材质没有独立结构 Normal/AO 贴图，本次未虚构新增此类贴图。

## 制作文件

- `author_assets.py`：几何适配、区域遮罩、涂层 UV，六个子目录保留 FBX 和 Editable.blend。
- `finalize_uv.py`：将旧幻影多余 UV 层移除，保留原 UV0，把新增涂层固定在 UV1。
- `bake_qbz.py`、`QBZ191_RearGripCoating_Editable.blend`：QBZ 涂层烘焙与可编辑源。
- `import_finish.py`、`installed.json`：导入与实际新资产绑定路径。
- `before.json`、`after.json`：本次用户要求的材质读取记录。

## 实际完成范围

六个网格逐槽读回正确枪型专用材质，均为两套 UV，并存在导入的顶点色；主体材质包含区域遮罩及 UV1 涂层采样。原枪身材质没有修改。编辑器构建 `9131653` 成功，见 `build.log`。

导入和读回 Python 完成；命令行进程返回 1 来自工程已有的 GameFeatureData 资产管理器配置错误，不能记作无错误命令行运行。没有进行游戏运行、存档回归或新材质画面对比；由用户启动编辑器测试。已打开的编辑器需要重新启动以加载新的原生模块。

## M4 均衡后握把前移修正

根据用户反馈，握把主体沿枪口方向（源坐标 -Y）前移 5 mm，原厂连接座保持不动。已重新导入当前运行资产，保留材质、UV、角点色和数值。可编辑源、FBX、导入脚本及修改前资产备份见 `M4/balanced/ForwardFit`；authoring.json 已指向修正版。没有启动游戏或渲染，贴合效果由用户测试。导入脚本完成；命令行仍有既有 GameFeatureData 配置及 8000 端口占用错误。
