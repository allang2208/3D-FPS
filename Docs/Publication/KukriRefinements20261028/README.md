# 弯刀霜鸦定稿与联机回查增量

2026-10-28，工程 `D:/FPS3D/FPSGAME`，发布到 `allang2208/3D-FPS` 的 `main`。本次延续 [前轮弯刀发布](../KukriMods20261028/README.md)，整理后续鹰头、刀面符文、HUD、稀有度和联机修复；不包含其他任务的武器、动作或动画改动。

## 当前定稿

- 霜鸦头像使用 [CrystalCrownV3](../../../SourceAssets/KukriFrostRaven20261028/CrystalCrownV3/README.md) 的统一蓝色水晶材质，移除旧银色金属底座。只将下颈逐渐拓宽至柱体宽度，上方头形、原能量柱和螺旋粒子设计保留。这是具有立体明暗的 **2.5D HUD 图层**。
- 刀面使用 [BladeSigilV2](../../../SourceAssets/KukriFrostRaven20261028/BladeSigilV2/README.md) 的细密羽纹刻图，六种刀身分别拟合，保留原金属材质和法线，降低发光峰值以保留细节。ProductionV1 的生成、导入和交付来源已同步。
- 霜鸦能量条在持有者视口右侧与左侧对称排列，图案方向不翻转。狂战士和霜鸦明确归为传说，猎手和犬牙刀身归为特殊。
- 狂战士状态复制到观察者；世界身体粒子与整刀红光按复制的刀实例和符文材质匹配。能量条和屏幕边缘仍仅向持有者显示。
- 组合冲刺的单次接触累计两把实际参与刀的犬牙流血；普通和重击的独立接触不借用另一把刀的效果。

## 发布范围与共享接入

独立组件、作者脚本、HLSL、最终小型参数和目录文案直接保存到原路径。共享稀有度文件只发布弯刀分支，`.gitignore` 和 `Docs/AssetSetup.md` 只发布本轮追加段落。

[combined-dash-bleed.patch](combined-dash-bleed.patch) 仅包含组合冲刺流血增量，基于前轮 `modification-integration.patch` 中 **ColdSteelSkillModel.cpp 部分**应用后的文本，不能直接套到原始 Git 文件。应用顺序与前后文本散列见 [integration-baseline.json](integration-baseline.json)；核对同版本宿主，先按 `--include=Source/FPSGAME/Skills/ColdSteelSkillModel.cpp` 筛选前轮补丁，再用 `git apply --unidiff-zero` 应用本增量。其他共享接口按前轮文档移植，不对本次已直接发布的文件重复套旧补丁。本机已包含修复，不要重复套用。

原生检查案例仍依赖单独维护的 `KukriNetworkAuditCommandlet`、影子档案和攻击回执框架；[local-dependencies.json](local-dependencies.json) 记录本机对应版本，但不把其他任务的未提交源码一并公开。新增 [KukriRuneAudit 工具](../../../Tools/KukriRuneAudit/README.md) 是显式检查入口，不会在正常游戏启动时运行。公共仓库延续前轮的源码切片边界，**干净检出不是完整可运行工程**；本次未声称公开切片构建通过。

## 本地资产与归档

最终源图、已保存的霜鸦 UE 包及 SHA-256 见 [local-assets.json](local-assets.json)。已有刀身、图标、法线、材质供体沿用前轮清单；二进制资产按现有仓库与许可规则保留本机，不强制加入 Git。`Content` 仍联接至 `F:/FPSGAMEData/Content`，没有移动正式游戏资产。配方依赖现有基础刀模型、狼符文供体、合法源素材和本机 Blender／UE 环境，恢复时先恢复这些依赖，再执行最终导入入口。

34 个废案文件、6,868,906 字节已移入 `trash/kukri-refinements-retired-20261028`，包括被否定的银色鹰头与接座、早期低模鹰头和粗羽纹源文件／生成器。没有永久删除；所有移动前后散列一致，见 [归档清单](archive-manifest.json) 和 [完成记录](archive-receipt.json)。当前原图、图标源、狼的活动供体、构建日志与关键失败证据保留。

个人技能和仓库镜像同步补充了 [符文表面与局部拼接](../../../skills/ue5-weapon-workflow/references/rune-surfaces.md)、[逐刀结算合同](../../../skills/ue5-weapon-workflow/references/attachment-effect-contracts.md)、[观察者复制与传输检查边界](../../../skills/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)。

## 已有证据与未覆盖范围

[validation-evidence.json](validation-evidence.json) 保存前一轮用户授权检查的结果及本地日志散列：最终 Editor 构建成功；75 项隔离权威检查通过；监听主机／客机之间的 6 阶段 UDP 符文状态检查通过，双方各配置 60ms 延迟、3% 丢包。19 个改造、67 个保存资产引用无缺失。UDP 检查先于单独的犬牙结算修复，之后符文复制代码未改动。

UDP 夹具通过权威确认函数蓄能，检查持有者和双方观察者；没有覆盖端到端输入、攻击伤害 RPC 或背包上传。NullRHI 结果也不代表粒子画面、专用服务器、重连或打包验收通过。本次只做用户要求的整理和推送检查，未启动 UE、重新构建或重跑玩法测试。
