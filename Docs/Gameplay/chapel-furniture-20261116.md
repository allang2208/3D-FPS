# 教堂石桌与长椅交互（2026-11-16）

## 石桌

`TemperateHillsChapel.cpp` 中祭坛石桌的局部缩放设为 `0.75`，叠加教堂整体 `1.25` 后为 `0.9375`，即当前尺寸缩小 25%。保留原中心位置、台阶上的底部高度和材质。丘陵教堂重新生成时采用新尺寸，无需更换地图种子。

## 长椅

- 复用 `UFPSFurnitureRestComponent` 的 E 键交互、轮廓提示、服务端座位占用、入座和起身流程。
- 8 张实例化长椅，每张 3 个座位，共 24 个。模型缩放明确为 `1.25`，原生角色骨长与角色缩放不随家具放大。
- 座位横向间距 87.5 厘米，匹配玩家 84 厘米胶囊直径；按瞄准位置选择左／中／右座，目标被占时选择最近的空座。
- 模型局部正面为 `-X`；座位 yaw 为 180 度，叠加场景长椅的 180 度朝向后，坐姿面向祭坛。
- 作者网格椅面约 43.65 厘米，场景实际支撑高度取 54.561 厘米；动作锚点局部 X=-18，入座／起身点在动作前方 70 厘米。支撑数据保存于 `SourceAssets/ChapelFurniture20261116/pew_geometry.json`。

## 动作与性能

新增 `Rest.ChapelPew.Enter/Idle/Exit`，分别从当前男女 `Rest.Chair55.*` 已保存原生动画采样，未再次重定向女角色。保留原生脊柱、手指和其余动作轨道，仅修改骨盆以及腿、臂、手脚的接触轨道。

坐稳阶段降低原高椅动作悬起的双脚，采用各身体入座开始时的脚部支撑高度；掌根随大腿位置调整。骨盆按照实际椅面高度落位。进入后半段渐入接触修正，起身时按相反时序释放；入座、休息和起身衔接端点统一。保留 2.8 秒入座、4 秒休息循环和 3.1 秒起身，另沿用交互系统 0.6 秒就位。

6 个原生动画资产已编译并保存。男女第一人称眼位分别从对应的已保存新动画生成，并绑定该动画路径。只增加教堂长椅配置，不替换旧家具动作。沿用长椅 ISM 和现有交互节流；接触调整离线烘焙，无新增 Actor、每帧场景扫描或运行时 IK。

资产路径：

- `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/ChapelPew20261116/`
- `/Game/Characters/KaitlinPlayer20261023/ChapelPew20261116/`

作者与发布入口：`Tools/FurnitureRest/chapel_pew_geometry.py`、`chapel_pew_assets.py`、`author_chapel_pew.py`、`publish_chapel_pew.py`。共享玩家配置通过 `config_transaction.py` 按字段合并；家具配置在写入锁内重新读取，仅合并长椅类型、动作和目标模型座位。

## 交付边界

后台资产保存和配置接入已完成，回执见 `SourceAssets/ChapelFurniture20261116/assets_saved.json` 与 `publication.json`。程序构建结果分别记录在同目录的 `FPSGAME-build.json`、`FPSGAMEEditor-build.json`。

`FPSGAME` Development 构建成功。`FPSGAMEEditor` 由现有共享工程构建完成：本次 `TemperateHillsChapel.cpp` 已编译，随后共享工程中的网络调试命名错误由该模块当前工作修正，最终 DLL 链接成功。保留了现有构建与后台进程，没有修改该网络调试文件；编辑器回执记录实际采用的共享构建日志。

按用户规则未启动交互式 UE、PIE、游戏或视觉验收；坐姿外观、多人交互和实际游玩由用户测试。

## 用户要求的男女动画预览（2026-11-16，后续）

用户随后明确要求查看坐下和起身，以及臀部／椅面、脚底／地面、手掌／大腿的接触。已通过只读后台 commandlet 读取当前配置对应的六个已保存压缩动画、男女身体与头部蒙皮，以及长椅实际网格。按原配置的 1.25 倍家具缩放和中间座位锚点离线渲染，角色骨长保持原值。未修改正式动画、模型或交互配置。

交付位于 `SourceAssets/ChapelFurniture20261116/PreviewR1/`：

- `chapel_pew_male.gif/.mp4`、`chapel_pew_female.gif/.mp4`：各 8 秒，原速，前侧视角与侧面剖切同步；尾部含短暂站稳停留。
- `chapel_pew_male_inline.gif`、`chapel_pew_female_inline.gif`：对话直接展示版本，960×600、12 FPS，各 8 秒，约 2.4 MB。
- `chapel_pew_contacts.png`：男女坐稳 0.6 秒时的臀部、双脚、手掌特写。
- `manifest.json`：实际读取的身体、动画和座位配置；`foot_contact_observation.json`：坐稳帧脚底最低蒙皮点到地面的距离。

预览采用中性灰模材质。剖切只隐藏近侧椅体以便观察支撑面，不移动椅面或修改角色姿态；非游戏 E 键交互录像，也未覆盖装备服装、多人与运行时混合层。

当前可见结果：男角色手掌与大腿仍有可见间隙，女角色更贴近大腿；坐稳 0.6 秒时，男角色双脚最低点离地约 0.345 厘米，女角色约 0.364／0.392 厘米。这是当前资产的预览结果，不将其记为完全贴合通过。当前请求仅交付预览，未据此重新发布动作。

## 手部自然放置修订 HandsR2

用户要求参考其他入座动作继续优化僵硬手部。此次读取当前男女原生 `Rest.Sofa.Enter/Idle/Exit`，以沙发入座前段的自然下垂和坐稳时的腿上手指姿态为参考。参考路径记录于 `SourceAssets/ChapelFurniture20261116/HandsR2/reference_routes.json`。

调整锁骨、上臂、前臂、手腕和手指轨道；骨盆、腿脚、脊柱、头部、座位锚点及动作时长沿用 R1。男女分别在各自原生骨架上制作，用实际蒙皮大腿表面和掌根厚度确定放置点，不重复重定向。左右手位置略有前后差异，掌面顺着大腿坡度，手指保留自然弯曲并减少张开幅度。

入座时左手在 0.72–2.32 秒、右手在 0.92–2.55 秒逐渐落位，手腕旋转和手指放松稍后跟随。起身时左手在 0.60–2.18 秒、右手在 0.76–2.36 秒释放接触，经过抬离和回收，再回到身侧。低位下垂路径绕开长椅前缘。接触与过渡均离线烘焙，运行时不增加 IK 或场景查询。

制作入口为 `Tools/FurnitureRest/read_chapel_hand_sources.py`、`author_chapel_relaxed_hands.py`、`save_chapel_relaxed_hands.py`。新版目录为 `ChapelPewHandsR2_20261116`；保留 R1 动画，发布器只合并六个教堂长椅动作和对应眼位字段。

六个原生动画已通过后台 commandlet 保存，`HandsR2/assets_saved.json` 记录 `saved=true`；`HandsR2/publication.json` 记录配置已应用。此次实际修改为男女六个动作引用及其眼位动画绑定，家具时长和眼位采样数值没有变化。未改动 C++，无需为此次手部修订重新构建程序。

`HandsR2/Preview/manifest.json` 与各角色 `saved_poses.json` 来自保存后的原生压缩动画；离线预览使用实际身体和长椅网格，显示全身及手臂近景。此范围不包含服装覆盖或游戏内交互、多人同步测试，未启动交互式 UE 或 PIE。

最终预览已输出至 `HandsR2/Preview/`：男女分别为 `chapel_pew_male_inline.gif/.mp4` 和 `chapel_pew_female_inline.gif/.mp4`（MP4 文件名不含 `_inline`），各约 8 秒、原速；GIF 为 960×600、12 FPS，MP4 为 1280×800、15 FPS。`chapel_pew_hands_before_after.png` 使用 R1 与 R2 的同机位、同坐稳时刻作男女手部对比；`chapel_pew_contacts.png` 保留臀部、脚底和手掌接触特写。预览文件信息记录于 `delivery.json`。

## 用户改为自然下垂：HangingHandsR3

用户随后明确要求“调整自然下垂，不放在大腿上”。此版取消入座时向大腿落手以及坐稳时的腿上接触，双臂放松垂于身体两侧，掌心朝内、手指轻弯，起身随身体回到站姿下垂。手肘略弯，用实际手部蒙皮的最低点给连续长椅椅面留出指尖空间。

男女分别从 R2 保存后的原生压缩姿态制作，参考各自已有沙发入座前段的下垂手臂与手指。仍只写入原来的 38 条锁骨、手臂、手腕、手指轨道；时长、骨盆、腿脚、头部和长椅座位配置沿用现有数据，不增加运行时 IK。

作者入口：`Tools/FurnitureRest/author_chapel_hanging_hands.py`。保存、发布与原生预览采样入口：`Tools/FurnitureRest/save_chapel_hanging_hands.py`。制作数据位于 `SourceAssets/ChapelFurniture20261116/HangingHandsR3/`，新动画目录名为 `ChapelPewHangingHandsR3_20261116`。

六个新版动画已保存并发布到当前教堂长椅动作引用，回执为该目录的 `assets_saved.json`、`publication.json`。后台保存命令正常退出；此次没有 C++ 修改或程序构建。`Preview/` 从已保存的原生压缩动画生成，前后对比使用上一版 R2。未启动游戏或 PIE；服装覆盖、交互和多人同步仍由用户在游戏中体验。

下垂版最终预览已完成：`HangingHandsR3/Preview/chapel_pew_male_inline.gif`、`chapel_pew_female_inline.gif`，以及对应不带 `_inline` 的 MP4，均显示原速坐下、坐稳和起身。`chapel_pew_hands_before_after.png` 为 R2 腿上放手与 R3 身侧下垂的同机位对比。
