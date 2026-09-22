# 玩家全身、双套动画与动作修复发布

本轮发布保留第一人称手臂，加入独立第三人称 Manny 身体、简化动作、世界武器/配件、F6 基础页视角切换及眼部交互距离。随后修正站立/蹲起偏移、步频、蹲姿腿部 IK、皮肤槽绑定，以及动作复审确认的六项问题：阴影覆盖、施法副手枪显隐、双持砸击左右手、施法中断回位、翻越离手时机、双持装备过程。

## 源码与内容边界

- `Source/FPSGAME/Characters/FPSPlayerBody*`：全身动画、动作采样、相机、世界装备、外观与复制入口。
- Character、动作执行器、F6 与交互公共文件仅提交本轮必要片段。其他任务的枪械、地牢、动作优先级和性能面板改动保留本地。
- 本地共享源码已有尚未发布的新性能统计接口。此次暂存版本保留主线现有的无参数计数接口，不纳入新计时器、分对象统计和相关面板；工作目录中的并行统计代码保持不变。
- `Content/ColdSteelData/player_body.json`：独立身体路径、59 个动画映射与外观配置接口。当前 `outfits` 为空，没有随本轮提供可穿衣物或新头模。
- `SourceAssets/PlayerBody20260921`：自有皮肤 HLSL、模板来源及动画时长元数据、皮肤安装记录、历史 Fab 候选记录。候选记录不代表已下载或已接入头部。
- `Tools/PlayerBody`：保留制作/恢复及按需诊断工具，使用方式见其 README。

本机 UE 资源、Epic 模板原始网格/骨架/动画、武器资源、缓存、构建产物和日志不公开上传。本次 JSON 记录路径/帧数/时长，不含密集骨轨道或网格导出。原 Manny 和第一人称资源保持本机现状。

## 本机恢复顺序

1. 使用本机已有合法 UE 5.8 模板内容，恢复 `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple` 及其 Skeleton、材质和依赖；沿用工程已有第一人称装备资产。Git 克隆不是完整可运行资源包。
2. 普通 Python 运行 `Tools/PlayerBody/prepare_manny_assets.py`，从脚本指定的本机引擎模板目录补缺失动画。它只复制动画，不执行 Manny Mesh/Skeleton 的完整迁移，也不覆盖现有动画。更换机器时先调整引擎路径。
3. 通过项目 MCP 桥在正确编辑器执行 `import_manny_assets.py`，注册动画并记录来源元数据。
4. 通过同一桥执行 `install_body_skin.py`，生成 `/Game/Characters/Mannequins/PlayerBodySkin` 的独立 Mesh、材质和皮下散射配置，并更新 `player_body.json`。脚本会写回材质槽并保存身体副本。
5. 必要的原生构建使用 `Tools/Build/Build-Editor.ps1`。按用户明确授权决定是否运行诊断工具；恢复本身不启动 PIE。

## 归档与知识沉淀

三个退役脚本放在本机 `trash/player-body-retired-20260922/Tools/PlayerBody/`：一次性热编译、旧地图复现启动器、重复编辑器状态读取。原路径、目标路径、大小、SHA-256、退役原因和替代项见 [归档清单](player-body-retired-manifest-20260922.json)。已按项目规则进行路径范围确认和移动后散列核对。归档实体不上传 Git。

可复用经验进入 [玩家全身表现](../../skills/ue5-cpp-gameplay/references/player-world-body.md)，由 C++ 玩法及手臂动画技能链接，个人技能与工程镜像同步本轮新增内容。历史审计和修复记录保留，不作为废案移走。

## 构建与验证范围

六项修复所在的本机共享工程已在 `Saved/BuildEditor/build-20260922-183745.log` 记录 `Result: Succeeded`，最终调用显示目标已是最新；对应 DLL 时间为 2026-09-22 18:36:40。此证据仅属于当时完整共享宿主，不把它表述为此次剥离其他任务改动后的独立 Git 树已重新构建。

此次整理按用户要求执行提交范围、差异、文件大小、敏感信息、许可边界和归档完整性检查。不启动游戏、不增加动作视觉验收。待用户自行测试动作表现；联机权威流程、真实换装资产、面部建模/动画和布料仍属于后续开发。
