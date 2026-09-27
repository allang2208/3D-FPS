# 锻造随机节奏、热剑胚与操作文字

用户要求在现有锻造流程内接入：光圈出现／消失时间合理随机、剑胚烧红、光圈与主体对比、下方按钮横向单行显示。

## 布局与数据合同

- 继续使用现有锻造抽屉及固定页脚，三项操作均分横向宽度。按钮正文沿用冷钢共享字体 14 px、36 px 操作高度与既有 DPI 换算；文字槽横向 Fill、纵向 Center，取消自动换行和显式换行宽度，单行居中。正文说明仍允许换行，内容区域独立滚动，矮窗保持页脚可达。
- 开始／领取、废弃与冶炼队列仍调用原有系统入口，保留禁用状态、返还预览、输入就绪条件和打开收回行为；本次不改变品质、材料或存档事务。
- `ForgingSystem` 在每处光圈打开时只随机一次寿命（2.2～3.2 秒）；接触或超时结算后只随机一次间隔（0.85～1.35 秒）。下个点还须满足回锤完成及已有交互余量。出锤后锁定当前点直至接触，保留 3 秒准备、20 点一轮；倒计时、目标可见性与超时使用同一实际寿命。
- UI 延续现有 50 ms 刷新及模型事件；不每帧重新采样、不增加独立计时器，不重建控件。说明文字从系统范围常量生成，避免文案与玩法漂移。

## 资源与呈现

- `M_ForgeHotSteel` 使用红橙自发光及 UV 程序化氧化斑。工作阶段热量维持 1.20→0.95，保留淬火阶段衰减至零的行为，冷却后显示深色氧化钢。
- 光圈使用青蓝色，与通红剑胚形成冷暖对比；瞄准小圈维持中性色，火星使用独立动态材质实例并保留暖橙色。
- 仅更新 `/Game/Props/ForgeInteraction20260927/M_ForgeHotSteel` 与 `M_ForgeGuide` 两个材质，不重导工具、手臂或动画。统一的 `Tools/Forging/forge_materials.py` 同时供增量材质保存脚本和完整导入脚本使用。程序化材质无新增下载素材。
- 完成源码、必要编译和实际材质保存；未要求预览、渲染或测试，交由用户测试。

## 本轮交付记录

- 用户关闭 UE 后完成常规 `FPSGAMEEditor Win64 Development` 构建并链接基础 `UnrealEditor-FPSGAME.dll`，日志为 `Saved/forge-random-heat-buttons-build-retry-20260927.txt`，结果 `Succeeded`。构建中修正了 MSVC 对导出类内多个 constexpr 成员合并声明的限制，四项范围常量改为分别声明。
- 无界面 Python commandlet 已保存 `M_ForgeHotSteel.uasset` 与 `M_ForgeGuide.uasset`，写盘时间分别为 2026-09-27 16:47:08／16:47:09。`Saved/forge-redhot-materials-receipt-20260927.json` 记录两个已保存路径；`Saved/forge-redhot-materials-commandlet-20260927.log` 含对应 SavePackage 写盘记录及 `FORGE_MATERIALS_SAVED`。
- 材质脚本已完成且没有材质编译错误；该后台进程因项目 AssetManager 未加载 `/Script/GameFeatures.GameFeatureData` 的 ensure 返回 1，不能将整个 commandlet 描述为零错误退出。未修改这项非锻造项目配置，也未重复导入网格。
- 未主动打开／重启图形编辑器，未运行游戏、截图、渲染或测试；实际节奏、热钢观感和按钮排版由用户测试。
