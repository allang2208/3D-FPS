# 突变体-3：跑步与受击替换

**后续反馈（2026-09-15）：** 用户已明确否定本版 Running / RunFast 的跑姿，认为不如先前 Meshy 独特奔跑。本版跑步属于已安装但被判不合格的历史结果，不能作为后续动作模板。用户选择继续推进 MoCap Online Hyper Chase，当前缺少该源文件，见 [../hyperchase/README.md](../hyperchase/README.md)。Hit_Chest 不在此次跑步替换范围内。

用户报告原 RunFast 跑姿奇怪、受击直接躺倒。本次仅替换正式路径中的 `A_Mutant3_Running`、`A_Mutant3_RunFast`、`A_Mutant3_Stagger`，原始模型、蒙皮、材质、Walking、待机、攻击、死亡、物理与 C++ 战斗逻辑不改。

动作库在 2026-09-15 查询的 HEAD 为 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`，与原来缓存相同。两份人形库没有专门命名的 Zombie Run 动作。查看了 Jog、Run_Stealth、Zombie_Walk_2、Hit_Chest、Hit_Head、Hit_Knockback 的官方视频。

旧成品实际姿态读取见 `read_current/`：RunFast 大幅前倾甩臂，Stagger 在 0.1 s 已经双脚离地、双臂抬起，后段继续躺倒。这来自 Hit_Knockback 源动作的倒地过程，上一版把它直接纳入受击恢复段，源动作选择不符。

新跑步以 Jog 步态为主体，保留骨盆、双腿和交替迈步；只对脊柱与头部加入 16%、手臂加入 12% 的 Zombie_Walk_2 姿态。它是对动作库的适配，不是库内原名为“僵尸奔跑”的动作。Running 0.8 s、RunFast 0.65 s，沿用原有速度控制，移除周期净水平漂移、保留腾空起伏并处理末尾 50 ms 循环衔接。

新 Stagger 改用 **Hit_Chest**，不含任何 Knockback/倒地键。源动作约 0.4 s，读取到胸部反应峰值位于原片段 75%（约 0.3 s），重排到成品 0.1 s；保持至 0.6 s，最后 0.3 s 收势。成品总长仍为 0.9 s，对应现有反应时钟；世界击退仍由战斗组件立即执行，弹反倒放 0.3 s 的合同不变。

制作入口：`prepare_sources.py` → 在原独立 UE 制作工程运行 `retarget_sources.py` → `author_replacements.py` → `import_replacements.py`。最后关闭 FPSGAME 编辑器，在 FPSGAME 制作命令中执行 `install_replacements.py`；该步骤保留旧三个包，再导入正式资源并更新主合同。`installed.json` 是实际安装结果。

最新可编辑源为 `Mutant3_Meshy_Animated_Revision2.blend`，其中保留其余动作，并把旧三个动作命名为 BeforeRevision2。引擎输入位于 `final/`，原生重定向保留在 `native_retarget/`。重建完整怪物时，先运行上一版基础流程，再执行本次替换流程。

本次按用户要求读取了旧动作与源参考；没有启动游戏或做运行回归，替换后的游戏表现由用户测试。本次只改动画资产，无须重新编译 C++。

来源：[Mesh2Motion 官方动作库](https://github.com/Mesh2Motion/mesh2motion-assets)、[固定版本源 GLB](https://github.com/Mesh2Motion/mesh2motion-app/tree/2d3d1ff03247d9e7e830d1ae375653da4e2146e2/static/animations)。动作采用 CC0-1.0；许可副本与散列沿用父目录的 source_manifest.json。用户 Meshy 模型的授权独立于 CC0 动作。
