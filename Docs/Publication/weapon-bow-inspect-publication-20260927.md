# PKM、弓配件与手枪检视发布／恢复

本轮以用户最终决定为准：PKM 枪钢与绿色弹箱缎面升级；两款弓弦、两款箭台、开放单片 2×／4× 瞄具；绿色分划清晰度与拖影修订；无限备弹箭也可靠近收走；撤回独立转枪检视，单持 DW715 恢复原检视并适配到 M1911，双持不播放检视。

## 发布与保留边界

在 `D:/FPS3D/FPSGAME` 当前 Git 仓库精确暂存本轮变更，普通推送到 `origin/main`。共享角色、双持、弓组件、配置仅收录本轮部分，不携带其他任务的动作优先级、换弹、奔跑／跳跃、LMG201 或其他武器改造。

公开 C++、正式弓改造目录、作者 Python／PowerShell／HLSL、三份独立数值配方、文档和技能。原始／派生 Blend、FBX、图片、声音、UE 包、密集表面／姿态 JSON、临时日志、导入及桥接回执留在本机；`trash` 不上传。源代码发布不等于完整工程素材备份。

## 当前依赖与恢复顺序

1. **PKM**：保留合法 `PKMLowpoly20260922` 枪体、QBZ 系原有材质、SVD/A762 细纹来源与 `DA_PKM_WetMaterials`。当前配方 `SourceAssets/PKMRefinedFinish20260927/finish_recipe.py`＋六份 HLSL，安装入口 `install_finish.py`／`run_install.ps1`；`inputs.json` 为本机读取输入。82 份干湿母材质及 `T_PKM_SatinFinish` 已保存，旧分阶段入口 Finish20／HandleFinish27／AmmoBox30 末尾也应用当前配方。不要把旧入口当全枪重建顺序反复覆盖现有分件。
2. **弓弦**：恢复现用猎手弓、动态弦挂点与原程序化弦几何；运行 `BowStringVariants20260927` 的图标制作、材质导入和目录安装入口。两款数值以 `series.json` 和 `Content/ColdSteelData/bow-gunsmith.json` 为准，5 个资产已保存。
3. **箭台**：恢复原木箭台表面／UV、现用木材与弓体中心接口；`read_source.py` 生成本机 `source-binding.json`，再 author → import → install。`BowArrowRestVariants20260927` 的 12 个资产已保存，开口速搭为搭箭 −80%、拉满 −10%、子弹速度 +5%、腰射扩散 +10%；双叉腰射扩散 −25%、子弹速度 −5%。
4. **单镜片瞄具**：保留 WoodBracketV19 木座作者源、WoodLongbow 木纹、受保护弓体接口及已认可的单镜片概念图。`BowSingleLensOptics20260927/author_assets.py` → `import_assets.py` → `install_config.py`；11 个初始资产已保存。当前材质必须使用 `ReticleReadability/materials.py`／`Reticle.hlsl`，已有包的最后增量入口为 `TemporalStability/apply_temporal.py`。不用已归档的全屏绘制或旧绿色过渡版；相机提供 2×／4×，并非镜内独立 SceneCapture。
5. **回收**：按 `BowArrow.cpp` 发射时的实际消耗标志分流；实弹提交原箭种入袋，虚拟箭仅销毁，保留遮挡／死亡判定。无需新增资产。
6. **M1911 原检视**：保留本机 `DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend` 的原 inspect/idle、`M1911RearRain20260913/M1911_RearFinish_Editable.blend` 的正常／空仓 idle、原生 BarePalmV7 源和 `DualPistolQuickCombat20260920/VideoRefV3/author_actions.py` 的纯整臂求解函数。`M1911RevolverInspect20260927/author_inspect.py` 使用独立 `author_support.py`，不依赖退役 spin 源；再运行 `import_assets.py` 创建两段新动画，现已保存于 `/Game/Weapons/M1911/RevolverInspect20260927/Animations`。原 DW715 动画未覆盖。

上述输入含本机授权／已有来源派生内容，未新增可公开分发素材的许可。不能仅从 Git 克隆恢复最终外观；先补齐合法本机依赖，再按各目录 README 制作。

## 废案归档

此前独立转枪检视源及 27 段 UE 动画共 76 文件已在 `trash/pistol-spin-inspect-rejected-20260927/`。本次另将旧检视文档、弓全屏绘制、旧荧光绿与中心点过渡版本、PKM 哑光备份、旧分划备份和已完成一次性助手共 127 文件移入 `trash/weapon-bow-inspect-publication-20260927/`，合计 203 文件。逐文件原路径、目标、大小、SHA-256、原因与替代物见 [归档清单](weapon-bow-inspect-archive-20260927.json)。本次新增归档已作移动后散列读回；有效底座、原动画、手模、原生绑定、求解器和当前可编辑源继续保留。

## 构建与检查边界

本机资产保存状态以各目录回执为准。弓实体瞄具和回收曾分别取得 Live Coding 成功记录；最终手枪回退遇到 `LiveCodingLimitError`，常规 DLL 构建随后因编辑器重新打开而未执行。本次整理又移除了已禁用的弓全屏绘制分支，最终原生源码尚待常规构建，不能称已更新运行 DLL。已有编辑器未主动关闭、重启或开启游戏。

按用户本次要求只进行发布检查：远端／分支、待推送历史、完整暂存差异、空白错误、文件大小、敏感信息与许可边界。不运行游戏、自测、截图或动画／材质验收，效果由用户测试。共享工程其余未提交工作保持原状。

本次检查覆盖精确清单中的 77 个文件，`git diff --cached --check` 无错误；暂存项均为文字源码／配置／文档，没有二进制或超过 1 MiB 的文件，凭据模式扫描未发现命中。PowerShell 制作脚本保留 UTF-8 BOM。归档元数据和本地目标大小对应，203 个原路径均已移出当前目录。完整暂存差异及逐文件散列留在本机 `Saved/WeaponPublication20260927/`，不把这些发布检查当成游戏验证。
