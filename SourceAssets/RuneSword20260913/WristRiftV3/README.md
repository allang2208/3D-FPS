# 双手符文剑 WristRiftV3

本轮用户要求：待机剑身转 90°、减少挥砍时腕部扭曲、拆分蓄力/快速斩击/回收、快速斩击速度提升 100%、利用现有资产添加空间扭曲剑气。

## 制作与接入

- 待机剑身在 V2 基础上绕剑长轴转 90°，护手中心继续使用相机作者坐标 `(13,48,-8) cm`。剑的宽面趋于与前视方向平行。上下两处握位仍是护手下方 9 cm / 21.5 cm。
- V2 作者姿态显示横扫时握手方向和前臂轴线发生大幅反折，原固定肘 pole 不能支撑横置剑柄。本轮保留既有 Manny 手臂、手套、骨长、蒙皮与手指包握，重新求解绕柄握向、支撑肩位和肘部弯曲平面；前臂主骨承担轴向姿态，两个 twist 辅助骨按实际骨段位置分担，避免腕骨单独承担全部扭转。该解算是第一人称无躯干视模专用制作，不能直接用于全身角色。
- 六条动画统一以 240 Hz 烘焙，Idle / Walk / Equip / Sprint 同步新握姿。两段横扫仍分别右→左、左→右，接触阶段保持 160° 方向跨度。

### 时间映射

| 阶段 | V3 游戏时间 | 处理 |
|---|---|---|
| 蓄力起势 | 0–0.230 s | 保留准备节奏，转向侧方 |
| 快速横扫 | 0.230–0.345 s | V2 的 0.230–0.460 s 压缩至一半，速度 2× |
| 惯性收势、回到待机 | 0.345–0.8333 s | 用余下时间平顺回收，恢复上下双手握姿 |

总动作周期继续为 20/24 s，角色攻速和强化照常作用在周期上。声音触发点仍是 0.230 s，命中窗口截止改为 0.345 s，接触采样提高到 240 Hz 并显式处理窗口边界。运行时由当前动画版本规定时序，避免旧存档中 `contact_end=0.46` 让收剑阶段继续造成伤害。物品定义及初始安装脚本也已同步新值。

## 空间扭曲剑气

本机已存在可用资源。读取到 `/Game/RPGEnvironmentVFX/Essentials/Materials/M_HeatDistortion` 使用 Index Of Refraction，且 Normal / Refraction 输入有连接；`NiagaraExamples` 和 `Realistic_Starter_VFX_Pack_Vol2` 也有扭曲材质。读取结果保留在 `existing_vfx.json`，不视为渲染验收。

实际实现复用 `/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A`，参考现有热扭曲的折射方式，新建：

- `/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift`：双面半透明、景深前绘制、深度检测开启，流动法线造成背景折射；柔化边缘并带一条淡苍蓝高光。动态参数 `SweepProgress` 控制沿轨迹展开，`RiftFade` 控制消散，`RiftStrength` 默认 0.085 控制折射强度。
- 同目录 `SM_RuneRift_Slash1` / `SM_RuneRift_Slash2`：由各自快速阶段的真实作者剑刃轨迹制作弧面，UV 的 U 对应挥砍时间、V 对应剑刃宽度。
- `URuneSwordComponent` 在接触开始时选择对应弧面，按攻击快照的攻速展开；展开后 0.20 s 内消散，并以 85 cm/s 向发出方向移动。发出后保持世界空间变换；切武器、菜单、死亡、攀爬等取消路径关闭效果；组件退出时销毁。

剑气是外观效果，仍由剑刃原有接触扫掠结算伤害；没有添加远程伤害或改变 1.8 m 距离上限。未复制或修改第三方原始资产，原许可继续沿用已安装素材包，不公开发布素材源。

## 文件

- `build_sword.py`：完整动画作者入口及剑气弧面生成入口。
- `AzureRunesword_Manny_Editable.blend`：当前双手、剑体和六条动作的可编辑源。
- `Export/`：六条动画 FBX、两张剑气弧面 FBX；剑体网格 FBX 随源保存，本轮无需更换手持剑体网格。
- `import_revision.py`：六条动画、剑气材质及弧面导入入口。
- `Before/`：导入前动画/骨架 uasset、切换前模块清单备份；V2 的 blend 与 FBX 保留于父目录的 `ReachSweepV2/`。
- `authoring.json`：制作参数及时间合同；`import_receipt.json`：资源导入回执。
- `read_wrist_source.py` / `wrist_source.json`：本轮腕部问题的源姿态定位记录。
- `build_editor.log` / `build_suffix.txt`：本轮必要 Editor 构建记录，模块组后缀 `913220329`；`install_binaries.py` 按该后缀设置 FPSGAME 与 AutoFootstep 两个模块的清单。

## 交付边界

Blender 制作及必要 Editor 构建完成。UE 导入脚本执行完成并保存六条动画、折射材质、两张弧面；进程因已有 GameFeatureData 配置错误和 127.0.0.1:8000 监听占用返回 1。首次创建 `M_RuneRift` 前尝试加载同名资源产生一条不存在提示，随后脚本创建并保存该新材质。完整日志保留于 `import.log` / `import_console.log`。

按照用户规则，未启动游戏、执行回归、渲染预览或视觉验收。实际腕肘轮廓、挥砍力度和折射效果需由用户重新打开 UE 工程后测试；不宣称它们已通过实机验收。
