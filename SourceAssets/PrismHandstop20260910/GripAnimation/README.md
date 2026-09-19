# M4 棱镜阻手器专用握姿

2026-09-11 用户确认新版抓握成功。本目录保留已接受案例和复现入口；通用制作步骤统一维护在 [改造配件标准](../../../skills/ue5-weapon-workflow/references/attachment-standard.md)，旧流程不再单独演化。

安装 `prism_handstop` 后自动选择 `/Game/Weapons/M4PrismGrip/A_M4_Prism_*` 的九个专用动画。覆盖待机、瞄准、腰射/瞄准射击、装备拉栓，以及普通弹匣和弹鼓的普通/空仓换弹。卸下后恢复相应基础支撑姿态，切换三角握把则使用已有三角握把动作。

采用原 M4 手臂、手套、骨架和蒙皮。针对混元修整版的短阻手部安排掌位：食指、中指包握防滑部，拇指对握，无名指和小指收于下端。静态表面读回见 `contact_fit.json` 的 `final_surfaces`，不能把其中最初搜索候选的碰撞数当作最终姿态结果。

用户指出上一版只是贴在配件旁后，重新校正掌面朝向：掌长方向顺枪身，配件进入掌心与弯曲手指围出的空间。新增食指、中指对配件截面中心的包围检查、手套顶点侵入深度检查，以及掌侧/手背/正面实际渲染。最近表面距离和零相交本身不能证明抓握。旧失败脚本、参数及验收记录已移出活动目录，见 `trash/attachment-standard-20260911/manifest.json`。最终 `prism-grip-wrap` 为 336 项运行检查通过，9 个动画、446 个手指/阻手器采样无相交，用户已接受实际游戏预览。

## 作者入口

1. `fit_pose.py` 按运行安装座基准建立初始掌位和完整臂链。
2. `refine_contact.py` 在有限关节弯曲范围内修整手指，再调整掌位间隙并重新合指。
3. `build_animation.py -- idle` 生成静态拟合参考。
4. `fit_release.py` 检查手指展开与退让组合，结果以 `release_fit.json` 为准。修正掌面朝向后，手指可直接自然松开；随后进入原有取弹路径，末段反向合拢。
5. `build_animation.py` 生成九个可编辑 `A_M4_Prism_*.blend` 与 FBX。换弹接近段还沿模型下方绕行，避免从弹匣直接插值穿过阻手器。采样率沿用已验证的 120/240/480 Hz。
6. `validate_source.py` 检查骨长、缩放、手指局部平移、非左手轨迹和取弹插入合同。`check_geometry.py --full` 密集检查动作过渡的手指/阻手器表面，`review_animation.py` 输出实际模型关键姿态。
7. `import_assets.py` 导入独立 UE 动画目录，读回时长、压缩偏差，以及右手/枪体/弹匣和保留接触段与基础动画的偏差。
8. `run_validation.ps1 -Run <unique>` 以隔离 profile 启动新游戏进程，检查实际动画选择、瞄准射击、四种换弹、保存重载、替换与卸下、装备及近景截图。审计输出位于 `Saved/ForegripAudit/<Run>/`。

`ReferenceWorkflow/` 固定本次参考的三角握把作者脚本；对应散列见 `reference_hashes.json`。详细源动作帧合同见 `reference_contract.md`。

## 运行代码

`M4HandstopVisual.cpp` 加载专用变体；`FPSGAMECharacter.cpp` 在安装棱镜阻手器时选择它们，优先于通用弹鼓支撑姿态，动作时钟和机械音效仍走原有流程。`ForegripAudit.cpp` 共用两种握把的行为回归，区分各自的动画映射。

本次没有重做枪械数值、声效或手模。开发运行验证与最终产物散列见 `acceptance.json`；不代表完整打包验收。
