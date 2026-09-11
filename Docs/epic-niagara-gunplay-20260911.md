# Epic Niagara 枪口效果接入（2026-09-11）

> 当前运行与重建入口为 V5；下文 V2–V4 为历史验证记录。旧候选和生成脚本已按 [归档清单](gunplay-archive-20260911.json) 移入 trash。


来源：用户已导入 Epic Games Niagara Examples Pack。Fab：https://www.fab.com/listings/0e188eca-4e54-4fb2-a9ed-d8b8a565e600 。源资产 /Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash 及其材质、序列贴图；保留原资产，不覆盖官方包。

运行副本：/Game/Weapons/GunplayFX/NS_FPS_MuzzleEpicV2、NS_FPS_BarrelSmokeEpicV2。前者保留中心、正面、侧面火光及烟雾，后者只保留烟雾。独立单次发射生命周期；火光寿命 0.025–0.055 秒，烟雾 0.55–0.95 秒。移除官方弹壳发射器，继续使用现有抛壳。脚本 Tools/AssetPipeline/build_epic_gun_fx.py 可重建副本；资产被其他编辑器占用时需另用候选名称，不关闭用户进程。

FPSWeaponFXComponent 使用 24 个组件上限的复用池。每次开火从有效枪口创建官方效果，火光随枪口更新，烟雾沿用源发射器的世界空间模拟。普通枪口尺度系数 0.22，消音器 0.07，ADS 额外乘 0.78；火光颜色从官方资产默认 HDR 值读取（100, 23.909069, 1.215285，alpha 0.5），RGB 乘 0.3 适配第一人称。余烟由已有枪管热量按 0.11 秒间隔驱动，缩小且降低透明度，冷却后停止。原始卡片火光/烟雾仅在缺失新资产时回退，不与新特效叠加。切枪及 EndPlay 清理组件。

仅替换视觉层；瞄具弹道、后坐力、枪口改装出口、弹伤、曳光和命中提示沿用现有逻辑。测试扩展为核对官方资产实际加载、逐发触发数量、余烟发射和冷却后所有 Niagara 组件结束。

首次新进程回归 64 项通过；画面检查发现最初覆盖的火光颜色过暗，已改为读取官方原始颜色，并再次录制。原始素材和 VFX 的归属沿用 Fab 领取许可，本次没有对其作公开再分发。

最终验证：UnrealEditor-FPSGAME-9111622.dll 编译成功。新进程日志 Saved/BallisticPresentationAudit-20260911124721.log，64 项通过、0 失败，逐发火光数量与实际 ShotsFired 相同；热量耗尽后活跃 Niagara 组件为零。已查看腰射火光、ADS 与烟雾画面。Saved/BallisticPresentationAudit/epic-niagara-gunplay.gif 和 .mp4 为本次真实游戏截图按 60 Hz 时间轴合成，预览无音轨。中间一次运行受桌面鼠标输入干扰，现仅在审计进程中屏蔽视角/移动输入。未做独占硬件性能基准；旧编辑器需重启以加载新模块。
