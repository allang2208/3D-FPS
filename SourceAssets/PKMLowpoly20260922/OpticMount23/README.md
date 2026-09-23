# PKM 上机匣瞄具连接座修订

2026-09-23，用户要求统一连接座材质，并检查、调整其大小与形态。只修改连接座及瞄具安装高度，沿用 Motion21 主体、Finish20 枪身与配件材质、现有动作和弹链动态层。

## 定位与修改

旧连接座为 173 mm 长的矩形脊梁、两个 18 mm 高方块支脚及矩形导轨齿。支脚未按上盖表面成形，底部在中心区域埋入约 3.7 mm；后端进入照门所在的纵向范围。旧件实际已绑定 Finish20 的 Interface 材质，但使用 Accessories14 的独立涂层图和 UV2，并不是当前机匣实际图集与材质图。

新版长 122 mm，顶面从枪局部 Z=123.5 mm 降至 114.4 mm。两只低支脚以当前 `PKM_Part_043` 表面逐点取样，前脚适应较宽上盖、后脚适应较窄的隆起区域；斜肩过渡、斜面导轨齿、倒角、加权法线及小型紧固件取代原方块堆叠。底部留 0.12 mm 的装配交叠，避免接触面闪烁。

全息、全景红点、2 倍棱镜和 LPVO 保留自身大小与纵向位置，安装平面统一下降 9.1 mm。仍挂在 `PKM_Cover`，开盖时连接座与瞄具一起运动。`PKMAttachments::MeshPath` 和 `OpticMount` 是角色/展示所用的现有共同入口。

## 材质

从当前机匣顶部干净的 24×50 mm 区域，按实际 UV 提取 BaseColor 和 ORM 的涂层信息，生成连接座专用贴图。复制当前机匣的 Finish20 干/湿材质图，保留实际粗糙度转换、金属度处理及微划痕强度，再替换采样贴图。

连接座的材质使用自身 UV0 与对应切线。原机匣图集的结构法线不挪用到新连接座；造型由新几何倒角和加权法线表达，避免把别处的凹槽投射到支脚。去除采样区域的宿主 AO，保留新模型自己的光照遮蔽。新增干湿对应项合并进原 `Finish20/DA_PKM_WetMaterials`，未替换其他配件的映射。

## 保存资源

- 网格：`/Game/Weapons/PKMLowpoly20260922/OpticMount23/SM_PKM_optic_rail`。
- 干/湿材质与三张贴图：同目录的 `Materials`、`Textures`。
- 可编辑源：`PKM_OpticMount_Editable.blend`，含上盖接触参考；仅导出新连接座。
- 作者入口：`author_mount.py`、`sample_receiver_finish.py`；后台导入：`import_mount.py`。
- 旧连接座资产和作者文件保留，可回溯。

## 本次检查范围

`source_geometry.json`、`fit_measurements.json` 记录修改前实测，`fit_after.json` 记录新导轨范围、四种瞄具底脚余量、照门间隙及实际保存材质绑定。导轨后端距离照门前缘约 4.78 mm；四种瞄具底脚都落在新导轨纵向范围内，保守竖直间隙均为正。

`mount_before.png` / `mount_after.png` 是同视角的 Blender 几何检查图，使用统一灰模，不代表 UE 实际材质渲染。后台导入在 PCD3D_SM6 下完成，两份材质的编译错误列表为空，网格实际尺寸约 31.84×122×18.83 mm；保存回执为 `import_receipt.json`。

常规 Editor 构建已成功并写入正式 DLL；日志 `Saved/BuildEditor/build-20260923-100510.log`，控制台输出保存在本目录 `build_cpp.log`。没有打开交互式 UE 编辑器，也未运行游戏、ADS 或换弹测试，实机视觉与接触表现仍由用户测试。
