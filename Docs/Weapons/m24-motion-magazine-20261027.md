# M24 动作与 10 发扩容弹匣

用户本次指定：优化整套动作、加入战术冲刺，默认 5 发，并制作 10 发扩容弹匣。

## 接入

- 武器 `ue_m24` 默认容量保持 5，`magazine / m24_extended_mag_10` 使用标准 `mag_delta: 5`，得到 10 发。换回 `false` 恢复原厂短弹匣。没有改为逐发装填。
- 新骨骼网格：`/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9`。保留 Hold 的原生骨架、V9 手臂、JC 矫正形状和 Surface20261027 的母材质实例。原厂弹匣独立为 `M24_Magazine5` 材质段。
- 扩容壳体沿原模型的平直侧壁切分并连续延长 45 mm；保留上部接口，原有下部细节与底板整体平移，原表面 UV 不拉伸，新增连接带单独 UV 与标准金属母材质。静态件挂 `WPN_Magazine`，沿原生抽出、藏匣、插回动作运动。安装后仅隐藏原厂弹匣段。
- `modular_outfits.json` 为新网格继承原生 Hold 手臂适配。图标预加载沿现有 M24 配件路径分流，不添加新的逐帧加载。

## 动作安排

| 动作 | 本次处理 |
|---|---|
| 待机 / 瞄准 | 共享此前校准的 Hold 动作，保持腰射与瞄准基准 |
| 装备 | 沿原低位入场轨迹加入平滑加减速，结束回到同一持枪参考 |
| 射击 / 拉栓 | 保留已制作的右手拉栓接触，平滑末段回位，机械事件不挪帧 |
| 普通 / 空仓换弹 | 平滑起落；扩容版增加左臂托底位移和扭转差异层，跟随弹匣坐标，不移动整枪 |
| 检视 | 下移并略向右，减少镜筒进入画面中央 |
| 快速近战 | 保持第 5 帧命中，平滑后半段回收 |
| 战术冲刺 | 0.5 秒进入、1 秒循环、0.4 秒退出；右手持枪上抬、左手松握下放摆动；复用组件的可逆进入轨迹及 0.16 秒动作打断退出 |

扩容换弹保存为 `DA_M24_Mag10`，只有普通与空仓换弹的 5 根左臂骨骼有差异。比较用 FBX 保留于制作目录；其 UE 动画临时对象没有保存，不复制完整运行时动作族。待机、瞄准、射击、拉栓、检视与冲刺均共享。

源时钟 30 Hz：出匣 21、插入 38、坐实 40、空仓拉栓段开始 54、后拉 77、闭锁释放 94。弹药提交与普通换弹就绪改到第 40 帧坐实，音效继续按源时钟播放。

## 制作文件与交付边界

作者目录 `SourceAssets/M24MotionMagazine20261027`：`author.py`、可编辑 Blend、FBX、`install.py`、目录注册、图标制作与导入脚本。接入使用既有 UE 批次互斥；不主动打开、关闭或重启编辑器。

改造图标由内置 imagegen 依据实际模型图制作，均为灰阶金属框。原厂键 `ue_m24_magazine_false`，扩容键 `magazine_m24_extended_mag_10`，分类继续复用 `category_magazine`。最终源图在 [Icons](../../SourceAssets/M24MotionMagazine20261027/Icons)，实际提示词与来源在 [icon_generation.json](../../SourceAssets/M24MotionMagazine20261027/icon_generation.json)。正式 PNG 位于 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms`，对应 UI Texture2D 由 `import_icons.py` 保存。

后台 `FPSGAMEEditor` 构建成功：`Saved/BuildEditor/build-20261027-192125.log`。构建器等待现有构建结束后确认目标已是最新；没有关闭或启动编辑器、没有运行游戏。

运行与用户手感尚未测试。最终保存结果见 `install_receipt.json`、`registration_receipt.json`、`icon_receipt.json`；原生编译结果见 `build_receipt.json` 与 `build_console.log`。这些生产回执不代表游戏内视觉、动作或联机验收。
