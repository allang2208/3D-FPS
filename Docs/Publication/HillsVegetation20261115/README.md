# 丘陵植被、野猪与雨林水坑：2026-11-15

本批保存雨林绿色草、野猪外观与生成、动物距离休眠与肉块掉落、静止植被闪灭修复，以及待提交掉落保存、联机生态快照和扩大雨林水坑选址。

## 发布范围

- 本机生产入口仍为 D:/FPS3D/FPSGAME；活动 Content 联接到 F:/FPSGAMEData/Content。
- Sources 保存 28 个独立模块文件，source-manifest.json 记录原路径与 SHA-256。它们已在本机原生目录接入；公开根目录尚不包含完整宿主依赖，不要把本目录加入 UE 模块编译。
- Integration 为共享文件中的 16 个定向补丁。integration-manifest.json 记录每个补丁的前后 LF 内容哈希；仅在基线一致时应用。基线来自完整本机宿主逆向移除本批改动，并非公开 HEAD。16 个补丁已在独立基线副本用 git apply 重放，结果哈希一致。
- 可参考[丘陵异步入场](../HillsAsyncEntry20261112/README.md)和[丘陵联机发布](../HillsMultiplayer20261115/README.md)。共享宿主仍有未公开的地编、村庄、PCG 调度等依赖，本批是源码及定向补丁恢复包，不能视作可独立构建的完整克隆。
- History/vegetation-streaming-20261113.patch 是早期调度工作证据，不是当前安装补丁，不能覆盖较新宿主。
- Tools 下发布精确选定的制作脚本；forest_wet_materials.py 仅合入雨林掩码部分。wildlife.json 保存物种与掉落配置。共享 DefaultGame.ini 不整文件覆盖，Config/rainforest-ecology.ini.fragment 仅供合并雨林键。

## 当前实现

雨林覆盖目标为丘陵可玩面积的 30%，沿河域形成边界。绿色草使用独立数组及每网格风动边界，黄色丘陵草甸保留；淘汰的 SM_BankSedge 不在活动配方中。花朵复用村庄已使用的 Project Nature 族。

野猪沿雨林河岸林地小群生成并避开水体；普通猪不自然生成。Pig 是原包/资源目录名，物种 ID 为 boar。獠牙、灰褐皮毛、鬃毛和眼部由独立外观脚本制作。动物距所有玩家均超过 90 m 时暂停移动和 AI，靠近恢复；超过 140 m 继续既有回收。所有物种只掉 raw_meat_chunk，沿用篝火烤制定义。

待提交肉块在换图和正常退出前提交，失败保留队列并中止正常离场；World TearDown 为末帧兜底，不保证强制结束进程时保存。权威端按世界复制 NetEcology 与 SizeMeters；晚加入客机等待快照，地形、PCG、地图和动物显式使用同一份参数。双方仍需兼容的算法与资源。

水坑按实际雨林掩码全区粗筛（8 m），最多六个 64 m 地块内做 1 m 积水计算，最多 25,350 个细网格采样和八个水坑。河道、河岸和谷地道路避让保留，挖填可排水；数量受种子与适宜地形限制。

## 闪灭原因与完成状态

F6 跟踪记录 PCG 反复取消、销毁和再生成。WITH_EDITOR 下 UDynamicMeshComponent::SetMesh 即使在 PIE 也发出属性改变通知，丘陵 actor 的 PCG 追踪误将地面/河水/水坑网格提交当作输入变化，清理整层植被。修复限定同步 SetMesh 的变更来源屏蔽，并由 ON_SCOPE_EXIT 恢复，保留真实编辑与距离调度。用户已反馈该修复成功。

Evidence 保存已有采集结论和构建回执；旧 Saved 路径通过 cleanup-manifest.json 查归档地址。最近一次完整本机 FPSGAMEEditor Win64 Development 构建于 2026-11-15 16:28 CST 成功，耗时 246.02 秒，DLL SHA-256：7c11760d23ff613d5226d0d12757c3d105b6700bc0dc39a6aa08f45d21a8579d。该记录对应当时完整宿主，之后其他工作可能产生新 DLL，不证明恢复包独立构建。

最新掉落保存、生态快照和全区水坑仅完成源码与 Editor 构建，未进行新的单机、联机或视觉验收。本次整理不启动 UE、游戏、导入或制作脚本，也不借用其他批次的联机结果作为本次验收。

## 本地保留与许可

3,300 个文件（16,204,607,544 字节）及 16 个目录联接已归档到 trash/HillsVegetation20261115，逐文件 SHA-256 与联接目标读回一致。346 个图像扩展名文件包含截图、预览及诊断宿主复制纹理，不全是截图。manifest 记录精确原路径、目的地、理由及保留替代物；移动没有递归穿过联接。

正式 Content、当前 Binaries/Intermediate、存档、自动保存和制作输入保留。SourceAssets/Wildlife/Boar 保留 coat_uv.npz、T_PigDirty_BaseColor.tga、T_WL_BoarCoat.tga 和 T_WL_BoarMane.tga；独有原色输入在诊断目录归档前迁出保留。

Animal Variety Pack、Project Nature、Quixel/Fab 模型、贴图及派生二进制仅本机保留，未公开再分发。作者脚本需自行取得授权资源；离线烘焙使用 numpy、Pillow、SciPy、opencv-python，几何制作使用 Blender 或 UE Geometry Script。原始 GPU/F6 捕获、日志、临时宿主和 trash 不上传。

可复用经验已同步至个人与仓库的 ue5-pcg-building、ue5-debug-validation、ue5-save-load-replication 对应 references。
