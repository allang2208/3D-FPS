# 缚群 M-88：一次快速近战挣脱与连续软体死亡 V32

## 请求与制作范围

用户将快速近战挣脱改为一次，并要求按此前死亡方案重做。此前方案指 M-14 V19 的连续 XPBD 软体倒伏、落地和摊开，不是重复播放旧线性 DeathV3。保留活体 V29 模型、30 m 触手、V25 衣物、已认可 V28 拍击和既有战斗数值。

- 快速近战在实际接触时刻命中一次解除束缚，HUD 的次数读取同一常量，缠绕说明同步。射击挣脱仍为触手独立 300 生命。
- 死亡时先捕获正在显示的姿态，再释放玩家、停止攻击与更新死亡状态；避免先重置触手驱动再采样尸体。
- 独立 DeathV32 尸体资源；躯干采用连续四面体场，肢体与攻击触手沿真实骨链建立截面站点，通过实际父级附近的体积连接到主体。相邻腿、盘绕触手不能按空间近邻焊成同一块。
- 站点保留显式原骨架初始化权重；其后仅由共享软体求解器驱动。无旧死亡片段与刚体双重驱动，沿用 120 Hz / 每帧最多六子步、700 节点上限、尸体预算与稳定休眠。
- 复用 V29 尸体的变形法线材质，保持原 UV、衣物和伤口参数；仅尸体 LOD0 重绑，不切换到旧蒙皮 LOD。

## 重建输入及接入

- `Tools/BoundCongregate/prepare_death_v32.py`：从当前活体派生独立尸体，导出表面和原始蒙皮。
- `Tools/BoundCongregate/author_death_v32.py`：生成连续解剖代理、正权重表面嵌入及作者记录；不运行模拟或渲染。
- `Tools/BoundCongregate/install_death_v32.py`：构建并保存独立尸体网格、骨架和 DataAsset，最后只替换活体网格的死亡绑定。
- `SourceAssets/BoundCongregateMeshy20261006/DeathV32/`：作者输入、代理、嵌入、生产收据及本次构建记录。
- 正式资源目录 `/Game/Monsters/BoundCongregate/DeathV32`；原 RigV3 DeathClip 仅保留为资源缺失时的旧回退，不是此次正常死亡路径。

## 状态

Editor、Game 常规构建均为 `Result: Succeeded`，记录分别为制作目录下 `build-FPSGAMEEditor.log`、`build-FPSGAME.log`。Live Coding 请求的连接中断不作为构建成功依据。

代理制作完成：693 节点、1446 四面体、2782 条体积边；13 条肢体／器官分支与躯干连接。四角截面按原始表面逐步拟合，近主体组织包含在连续体积内，125641 个独立表面位置使用局部正权重绑定。具体参数和作者输出见 `authoring.json`。

最终通过已运行编辑器的互斥桥完成保存：`SK_BoundCongregate_CorpseV32`、`SKEL_BoundCongregate_CorpseV32`、`DA_BoundCongregate_CorpseV32`，以及当前 V29 活体网格上的死亡绑定；`delivery.json` 为 `complete: true`，`install-bridge-final-02.txt` 返回 `BOUND_DEATH_V32_SAVED`。活体几何、活体骨架与攻击资源引用保留，切换前的活体资产包备份在 `before/`。

本轮未运行游戏测试、动画预览或渲染；此前 V31 检查通过数字不作为 V32 验收证据。用户明确授权停止当前 PIE 以继续接入，未主动启动编辑器或游戏。死亡画面、落地细节及多人表现交由用户测试。
