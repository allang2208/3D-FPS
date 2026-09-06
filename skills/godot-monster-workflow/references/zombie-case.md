# 普通僵尸案例（2026-09-06）

这是已执行案例，参数不是所有怪物的默认值。

## 来源与资产

- 二维来源：game-dev/assets/enemies/zombie/v2/{idle,walking,attacking,dying}.png；配置 data/enemy-config.json#zombie。
- 当时生产仓库 E:/3d/3-dfps；素材 E:/无尽轮回/3d/3-dfps/tools/ai-gen/zombie-3d-v01-20260905。使用前确认路径是否仍有效。
- 身份是瘦削尸体、驼背、骨感小腿和棕色破短裤。image_gen 从原 idle 补正面 A 姿；用户自有 ComfyUI TRELLIS.2，seed 905122、512、sparse32、DC-Quad、约 3 万三角面、2048 贴图。
- Blender 脚本 rig_and_animate.py 构建 21 骨（含非变形 root）、导出 20 骨、最多 4 权重。保留 zombie-rigged.blend、zombie-preview.glb、package_preview.py、check_export.py。
- 手指随整只手变形，未逐指绑骨；头面细节为样板精度。生成背面和三维关键帧属于重建，不是自动视频动捕。

## 动作与时间合同

| 动作 | 原参考与三维实现 |
|---|---|
| Idle | 24 帧/5fps，4.8 秒循环 |
| Walk | 27 帧/12fps，2.25 秒；强腿 L 支撑 76%、抬脚 7cm，弱腿 R 支撑 48%、抬脚 1.8cm；弱侧承重下沉 4.8cm；匹配速度 0.305m/s |
| Attack | 24 帧，1 秒；短起势、转体张臂、错位扑抓、跨步、回收；接触 0.375 秒，有效区间 [8/24,11/24)，冷却 2 秒 |
| Death | 2 秒屈膝、坐倒、仰倒、伸腿躺平；终帧保留 1 秒；预览 GIF 可循环，游戏单播 |

先查看 walking 后才形成左右支撑差异；先查看 attacking 后才形成不对称扑抓；死亡同样先看原 dying。这个参考优先顺序是用户明确要求。

## 运行实现

- scripts/ordinary_zombie.gd 继承现有 enemy.gd，独立推进业务时钟与 AnimationPlayer 手动 seek。
- scenes/enemies/ordinary_zombie.tscn 引用 assets/models/ordinary_zombie/zombie_v01.glb；主场景在 (-3,0,-4) 生成并连接玩家及击杀回调。
- 等级 3、生命 120、伤害 13、物防 25；物理伤害 floor(d*60/(60+25)) 至少 1，再交 BuffSystem。元素不套物防。追击 0.61m/s，Walk 约 2 倍速；警戒 14m、起手 1.25m、命中深度 1.4m、半宽 0.48m。
- IDLE/CHASE/WINDUP/STRIKE/RECOVER/STUNNED/DYING/CORPSE；攻击锁定方向，最多一次命中，允许侧移和背后躲避，墙体遮挡；死亡 2+1 秒后移除。
- 测试 test_ordinary_zombie.gd 有 22 项通过；render_ordinary_zombie.gd 实际主场景 120 物理帧移动约 1.21m，并验证高度与 Walk。默认 D3D12 Forward+ 和 OpenGL Compatibility 均完成四姿态渲染。

## 已证明的踩坑

- 截图脚本禁用 main.process_mode 时地面物理失效，只检查平面距离仍会误判通过；修复为仅停止玩家/其他敌人的 physics_process，加高度断言。
- current_scene 必须指向已加入 root 的节点；顺序错误虽能出图仍会产生引擎错误，不能忽略。
- GIF 合并相同停留帧是正常压缩；比较总时长和关键姿态，不能仅按文件帧数报错。
- 原位动画按实际速度同步，受阻时不继续原地快走；.305 与 .61 是此模型的标定，不直接套其他怪物。

项目 docs/ordinary-zombie-integration.md 保存接入边界；runtime-tests 保存日志和截图。该轮完成自动测试与关键帧目检，未完成全程人工战斗试玩。
