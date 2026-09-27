# 药水动作、分品阶瓶型与恢复数值发布

## 本次范围

发布左手抓瓶、拔塞、饮用、抛空瓶与 recover 的运行源码；八种药水的四档瓶型映射、全品阶拾取、最终握点参数、基础值加最大资源百分比，以及旧物品实例的读档同步。所有角色等级均可使用。恢复量详见 [数值调整](../Items/potion-recovery-balance-20260927.md)。

共享文件按改动片段提取：角色药水组件／左手占用／菜单取消、手臂后置姿态层、库存接触结算、药水拾取和八个目录条目。并行的弓、手套、仓库、其他技能／近战调参及其他 SKILL 修订留在工作区。

共享 `FPSGAMECharacterActionPriority.cpp` 尚未入库，且依赖未发布的剑／魔法动作接口，本次不将整套并行动作系统一并发布。其中本轮添加的药水 include 与 Cancel 两处改动保存在 [接入补丁](potion-action-priority-integration-20260927.patch)，待动作优先级实现入库时合入；本机实际源码已含这两处改动。公开提交不宣称脱离这套并行依赖后可独立构建。

## 恢复素材和制作链

1. 恢复已合法持有的当前 V7 手模、各武器原生骨架、备用左臂与现有材质。AKM 大弹鼓／换弹提供抓握方法，脚本不替代这些输入或其使用许可。
2. `SourceAssets/PotionTierDesign20260926` 保存概念图、四张三视图、提示词和设计说明。图像留本机，提示词与说明公开。
3. `SourceAssets/PotionTiersBlender20260926/author_bottles.py` 读取 `design.json` 生成四套原创空心瓶、高模和三级 LOD、软木程序贴图、分件／完整瓶 FBX 和红蓝 GLB。`import_bottles.py` 后台导入并保存到 `/Game/Items/Consumables/PotionTiersV1`。
4. 恢复该目录的 16 个静态网格、Materials 与 Textures。`Content/ColdSteelData/potion_visuals.json` 供拾取与第一人称共用。各档 Shell／Liquid／Stopper／Closed 同原点，同档 HP/MP 只替换液体材质。
5. `SourceAssets/PotionUse20260926` 保留旧瓶拆分管线和两份可编辑动作参考。旧瓶 Blend 没有随最后两次纯 JSON 握点下移重烘焙，最终运行配置为 `potion_use_motion.json`：共用 HP 握姿，掌心 Y=-4.5，完整动作 2.10 s，1.46 s 结算，1.76 s 抛瓶，1.80–2.10 s recover。
6. 成功构建并重新加载档案后，现有药水的 useEffect 与 stats 在原 A/B 保存事务中同步；没有直接修改玩家二进制存档。当前目录的百分比为 15/20/25/30，无角色等级门槛。

## 公开与本机边界

Git 发布 C++、作者脚本、简洁设计／动作配置、提示词、文档与技能。Blend／FBX／GLB／UE 包、图片、贴图、原生手模和姿态输入、导入回执及生成的 manifest 继续留本机；源码克隆不等于完整游戏素材恢复。四档瓶造型和软木程序贴图为本次原创制作，原 V7 手模与旧瓶素材的来源规则仍适用。

## 废案归档

两份被当前编辑源替代的 Blender 自动备份归档至 `trash/potion-publication-20260927/SourceAssets/PotionUse20260926/`。逐文件原路径、去向、字节数和 SHA-256 见 [归档清单](potion-archive-20260927.json)，移动后散列一致。正式瓶源、设计图、动作参考、原瓶依赖和制作证据继续保留。

## 构建与检查边界

四档模型已后台导入保存；2026-09-26 的动作和瓶型构建成功记录见对应制作文档。2026-09-27 数值与旧档同步源码的完整 Editor 构建被弓模块编译错误阻断，日志 `Saved/BuildEditor/build-20260927-102316.log`；本次发布整理没有改弓或重新编译，不宣称旧药水的迁移已进入新 DLL。

本次仅进行用户要求的仓库整理、提交内容／敏感信息／文件大小检查和远端确认。未打开编辑器、运行游戏、测试、截图或渲染，效果交由用户测试。
