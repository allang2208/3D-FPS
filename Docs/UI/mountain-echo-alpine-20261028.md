# 山鸣 · 阿尔卑斯剪影 V23

用户认可 `approved_design.png` 后要求按图细化接入。本轮以已认可的阿尔卑斯剪影生成真实 RGBA 制作贴图，替换此前的矢量山脊。保留主峰、前后山层、岩壁和雪线、金色山脊与柔光；贴图和完整生成提示词保存于 `SourceAssets/WoodSteelLongbow20261026/MountainEchoAlpineV23`。

## 资产与表现

- 源贴图 `T_MountainEcho_Alpine.png`：2172 × 724，RGBA，原始生成文件直接保存；引擎 UI 纹理限制最长边 1024，保留 alpha、sRGB 和无损 UI 压缩，夹取寻址、双线性过滤、无 mip／不流送。单张小纹理，无额外模型、Niagara 或截图捕获。
- 引擎路径 `/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAlpineV23`：`T_MountainEcho_Alpine` 和 `M_MountainEcho_AlpineHUD`。材质为 UI / Translucent，使用贴图 alpha，底部平滑淡出；半透明边缘统一暖金色，保留不透明岩体原色，不会以整个矩形遮盖画面。
- 单一参数 `ResonanceState` 四通道承载点亮比例、命中亮带、满层呼吸和满层辉光。新命中仍用 .38 秒推进新增的 1/3，三层满时发光。暗态低亮青铜，已点亮区域保留原金色岩面及细节；边界平滑过渡，雪线高光承担短时反馈。
- HUD 画面宽度 160 px，高度按源贴图 3:1 保持为约 53.3 px，绘制矩形顶部在拉弓条下 4 px。图中主体与外部柔光保留透明留白。装备山鸣弓弦期间，经验提示基础偏移从 96 px 调至 136 px，留出上漂与外框空间；其他装备沿用原位置。

## 数据与生命周期

`UBowMountainEchoComponent` 随原装备资源异步请求加载 UI 材质，为每个玩家创建一个受 UPROPERTY 持有的动态实例；换装和 EndPlay 清理。父材质引用贴图，同一异步载入覆盖依赖。显示继续只读服务器层数及本地呈现时钟，组件不因为 UI 绘制增加层数或改变伤害。

`ColdSteelBowResonance::Paint` 仅更新一个参数向量并绘制一个材质矩形；不创建动态材质、不触发磁盘读取、同步加载或纹理等待。保留装备、死亡、菜单和翻越的原隐藏入口；不新增控件、输入焦点、委托或计时器。

满弓命中条件、训练靶兼容、10 秒层数时限、弦影箭发射消费与伤害、金色弹道／爆裂、B4 音效全部沿用现有规则。已有武器目录 AlwaysCook 覆盖新资产，无需新增全局打包目录。

本次组件新增瞬态动态材质成员，因此在资产导入及游戏构建后完成基础 Editor DLL 常规构建，不以当前编辑器热补丁代替正式交付。默认不启动游戏、不截图或实机测试，由用户测试。

2026-10-28 交付状态：透明剪影源图、认可设计图和生成提示词已保存。Texture2D 与 UI Material 已通过后台 commandlet 导入、编译并保存，最终回执 `import-receipt.json` 为 complete。FPSGAME 和 FPSGAMEEditor Win64 Development 常规构建均成功；没有启动 UE、游戏或实机验收。旧 V22 矢量源已保存在其制作目录，旧导出脚本改读该快照，保留恢复来源。
