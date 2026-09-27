# 长杖装备图标与手套／衣袖接入 V24

用户范围：按装备栏现有规则处理法杖图标，排查持杖双手未显示手部与衣物装备。保留 V7 身体、已认可的抓握和动作。

## 原因与修复

1. 动态武器图标固定从 `Icons/<Definition>.png` 读取目录回退图。原来只有方形斜放的 `apprentice_staff.png`，缺少 `ue_apprentice_staff.png`；离线导出器还只读 `items.json`，漏读分开的 `staffs.json`。
2. 动态图标使用 SceneColorHDR 反向 alpha，同样受 V22 Thin Translucent 不写覆盖率影响。工作台已有 V23 修正，现在经 `ColdSteelStaffPreview.h` 共用于工作台、动态图标、离线目录图，只覆盖临时组件。
3. 法杖图标采用作者占格画幅公式：320 高，宽 `max(256, round(320 * grid_w / grid_h))`，主轴填充 91%，轮廓居中。当前 1×4 法杖为 256×320 透明竖图。装备栏沿用近战图的 −90° 横放和等比 fit，杖头朝左；背包沿用占格及旋转处理。不改共享画刷尺寸或硬拉伸。
4. 原换装配置只登记完整 M4 视模，没有登记持杖实际使用的 `BarePalmV7/M4/SK_M4_BareArmsV7`。该独立网格的实际材质分区为 0 上臂、1 小臂、2 手部，不是完整 M4 的 6／7。已添加正确 profile，复用 `rig_profile=M4` 的现有衣袖、全指／露指／钢制手套派生和覆盖合同。
5. 换装继续由现有组件读取槽 3／7、异步装配、Leader Pose 跟随、卸下恢复裸手。资产查询确认这些装备与持杖裸手使用同一骨架。没有新增动画、改动握姿或重建皮肤。配置按现有合同在下一次进入游戏时读取。

## 文件与制作

- `inspect_outfit_source.py` / `outfit-source-inspection.json`：读取实际 UE 网格、材质槽与骨架，未运行游戏测试。
- `register_equipment.py`：只追加独立 M4 裸手 profile，并修正法杖目录的 `ue_icon`；不复制物品身份或编辑存档。
- `build_catalog_icon.ps1`：基础 DLL 更新后，后台仅生成学徒长杖目录图；同步旧文件名别名以兼容旧存档里的图标路径。当前正式图源为 UE 共享捕获，不再用 V21 的方形 Blender 图覆盖装备栏图。
- 图标子系统复用组件时清理长杖和剑的异类子件，避免旧杖头残留；法杖只请求当前装配与预览材质，不同步加载多余的完整世界模型。
- 修改前文件保留在 `Before/`；实际产物分别记录在注册、图标与构建 receipt。

## 边界

源码与配置已保存，FPSGAMEEditor Win64 Development 基础 DLL 构建成功（`Saved/BuildEditor/build-20260927-233829.log`）。后台单件目录制作成功（`catalog-export.log` 中 `COMPLETE failures=0`），实际透明 PNG 为 256×320，水晶可见，新旧文件名内容相同。制作中只追加了独立 M4 裸手 profile，其他已有 profile 与装备物品配置未变。

未主动打开编辑器或运行 PIE；持杖时换上、取下、切换手套与衣服的实际画面由用户确认。图标制作与资产结构核对不是游戏内换装验收。
