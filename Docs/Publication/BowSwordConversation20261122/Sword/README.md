# 锻钢双手剑开发恢复包

物品 ID 为 `ue_forged_steel_greatsword`。F6 通过物品定义进入「武器 → 双手剑」；仓库预置、锻造与改造台各自使用对应的登记项。公开数据基线为 `3068fe3fcb1e56b2fd73d0eb000c71f385ae0e96`，已包含物品定义、部件模型目录和全武器刀身材质。此次在该基线上补入武器公式、锻造配方、通用及四项专属改造、旋风材质映射与 Cook 目录。

## 恢复代码

完整制作工程使用拆分后的 C++ 模块。部分生产文件在公开仓库仅以先前发布的重放补丁存在。为保持同一套声明、实现与联机入口，`Runtime/Source/FPSGAME` 保存新增的九个完整单元，`Integration` 保存共享文件的精确差异。`runtime.json` 登记工程相对路径与前、后 SHA-256。散列统一将 CRLF 转为 LF，同时保留原文件 BOM。前置版本为从当前生产文件逐项扣除本会话改动得到的对应文件，其余同期修改保留在宿主中。

在含 `FPSGAME.uproject` 的匹配制作工程执行下列命令。第一条仅列出状态；第二条在所有选定文件均与记录相符时重放。发生版本分歧时按文件取 `Integration` 中的补丁，保留现行宿主的其他实现。已含最终版的文件可重复运行。如与弓的补丁同时重放，`GunsmithSystem` 和 `ColdSteelPlayerProfileSync` 的共用回执以完整实现合并一次。

```text
python Docs/Publication/BowSwordConversation20261122/Sword/replay.py <项目根目录>
python Docs/Publication/BowSwordConversation20261122/Sword/replay.py <项目根目录> --write
```

## 模型和改造的制作入口

从 `SourceAssets/ForgedSteelGreatsword20261120` 开始。在本机恢复原始 Meshy GLB、源贴图、已确认图标原稿和引擎依赖。原始 GLB 可放在 `Integration/Original` 或使用环境变量 `FPSGAME_FORGED_SWORD_GLB` 指定。图标提示的 `refs` 相对于项目的 `SourceAssets`。原厂卡的可复现输入是本机保留的五张原稿，重新生图时仅能复现构图和材质要求。

1. `Integration/prepare_model.py` 在 Blender 生成拟合模型；`author_modules.py` 按剑身、护手、握柄和配重的真实连接面分件，`install_assets.py` 导入正式包。使用原厂 UV，`BladeFinish/author_atlas.py` 与 `install_refinish.py` 提供修复后的锻钢表面。
2. `CommonMods/author_variants.py`、`author_grips.py` 生成共用造型和握柄。通用刀身材质从已发布的全武器入口恢复。原厂图通过 `author_icons.py` 生成形状参考，`stock_icon_prompts.json` 记录已采用的生成提示，`prepare_stock_icons.py` 和 `install_stock_icons.py` 输出同源的灰度图卡。
3. `LegendaryBladeLiebo` 保留历史制作目录名，物品使用「镂空剑身」；`ExecutionerBlade` 保存宽根尖锋及四种护手接口。GuardSeats 后台导入使用 `FORGED_GUARD_AUTHOR_HOST` 指定已准备好原厂材质和贴图的隔离宿主。两个目录均含 Blender 制作及 UE 导入入口。
4. `RingChainPommel` 提供七节铁链模型、PBR 制作与导向点，使用弯刀挂饰图的 WPO 节点；`FishtailPommel` 保存玩家确认的鱼尾造型。导入各自的模型和贴图后，通过 `CommonMods/publish_catalog.py` 登记。公用横扫动作及折射网格来源为 `SourceAssets/HighlandBroadbladeSweep20261104/SweepRift/bake_ribbons.py`，实装按握柄选取。
5. `SourceAssets/AllWeaponRuneFlow20261102/read_materials.py` 读取当前实际材质生成本机图表，`knife_flow.hlsl` 是刀类固定符文遮罩内的移动脉冲。普通和旋风材质的恢复要沿该目录现有制作脚本读取实际依赖。项目制作步骤与全部 GPU 资产分别存放。

## 证据与边界

`receipts.json` 给出 11 月 21 日生产回执和恢复包的文件路径、字节数与 SHA-256，方便在本机 F 盘按原件找回。该日历史测试包含本机独立进程经 UDP 的主客机、装备重连、普通及重击换装快照、镂空双目标流血、处刑眩晕、鱼尾物理加成及八目标横扫；最终重击精度修正录得 70 项通过。第三名远端旁观玩家、公网和独立专用服务器未在该轮覆盖。横扫和符文的远端读数来自组件、材质绑定和事件，F6 来源为命令行断言。本次 Git 整理复核了补丁双向恢复的 SHA-256，没有重新运行游戏。

材料、源模型、原稿及 UE 包以本机生产库为准；远端源码不能单独重建第三方输入。武器标准与专属属性详见 `skills/_shared/ue5-weapon-workflow/references/forged-greatsword-blades-and-pommels.md`。
