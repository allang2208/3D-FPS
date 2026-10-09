# 无面接待员：三视图候选 V01

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

日期：2026-10-07

## 本次交付
- M_FacelessReceptionist_ThreeView_v01_CoveredStudy.png：内置 image_gen 生成的正面、左侧、背面设计图。
- generation_prompts.json：完整提示词及生成状态。

## 设计
沿用项目 M-07／M-09 的灰白蜡质皮肤、冷蓝血管与低饱和生物实验体风格。
成人女性体型、正常双足人形关节、完整五指与脚掌，保留胸腰胯整体轮廓。
头部为连续封闭的皮肤椭圆体，不设眼、鼻、嘴、耳或头发。编号未分配。
计划基准身高约 175 cm，属于设计起点，尚未制作真实三维尺寸。

## 与原请求的差异
用户要求 Meshy 先生成无衣物主体，接待员衣物随后独立制作。
两次无衣／中性雕塑基体生成均被图像工具安全系统以 sexual 类别拦截，没有获得可交付图。
本次可交付图因此保留一件不透明灰色临时打底服，仅用于体型参考，不是最终接待员服装，也不是纯身体图。
若把当前图直接交给 Meshy，打底服可能会被生成进主体，不能保证靠提示词把它去除。
当前只交付三视图设计候选，不代用户调用 Meshy；真正多视图生成时需准备独立视角输入。此图是生成式设计，不是实际模型的精确投影。

## 后续骨架与衣物
遵循用户指定女僵尸供体方向。项目 Tools/NurseZombie/integrate_nurse.py 中登记：
- 模型：/Game/ZombieFemale/Asset/Meshes/ZombieFemale_NurseOutfit
- 待机源：/Game/ZombieFemale/Asset/Animations/ANMS_ZombieFemaleIdle05
- 行走源：/Game/ZombieFemale/Asset/Animations/ANMS_ZombieFemaleWalk01Forward
- 攻击源：/Game/ZombieFemale/Asset/Animations/ANMS_ZombieFemaleAttackForward05
- 项目派生片段：/Game/Monsters/NurseZombie/A_Nurse_idle、A_Nurse_walk、A_Nurse_attack

以上是现有接入脚本记录，不是本次加载蓝图后的资产核验。待实际 Meshy 模型到位后，按父链与绑定姿态决定沿用有效 Meshy 蒙皮并重定向，或采用女僵尸骨架重新适配；不凭图片承诺可以直接共享骨架。
接待员衣物独立建模并适配最终身体与骨架，保留身体主体；本轮未制作衣物、模型、蒙皮或动画。

## 依据
已读取 ue5-monster-workflow、asset-model-workflow、imagegen；按需读取 infected-surface-style、meshy-humanoid 参考。
造型参考：
- SourceAssets/BlindSupplicantM07Meshy20261001/Inputs/M07_original_concept.png
- SourceAssets/HangingBellM09Concept20261003/Reference/M09_UserReference.png
另参考 SourceAssets/BoundCongregateConcept20261006/v05/generation_prompt.txt 与 v06/MeshyBody/README.txt 的材质及衣物分离约定。

本次仅资料读取与生成式三视图制作；未打开 UE、未修改运行资产、未测试或验收。造型由用户确认。
