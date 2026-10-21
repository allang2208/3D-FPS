# 玩家身体共享配置的修改与发布

适用于 `Content/ColdSteelData/player_body.json`，包括第三人称动作、第一人称身体、衣物和头部装备。它们共享一个文件，字段归属不同；以当前用户要求为修改边界。

## 这次排查发现的问题

2026-10-20，战锤 39 个动作入口全部缺失，21 个动画包和运行时处理仍在。本次恢复基准与 V7/V8/V16/V17/V18 的保存回执一致，见[恢复记录](../Weapons/steel-warhammer-third-person-routes-restored-20261020.md)。

尚未查实哪次操作删除了入口，但现有流程存在三个具体缺口：

1. `Tools/PlayerBody/publish_jason.py` 是早期初始化器，会整份赋值 `cfg['clips']=clips`，还会覆盖身体设置。它已停用，保留源码用于追溯；重新执行会在任何业务读写前报错。
2. 多个脚本先读取配置，完成其他处理后再整份写回。即使脚本只主动改一顶帽子，旧内存副本仍可能覆盖期间新加入的动作。部分脚本已有写前比较，但并未统一。
3. `published.json`、`assets-published.json` 经常只表示本地资产接入。它们没有证明所需动作配置和消费者源码进入提交。旧发布参考还误写“ColdSteelData 不进提交”，应以具体路径的实际 Git 跟踪和忽略规则为准，不能整体排除必要配置。

这些是已发现的风险，不是对某个会话的归责。

## 修改共享配置

使用 `Tools/PlayerBody/config_transaction.py` 的 `commit`，在开始准备修改时捕获原始字节，声明精确字段归属：

```python
import json, runpy
from pathlib import Path

root = Path("D:/FPS3D/FPSGAME")
path = root / "Content/ColdSteelData/player_body.json"
before = path.read_bytes()
candidate = json.loads(before.decode("utf-8-sig"))
role = "Warhammer.FullBody.Slash3"
candidate["clips"][role] = new_saved_asset
commit = runpy.run_path(str(root / "Tools/PlayerBody/config_transaction.py"))["commit"]
receipt = commit(path, before, candidate,
                 owned_paths=[("clips", role)], producer=__file__)
```

- 动作逐个列出角色键，不能声明整个 `clips`；帽子只声明自己的 `head_equipment/<物品键>` 或具体叶字段。
- 写入器按字段差量编辑当前读取的原文，保留其他字段、顺序、BOM 和换行；删除已有键、越界修改和重复 JSON 键会被拒绝。
- 配置在准备期间变化，或另一个使用此工具的写入者持有锁时，停止本次写入。重新读取并重新合并，不重复提交旧候选，不请求其他会话让位。
- 使用系统自动释放的文件锁和同目录原子替换。每次实际修改独立保存 `Saved/PlayerBodyConfigWrites/<时间-唯一标识>/before.json`、`after.json`、`receipt.json`，记录脚本来源、字段和散列；无改动不覆盖原回执。
- 不允许把 Git HEAD、暂存用裁剪内容、历史完整备份复制到真实工作配置。备份只用于提取本次明确需要恢复的字段。
- 此写入器默认不支持删除键。明确要求退役动作时，单独列出要删除的键和消费者变化，制作专门迁移；不能借整份字典替换隐式退役。
- 配置锁只保护采用同一工具的写入者，不能拦截手工编辑或外部 `git restore`。因此新脚本、临时脚本和旧脚本重用都要遵守此入口，不能声称全工作区已被强制锁定。

当前已接入保护的入口：

| 范围 | 脚本 |
| --- | --- |
| 钢盔 | `Tools/SteelArmet/publish_reference_match.py`、`publish_wide_visor.py`、`publish_crown_refine.py`、`publish_black_frame.py` |
| 其他头部装备 | `Tools/BlueMageHat/publish.py`、`Tools/FieldHat/publish.py` |
| 第一人称共用身体 | `Tools/FirstPersonLegs/publish_shared_body.py` |
| 当前战锤制作版本 | `SourceAssets/WarhammerThirdPersonSevarog20261016/{AnatomicalGripV7,RefinementV8,SourceGripV16,NaturalComboV17,Slash3AlignmentV18}/publish.py` |
| 弓与赤霄重击 | `SourceAssets/BowSparrowThirdPerson20261018/publish.py`、`SourceAssets/Zhanmadao20261018/ChixiaoDoubleHeavyV1/publish.py` |
| 本次恢复 | `Tools/PlayerBody/restore_warhammer_routes_20261020.py` |

V7/V8 发布器另加已有版本判断，不能重跑旧混合动作集覆盖后来的普攻版本。其他历史制作脚本未全量迁移；重用前必须改为上述写入入口，并确认它仍是当前版本。只读脚本和只写作者输出的脚本不属于配置写入者。

多文件发布仍不是一个跨文件事务；配置冲突时保留已写出的其他独立产物并报告阶段，不能宣称整批完成。

## 确保发布包含功能依赖

只有用户授权发布时执行以下发布步骤，不因此启动游戏测试或 UE：

1. 列出本次功能的运行代码、动作配置键、已保存资源、本地恢复输入。原始或未核准二进制仍按资源许可规则保留本地；不能因为二进制不公开就漏掉文本动作配置。
2. 混合文件构造暂存内容时读取当前索引 `git show :<路径>`，保留其他已暂存内容。只有确认索引与 HEAD 相同才可用 HEAD 为基底；更新索引前确认原 blob 未变化。临时索引内容只写独立临时路径，绝不落回真实工作文件。
3. 核对本功能必需的具体动作键和值进入实际暂存内容。不要把“没有带上别人修改”当作“功能依赖已经完整”。发现所需源码或配置不在本次允许发布范围，明确标注部分发布，不悄悄省略依赖后宣称完整发布。
4. 提交后对该提交重复读取指定字段；推送后记录远端分支及包含该提交的证据。Git 推送成功只证明提交到了远端，不证明本地未提交动作也到了远端。

本次战锤恢复的可追溯清单：`Docs/Weapons/warhammer-third-person-restored-manifest-20261020.json`。它记录 39 个角色、21 个本地包与 6 个消费者源文件。它是恢复时的集成快照，不是新的用户视觉验收。后续有意升级动作时生成对应新清单，不永久锁死为这一版。

可用的只读配置发布核对命令：

```powershell
python Tools/PlayerBody/check_publication.py --manifest Docs/Weapons/warhammer-third-person-restored-manifest-20261020.json --revision :index --output Saved/PlayerBodyPublication/staged.json
python Tools/PlayerBody/check_publication.py --manifest Docs/Weapons/warhammer-third-person-restored-manifest-20261020.json --revision HEAD --remote origin --branch main --output Saved/PlayerBodyPublication/remote.json
```

工具不暂存、提交、推送或 fetch，只读取指定索引/提交和可选远端分支；缺失字段或必要源文件返回非零。远端历史本地不可见时，明确标为未知，不自动取回。证明范围是所列配置值和源文件存在，不证明全部 C++ 差量、二进制、构建或游戏表现。

2026-10-21 修订：远端祖先关系不足以证明当前版本仍有这些内容；工具还核对远端当前分支尖端，后续删键/缺失源码会拒绝通过。战锤清单同时列出五个必需 Cook 目录并核对 `DefaultGame.ini`；此项证明显式打包规则存在，不代表已执行 Cook。配置写入器现支持首次创建父对象，同时禁止将已有对象替换成 null/标量来绕过删键保护。详细复查见 [动画与联机复查](../Weapons/animation-handoff-network-review-20261021.md)。

## 交付状态

分别报告“源码修改”“资产保存”“本地配置接入”“Git 提交 SHA”“推送远端”“用户视觉认可”。旧 `published` 字段保留兼容含义为本地接入；新写入回执的 `git_commit`、`git_push` 默认空，不能由本地脚本自动写成已推送。

本次工作流排查只在隔离临时目录复现配置丢失和并发覆盖，记录于 `Saved/WarhammerThirdPersonRestore20261020/workflow-review.json`。未重跑真实发布脚本、启动 UE 或运行游戏；后续普通开发不自动运行这些排查用例。

本轮记录：8 种隔离写入情形均得到预期结果，真实配置在排查前后 SHA256 均为 `2ebed71b320b00edc124c505cc4546c18f8b53c5fccb3c21970f43a0a3bf9481`。只读 Git 核对时，当前提交及远端 main 已推进到 `fced88da2025c51f96b436bb0217f75b59e3120a`；该提交仍缺失清单内 39 个动作入口及 `Source/FPSGAME/Characters/FPSBodyWarhammerMotion.h`。这不影响上一轮已经落盘的本地恢复，但不能报告为完整推送。详见 `Saved/WarhammerThirdPersonRestore20261020/publication-review.json`；本轮没有暂存、提交或推送。
