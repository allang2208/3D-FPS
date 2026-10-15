# M66 V09 小手与口腔/腹部蒙皮分离

用户反馈：另一只手在攻击时带动口腔、腹部，出现折叠条带与拉伸。来源为用户提供的游戏截图，未另行启动游戏或渲染。

## 原因与制作

V05 用已有的手指权重识别小手，导致本就错误绑定手指的口腔组织被跳过。V08 主要处理巨手，未解决这一侧的区域归属。例如原顶点 80049 与 82176 同属口腔表面，一端几乎完全绑定 Bone_046，另一端混有骨盆和腿部；原边长约 2.6 cm，在已有横扫源动作中被拉长约 43 cm。

V09 从 V08 源文件继续制作：

- 在临时焊接的邻接图上，以肘部横截面识别实际小手和前臂，共 3,988 个原网格顶点；不会将 UV 岛或原有骨骼标签当作解剖分区。
- 实际手部清除躯干、腿部影响，肘部衔接渐变；手部以外的口腔、腹部清除小掌与手指影响。
- 口腔组织采用连续的骨盆/脊柱权重场，侧边和上缘保留平滑过渡。同位置 UV 接缝写入一致权重。
- 共改写 37,457 个顶点的权重，保留 161,840 顶点、197,023 三角形、95 根源骨骼、原几何、UV、材质、眼珠及背部控制骨。
- 保留 V08 横扫动画、伤害时间和采样，以及现有导航、移动、受击与 V07 死亡物理资产。此轮不修改原生代码，无需重编译 DLL。

## 文件与接入

- 可编辑源：`Authoring/M66_small_hand_separation_v09.blend`
- 导出：`Export/SK_M66_SmallHandSeparation_V09.fbx`
- 选择记录：`Records/surface_ownership.json`
- 制作回执：`Records/skin_manifest.json`
- 目标网格：`/Game/Monsters/IncineratorBossM66/SmallHandSeparationV09/SK_M66_SmallHandSeparation_V09`
- 原角色：`/Game/Monsters/IncineratorBossM66/BP_M66RigPreview`
- 导入脚本：`import_skin.py` → `install_character.py`

状态：源文件与 FBX 已完成；2026-10-14 23:28 已后台导入并保存 V09 网格及原角色蓝图，commandlet 退出码 0。原角色已切换 V09 网格，保留 V08 横扫与 V07 物理资产。回执见 `Records/skin_import.json`、`Records/character_install.json`、`Records/install-20261014-232741/process.json`。未进行修复后的运行、截图或联机测试，由用户测试。
