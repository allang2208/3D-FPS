# 加长件（扩容弹匣类）改造与重建规则

来源：`ext_mag` 扩容弹匣连续五轮返工的收口经验（2026-09-18）。适用于任何"在原厂件基础上加长/改造"的配件（弹匣、枪管、枪托、导气管）。配套口径见 [attachment-standard.md](attachment-standard.md)（落位与接口）与 [weapon-finish.md](weapon-finish.md)（材质来源）。

## 1. 几何来源必须是该枪自己的源

- **不要**从别的枪的工作场景里取"同名部件"：本项目 M4 弹匣一度取自 `AKM_RearGripSections_Editable.blend` 里的 M4 段，坐标属于那个场景，实机就是"弹匣错位"。同一工作场景里各枪部件虽同名同结构，坐标系并不等于该枪运行时网格系。
- 正解：在**该枪自己的步枪源 FBX** 里按"该部件所属材质槽"取面。本项目用例：M4 → `SourceAssets/M4HK416Replica20260910/SK_M4_FoldingSights_HK416.fbx` 的 `Magazine Light.001`；QBZ-191 → `SourceAssets/PhantomRearGripIntegration20260913/QBZ191/SK_QBZ191_Manny.fbx` 的弹匣槽；AKM → `PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx` 的 `AKM_FactoryMagazine_Preview` / `M_AKM_Soviet_Magazine`。
- 原位延长后**落位由原厂件本身保证**，不要再做 RANSAC 拟合、也不要按井口测量重建坐标系——拟合是把"另一把枪的件"塞进本枪时才需要的补救手段。

## 2. 延长方式：直件切线平移，弯件绕曲率中心旋转

- 直筒件（AKM 7.62、M4 PMAG）：把延长带以下沿**该截面自身的局部切线**平移，位移量在带内 smoothstep 渐入。切线取中心线（切片质心）的二次拟合求导，避开肋骨造成的质心噪声。
- 弯件（QBZ 5.8 mm）：切线平移会把下半段拉直，实机一眼可见"弧度不对"。改为**绕拟合曲率中心刚性旋转**：在延长带处拟合中心线的曲率半径 R，把下段整体旋转 Δθ = 加长量 / R（方向沿原弧继续）。本项目 QBZ 拟合 R ≈ 45 cm、Δθ ≈ 7.6°，延长后宽度轴尺寸不变，弧线连续。R 与 Δθ 要写进回执。
- 曾经的两种错误做法，别再重复：① 沿一个固定方向整体平移（底板离开曲线，底部读成"尖角"）；② 复制一段本体再焊接（接缝处留下开放边，实机是台阶）。

## 3. 渐变带必须避开换弹抓握区

- 被拉长的那 6 cm 表面细节一定变形。本项目换弹动画左手在**距喉部 10–15 cm** 处合拢，早期按"距喉部 11 cm 以下延长"正好压住握点，实机表现是"左手没精准抓握弹匣"。
- 规则：延长带放到**靠近底板一侧**（本项目距底 ~2 cm 起），上段（喉部与抓握区）保持原厂几何；改完用手部抓握区与延长带的距离自检一次。

## 4. 重建件不要克隆原材质

- 克隆原材质会把它的图集贴图（BaseColor/ORM/Normal，按 UV0 采样）一起带过来。重建件的 UV0 与原厂件在枪身图集里的岛不再对应，结果是一片错位方块——用户原话"完全是马赛克"。
- 重建件用**自包含材质**：只采样"烘焙/投影到该件自己的 UV"的图（本项目 QBZ 走"机匣涂层 + 接触磨损烘到该件 atlas"，M4 走"物理投影 UV + 复用已验收的逐枪涂层材质"）。
- 绑定后自检：材质的纹理采样要么落在"该件自己的 atlas"，要么走物理投影 UV；不允许出现"按 UV0 采样枪身图集"的残留样本。

## 5. 验证手段（按可用性排序）

1. **编辑器直连**（首选，见 `Docs/ue-mcp-20260918.md`）：在运行中的编辑器里摆件、设相机、截图，并直接读资产的实际尺寸与材质绑定。
2. 夹具捕获：`FPSGAME.exe -DrumGripAudit -MagazineAudit=ext_mag -AuditWeapon=<id>`（需要 `Content/ShaderCodeLibrary` 存在，否则启动即报 `Failed to initialize ShaderCodeLibrary`）。
3. Blender 同机位对照渲染：原厂件与加长件同相机出图，用于判弧度、底板、渐变带位置（本项目 `Reference/akm_*_mag_*.png`、`m4_ext_mag_*.png`）。

## 6. 退役与留档

- 废案（旧 FBX 变体、旧烘焙图、被否决的脚本）按 [publication.md](publication.md) 移入 `SourceAssets/<task>/trash/<task>-<date>/`：记录原路径、目标路径、字节数、SHA-256、原因与替代物，移动后读回散列比对。本项目第五轮的清单见 `trash/extmag-superseded-20260918/MOVED_final.json`（48 项 / 254.9 MB，散列全一致）。
- 保留"能重建当前结果"的输入：该枪原厂件 FBX、延长脚本、UV 工序脚本、安装回执；只退役被取代的中间产物。
