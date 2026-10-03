from pathlib import Path
p=Path('Docs/Monsters/HangingBellM09RuntimeV04_20261003.md')
s=p.read_text(encoding='utf8')
s=s.replace('原生 Editor 基础 DLL 已后台构建成功。动画已保存；骨架收尾、音效特效、专用物理资产和地图的最终保存状态以本轮生产回执和交付说明为准。',
'''原生 Editor 基础 DLL 已后台构建成功（build_editor_v04_final.log，Result: Succeeded）。模型、骨架、材质、九段动画、七段音效、波纹模型、19体专用物理资产与测试地图均已实际保存；最后一次保存 commandlet 返回0。

生产回执 finish_commandlet_v04.json 记录 complete=true、tested=false；ue_room_saved_v04.json 记录主区59个握点／102条连接，两个侧区各12个握点／17条连接，以及专用物理资产保存成功。以上是制作与保存结果，不是运行时或视觉验收结果。未自动打开编辑器，未执行测试。''')
p.write_text(s,encoding='utf8')
p=Path('Docs/Monsters/HangingBellM09CeilingDesign20261003.md');s=p.read_text(encoding='utf8')
s=s.replace('本文件落实行为与测试环境设计，未制作关卡、运行时角色或测试入口，也未启动 UE 或运行测试。','本文件保留天花板限定设计。随后已完成 V04 运行时、动作、F6 分支和独立测试房的制作与保存，见 [V04 交付与操作](HangingBellM09RuntimeV04_20261003.md)。未运行游戏或测试。')
s=s.replace('当前 Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp 使用向下地面射线、地面导航投影和落脚净空，尚无 M09 条目，不能直接给悬钟沿用该生成路径。','Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp 已为 M09 添加独立天花板生成分支；其余怪物继续使用原地面生成逻辑。')
s=s.replace('接入时在现有 F6 生成目录为 M09 使用专用的天花定位分支：','现有 F6 生成目录为 M09 使用专用的天花定位分支：')
s=s.replace('这是制作尺寸提案，并非已保存地图尺寸。','V04 已保存主区20 m ×16 m、4.2 m顶高的地图，另在北侧增加两个高度对照房。')
s=s.replace('截至本设计落盘，只有 V03 本地绑骨产物；测试房、传送命令、悬挂动画、天花移动、战斗执行和 F6 接入尚未制作。当前换到已有测试地图并不能立即试玩悬钟。','V04 已保存 /Game/Tests/HangingBellM09/L_M09CeilingTest。手动进入游戏后输入 m09.TestRoom，再从 F6 选择“悬钟 M-09（天花板）”。房内返回门按 E，或输入 m09.Hub 返回主神空间。当前制作尚未经过用户游戏测试。')
p.write_text(s,encoding='utf8')
root=Path('SourceAssets/HangingBellM09Meshy20261003')
(root/'README.md').write_text("""# M-09 悬钟制作包

- V02：25个组织对象拆分，保留源UV和PBR。
- RigV03：113根导出变形骨和8个Blender控制骨，专用悬挂骨架及蒙皮。
- MotionV04：九段原创动画、七段原创合成音效、鸣震波纹，以及UE导入/构建/保存回执。
- 当前UE目录：/Game/Monsters/HangingBellM09/V04。
- 测试房：/Game/Tests/HangingBellM09/L_M09CeilingTest。
- 操作说明：工程 Docs/Monsters/HangingBellM09RuntimeV04_20261003.md。

已后台制作、构建并保存。未自动进行游戏、姿态、性能或多人测试，由用户体验。
完整模型保留约189万三角面；尚无性能LOD。
""",encoding='utf8')
