FPSGAME 宝箱 v3 · 线条与留白修订

本版依据“线条流畅一些，不要叠加在一起”调整装饰，未修改本地正式 UE 工程。
前板与盖侧改为两条平滑渐细的卷线和独立中叶，留出可见空隙；锁板只保留两片安静的叶形；顶徽章只保留一道细边框与相互分离的花瓣。未继续增加装饰密度。
V2 已保留为备份。

打开模型：需要前三个普通 ZIP
1. TreasureChest_v3_Core.zip
2. TreasureChest_v3_Metal_Textures.zip
3. TreasureChest_v3_Wood_Textures.zip
把三个 ZIP 解压到同一个目录，合并其中的 TreasureChest_v3 文件夹，然后打开 TreasureChest_v3/TreasureChest_v3.blend。
正确目录应为：
TreasureChest_v3/TreasureChest_v3.blend
TreasureChest_v3/Textures/（九张 PNG）
不需要分卷工具，也不用更改文件名。模型用相对路径读取纹理；原图字节、分辨率和材质质量均未降低。
如出现粉色材质，说明纹理包未解压到同一个 Textures 文件夹。

可选下载
- GLB：模型、原骨架与开盖动画、内嵌便携 PBR。
- FBX 与 PortablePBR：两个普通 ZIP 解压到同一目录，得到 FBX 与配套便携 PBR。
- Previews：装饰细节检查图、最终闭合与打开图，均为真实 Blender 渲染。

保留内容与验证边界
箱体结构修复、斜接框架、完整空心细框、贯穿钥匙孔、释放槽搭扣、PBR、Root/Lid 骨架与原 30 fps / 1 秒开盖动作均保留。
v3 在 Blender 5.2.2 中检查：158,044 三角面；0 边界边、0 非流形边、0 退化几何三角形、0 坍缩 UV 三角形。新增曲线采样用于更平滑的转弯。
UV0_Physical 为第 0 通道，UV1_ComponentWear 为第 1 通道。
此版没有在 UE 中完成新的导入、光照、碰撞、LOD 或性能验证。
完整外观以 Blender 源文件为准；FBX/GLB 的便携 PBR 不含依赖几何的边缘抛光，FBX 材质解释依赖导入器。
便携 NormalGL 为 OpenGL 约定；UE 若按 DirectX 解释法线需翻转绿色通道。源文件使用的原图与节点转换保留不变。

源文件与脚本
源模型保留可编辑分件。scripts/refine_ornament_v3.py 记录这次流畅、分离装饰的制作过程；可以在 Blender 5.2.2 下从同目录源模型重新生成修订副本。脚本输出到 working，不覆盖作为输入的主文件。
reports 包含几何/UV 检查、FBX/GLB 回读和纹理文件校验信息。
所有交付 ZIP 小于 40 MiB。
