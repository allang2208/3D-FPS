"""Prepare scoped publication candidates; never rewrite shared runtime sources."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/MonsterRagdollPublication20261003'
PERSONAL = Path('C:/Users/allan/.codex/skills')
OUT.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')

def head(path):
    result = subprocess.run(['git', 'show', 'HEAD:'+path], cwd=ROOT, capture_output=True)
    return result.stdout.decode('utf-8') if result.returncode == 0 else ''

def read(path):
    return (ROOT / path).read_text(encoding='utf-8-sig')

def append(path, block):
    data = path.read_text(encoding='utf-8-sig')
    if block.strip() not in data:
        path.write_text(data.rstrip()+'\n\n'+block.strip()+'\n', encoding='utf-8')

def skill_append(relative, block):
    for base in [ROOT / 'skills', PERSONAL]:
        append(base / relative, block)

human = '''## 巫婆接地与收尾的可复用经验（2026-10-03）

- 布娃娃没有启用时，先区分刚体不存在、预算拒绝与物理已接管。`NoCollision` 配合未强制创建物理状态会销毁查询刚体；准入前先创建有效身体、提交当前动画姿势，再计数及申请预算。不能根据角色胶囊接地或 `IsSimulatingPhysics` 单个布尔值推断全身落地。
- 长袍的活体布料与尸体显示分开：巫婆步行继续原模型、原布料和动作；击倒／死亡使用同骨架的连体裙身与完整腿部蒙皮，脚不拆成独立掉落组件。恢复站姿后重置布料，并渐进恢复显示权重。末端长袍范围约束放在步幅、FootPlacement、LegIK 之后，仅行走／起身启用，不能作用于已模拟尸体。
- 自然倒地要让关节和重力决定姿势。承重碰撞面实际接地且连续低速后，保存停止模拟前的完整求解器快照；尸体不再另转胸背或脚。预算不足的动画回退才做整体支撑高度调整。标准起身先重定位胶囊、转换快照根坐标，末端按恢复地面修正整体高度；腿部外观约束按衣物实例制作，不改写通用标准动作。
- 独立法杖脱离握持时继承手部线速度／角速度，关闭自动焊接、使用 Movable 与完整简单碰撞，由物理自由落地。凸包数量不能证明覆盖：巫婆旧八个凸包只覆盖骷髅，修复在临时碰撞网格焊接重合边并保留全部部位后合并形状，视觉网格不改。不要用指定平躺旋转或补造冲量掩盖缺失的杖身碰撞。
- 冻结后的优化集中在死亡路径：停用角色、战斗、移动、网格与布料计算，保留尸体寿命、奖励、状态效果及独立道具回收。所有怪物身体共享活跃数／刚体数／新尸体准入预算，独立道具不在此额度内；活体倒地中死亡保留已有名额，因此新尸体额度不是全场尸体硬上限。
- 保存完整 LOD0 姿势再允许已有自动 LOD。网格 Tick 已停时，仅 `SetForcedLOD(0)` 不会推进预测层级；共用弱引用列表低频调用 `UpdateLODStatus`，仅层级变化时零步长评估冻结快照并刷新骨骼，空列表停止调度。不要用低 LOD 采样覆盖完整快照，也不能把不存在的低 LOD 当成优化收益。

巫婆效果由用户认可；推广与预算改动只完成源码、资产保存及常规构建，未测帧率。发布／恢复及旧快照归档见工程 `Docs/Monsters/monster-ragdoll-publication-20261003.md`。
'''
skill_append('ue5-monster-workflow/references/humanoid-knockdown.md', human)
skill_append('ue5-monster-workflow/references/nonhumanoid-ragdoll.md', '''## 死亡与性能的共同边界

定姿后的死亡角色、战斗、移动、网格和布料计算统一退出；多 LOD 尸体复用世界级低频层级变化刷新，完整快照保留。具体规则见 [人形布娃娃的接地与收尾经验](humanoid-knockdown.md)。原查询物理资产不等于可模拟资产：巨手另建连接掌腕／指链的死亡资产，保留活体查询和专用起身。独立掉落道具继续其物理与回收，不因角色 Tick 停用而被锁成竖立姿势。
''')
skill_append('ue5-monster-workflow/references/feral-humanoid-pounce.md', '''## 手部修订恢复与废案边界（2026-10-03）

当前恢复依赖为干净身体源 → V2 制作源 → V3 翻掌／空中 → V4 落地腕 → V5 蓄力臂链；安装依次覆盖 V3、V4 落地、V5 蓄力。V2 的手掌方向被否定，但其制作源仍被 V3 读取，不能按“旧版”整体移走。首版 PalmDown、旧 V2 安装入口、覆盖前包及自动备份已入 `trash/monster-ragdoll-retired-20261003`；正式重建不读 trash。用户只确认起跳和空中方向，落地与蓄力的后续修订未获认可。发布范围与恢复说明见工程 `Docs/Monsters/monster-ragdoll-publication-20261003.md`。
''')
gun = '''# 枪击反馈与控制状态分离

用于“枪械默认不硬直，但要看得出命中”的现有怪物迭代。

- 伤害、削韧、控制和动作时钟仍归原结算入口；枪弹接触只向共享骨骼网格提交短时局部姿态脉冲，不进入硬直／眩晕、不打断攻击、不改变位移。
- 用实际命中骨与解剖父链选回弹关节；胶囊命中才按接触点使用缓存的骨架／物理资产关系。避免根、骨盆和装饰骨，腿部反馈保留远端支撑。
- 有界叠加、快速偏转、小幅反向回弹、平滑归零；连续命中不能无限累积。FPSGAME 当前为最多四脉冲、全身合计七度、0.26 秒，重型角色 0.30 秒并减小幅度，属于本例参数。
- 在原动画最终求姿态后叠加；死亡、受控倒地、起身或物理接管时停止并清空，不重新摆正尸体。魔法局部反馈、冻结尸体再受击和网络广播按另行需求接入。
- 首次命中／资产更换时缓存关系，空闲无回弹姿态计算；复用现有网格路径，不新建逐帧调度或全场扫描。

当前源码与普通构建记录：工程 `Docs/Monsters/monster-gun-hit-feedback-20261002.md`。未进行运行和视觉测试，幅度仍由用户测试；巫婆布娃娃的认可不覆盖枪击反馈。
'''
for base in [ROOT / 'skills', PERSONAL]:
    (base / 'ue5-monster-workflow/references/gun-hit-feedback.md').write_text(gun, encoding='utf-8')
skill_append('ue5-monster-workflow/SKILL.md', '''枪械默认无硬直但需要局部身体回弹时，读 [枪击反馈与控制分离](references/gun-hit-feedback.md)；不把姿态脉冲当成击倒或布娃娃。布娃娃与飞扑修订的保留输入、归档和公开源码边界见工程 `Docs/Monsters/monster-ragdoll-publication-20261003.md`。
''')
skill_append('ue5-performance-packaging/references/fpsgame-performance-development.md', '''## 怪物倒地与尸体预算（2026-10-03）

身体物理统一受活跃怪物／刚体总数／新尸体准入预算约束；尸体必须真实接地并持续稳定才定姿释放，不能为性能按期限冻结半空姿势。死亡定姿后关闭角色、战斗、移动、网格与布料的剩余计算；现有多 LOD 用共享低频、仅层级变化刷新保留的完整快照。无低 LOD 资产不承诺减面收益，法杖等独立道具另计。实施细节集中在 [怪物接地与收尾](../../ue5-monster-workflow/references/humanoid-knockdown.md)，本次来源为工程 `Docs/Monsters/monster-ragdoll-performance-20261003.md`；普通构建成功与实际性能测量分别报告。
''')

packs = ['MonsterRagdollCore20261002', 'NonHumanoidRagdoll20261002',
         'MonsterGunHitFeedback20261002', 'WitchCorpseGround20261002',
         'WitchCorpseFollow20261002', 'WitchCorpseContact20261002',
         'WitchGetUpRobe20261002', 'WitchGroundContact20261002',
         'WitchStaffDrop20261002', 'WitchPhysicalSettle20261003',
         'WitchLegRestore20261003', 'MonsterRagdollStandard20261003',
         'MonsterRagdollPerformance20261003', 'MonsterRagdollPublication20261003']
ignore = '# Monster ragdoll publication 20261003: recipes/prose only; local assets, snapshots and receipts excluded.\n'
for pack in packs:
    ignore += f'/SourceAssets/{pack}/**\n!/SourceAssets/{pack}/**/\n'
    for extension in ['py', 'ps1', 'md']:
        ignore += f'!/SourceAssets/{pack}/**/*.{extension}\n'
ignore += '!/SourceAssets/MonsterRagdollCore20261002/provenance.json\n!/SourceAssets/MonsterRagdollCore20261002/Reference/AlsCharacter_Actions.cpp\n/SourceAssets/MonsterRagdollPublication20261003/Candidates/\n'
append(ROOT / '.gitignore', ignore)
mutant_ignore = '# Pounce hand revision recipes; donor samples, binaries and local receipts stay local.\n'
allow = {
    'pounce_takeoff_hands_v2_20261002': ['author_takeoff_hands.py'],
    'pounce_forward_flip_v3_20261002': ['author_forward_flip.py', 'install_forward_flip.py', 'install_materialized_tracks.py', 'prepare_asset_save.py'],
    'pounce_landing_wrist_v4_20261002': ['author_landing_wrist.py', 'install_landing_wrist.py', 'prepare_asset_save.py'],
    'pounce_open_windup_v5_20261002': ['author_open_windup.py', 'install_open_windup.py', 'prepare_asset_save.py'],
}
for folder, names in allow.items():
    mutant_ignore += ''.join(f'!/{folder}/{name}\n' for name in names)
append(ROOT / 'SourceAssets/Mutant3Khaimera20260923/.gitignore', mutant_ignore)

asset_section = '''## 怪物布娃娃、巫婆与飞扑修订（2026-10-03）

恢复连体巫婆 CorpseFollow、专用完整法杖碰撞、巨手死亡 Physics Asset，以及突变体 V3 空中／V4 落地／V5 蓄力动画。公开运行源码、原创制作脚本、ALS 固定修订与 MIT 许可、制作及归档说明；Meshy／Epic／第三方模型、采样姿势、UE／Blender／FBX 包和构建产物留本机。115 个退役文件（约 98.57 MiB）已带散列移入 `trash/monster-ragdoll-retired-20261003`。完整输入、重建顺序和本轮未测试范围见 [怪物布娃娃整理发布](Monsters/monster-ragdoll-publication-20261003.md)。纯源码克隆不包含这些运行内容。
'''
asset_path = ROOT / 'Docs/AssetSetup.md'
asset_data = asset_path.read_text(encoding='utf-8-sig')
if asset_section.strip() not in asset_data:
    first, rest = asset_data.split('\n', 1)
    asset_path.write_text(first+'\n\n'+asset_section.strip()+'\n'+rest, encoding='utf-8')

# Publication candidates for shared paths derive from HEAD or drop only clearly
# unrelated changes. The working source and other sessions' index are untouched.
candidates = {}
def candidate(path, data=None):
    data = read(path) if data is None else data
    data = data.replace('\r\n', '\n').rstrip()+'\n'
    if data != head(path):
        candidates[path] = data

def remove_function(data, name):
    match = re.search(r'^void '+re.escape(name)+r'\([^\n]*\)(?: const)?\n\{', data, re.M)
    if not match:
        raise RuntimeError('Expected parallel function absent: '+name)
    start = match.start()
    pos = data.index('{', match.start())
    level = 1
    end = pos+1
    while level:
        level += (data[end] == '{') - (data[end] == '}')
        end += 1
    if data[end:end+1] == '\n':
        end += 1
    return data[:start]+data[end:]

for name, cls in [('HandBrainMonster','AHandBrainMonster'), ('PoisonMaggotMonster','APoisonMaggotMonster'),
                  ('WolfMonster','AWolfMonster'), ('FleshHandMonster','AFleshHandMonster'),
                  ('HundredEyedSlagMonster','AHundredEyedSlagMonster'), ('NurseZombie','ANurseZombie')]:
    for extension in ['cpp', 'h']:
        path = f'Source/FPSGAME/Monsters/{name}.{extension}'
        data = read(path)
        if extension == 'cpp':
            data = data.replace('#include "Net/UnrealNetwork.h"\n','').replace('#include "../Skills/ColdSteelSkillRules.h"\n','')
            data = re.sub(r'^.*ColdSteelSkills::NotifyKillByOwner\([^\n]*\n', '', data, flags=re.M)
            for method in ['GetLifetimeReplicatedProps', 'OnRep_State']:
                data = remove_function(data, cls+'::'+method)
        else:
            data = re.sub(r'^\s*/\*\* 复制给远端[^\n]*\n','',data,flags=re.M)
            data = re.sub(r',\s*ReplicatedUsing=OnRep_State', '', data)
            data = re.sub(r'^.*(?:virtual void GetLifetimeReplicatedProps|UFUNCTION\(\) void OnRep_State)[^\n]*\n', '', data, flags=re.M)
        candidate(path, data)

whole = ['HumanoidKnockdownComponent.cpp','HumanoidKnockdownComponent.h','HumanoidKnockdownObstacles.cpp',
         'HumanoidRagdollBudget.cpp','HumanoidRagdollBudget.h','MonsterRagdollPhysics.cpp','MonsterRagdollPhysics.h',
         'MonsterCorpsePoseAnimInstance.cpp','MonsterCorpsePoseAnimInstance.h',
         'MonsterCorpseRagdollComponent.cpp','MonsterCorpseRagdollComponent.h',
         'MonsterGunHitFeedback.cpp','MonsterIdleBreathingMeshComponent.cpp','MonsterIdleBreathingMeshComponent.h',
         'FatZombieAnimInstance.cpp','WitchMonster.cpp','WitchMonster.h','WitchRebuiltMonster.cpp','WitchRebuiltMonster.h',
         'WitchRebuiltAnimInstance.cpp','WitchRebuiltPhysics.cpp','WitchCorpsePose.cpp','WitchRecoveryLegNode.cpp','WitchRecoveryLegNode.h',
         'FleshHandCorpsePhysics.cpp','FleshHandKnockdownComponent.cpp',
         'HundredEyedSlagPhysics.cpp','HundredEyedSlagSpecialAttacks.cpp']
for name in whole:
    candidate('Source/FPSGAME/Monsters/'+name)

spawn = 'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp'
candidate(spawn, head(spawn).replace('TEXT("巫婆·重建候选")','TEXT("巫婆")'))

hit_path = 'Source/FPSGAME/Skills/ColdSteelSkillModel.cpp'
base, current = head(hit_path), read(hit_path)
for include, anchor in [('#include "../Monsters/MonsterIdleBreathingMeshComponent.h"','#include "../Monsters/MonsterCombatComponent.h"'),
                        ('#include "GameFramework/Character.h"','#include "Engine/World.h"')]:
    base = base.replace(anchor+'\n',anchor+'\n'+include+'\n',1)
start = base.index('// 枪械默认不给怪物硬直')
end = base.index('    // One contact, one captured ammo effect.',start)
current_start = current.index('// 枪械默认不给怪物硬直')
current_end = current.index('    // One contact, one captured ammo effect.',current_start)
candidate(hit_path,base[:start]+current[current_start:current_end]+base[end:])

candidate('.gitignore',head('.gitignore').rstrip()+'\n\n'+ignore)
mutant_path = 'SourceAssets/Mutant3Khaimera20260923/.gitignore'
candidate(mutant_path,head(mutant_path).rstrip()+'\n\n'+mutant_ignore)
asset_base = head('Docs/AssetSetup.md')
first, rest = asset_base.split('\n',1)
candidate('Docs/AssetSetup.md',first+'\n\n'+asset_section.strip()+'\n'+rest)
skill_path = 'skills/ue5-monster-workflow/SKILL.md'
data = head(skill_path)
current = read(skill_path)
old = next(line for line in data.splitlines() if line.startswith('人形击飞、倒地起身'))
new = next(line for line in current.splitlines() if line.startswith('人形击飞、倒地起身'))
nonhuman = next(line for line in current.splitlines() if line.startswith('毒蛆、手脑和犬类的死亡物理'))
data = data.replace(old,new+'\n\n'+nonhuman)
gun_route = next(line for line in current.splitlines() if line.startswith('枪械默认无硬直但需要局部身体回弹'))
candidate(skill_path,data.rstrip()+'\n\n'+gun_route+'\n')
for path in ['skills/ue5-monster-workflow/references/humanoid-knockdown.md',
             'skills/ue5-monster-workflow/references/nonhumanoid-ragdoll.md',
             'skills/ue5-monster-workflow/references/feral-humanoid-pounce.md',
             'skills/ue5-monster-workflow/references/hundred-eyed-slag.md',
             'skills/ue5-monster-workflow/references/gun-hit-feedback.md']:
    candidate(path)
perf_path = 'skills/ue5-performance-packaging/references/fpsgame-performance-development.md'
perf_block = read(perf_path).split('## 怪物倒地与尸体预算（2026-10-03）',1)[1]
candidate(perf_path,head(perf_path).rstrip()+'\n\n## 怪物倒地与尸体预算（2026-10-03）'+perf_block)

docs = ['monster-ragdoll-publication-20261003.md','monster-ragdoll-core-20261002.md','nonhumanoid-ragdoll-20261002.md',
        'monster-gun-hit-feedback-20261002.md','monster-ragdoll-standard-20261003.md',
        'monster-ragdoll-performance-20261003.md','witch-corpse-ground-20261002.md',
        'witch-corpse-follow-20261002.md','witch-corpse-contact-20261002.md',
        'witch-getup-robe-20261002.md','witch-ground-contact-20261002.md',
        'witch-staff-physics-and-death-systems-20261002.md','witch-physical-settle-20261003.md',
        'witch-walking-leg-restore-20261003.md','Mutant3PouncePalmDown20261002.md',
        'Mutant3PounceTakeoffHandsV2_20261002.md','Mutant3PounceForwardFlipV3_20261002.md',
        'Mutant3PounceLandingWristV4_20261002.md','Mutant3PounceOpenWindupV5_20261002.md',
        'hundred-eyed-slag-ragdoll-ground-v17-20261002.md']
for name in docs:
    candidate('Docs/Monsters/'+name)
candidate('Docs/ThirdParty/ALS-Refactored-LICENSE.md')
for pack in packs:
    for file in (ROOT / 'SourceAssets' / pack).rglob('*'):
        if file.is_file() and file.suffix in ['.py','.ps1','.md'] and 'Candidates' not in file.relative_to(ROOT).parts:
            candidate(file.relative_to(ROOT).as_posix())
for path in ['SourceAssets/MonsterRagdollCore20261002/provenance.json',
             'SourceAssets/MonsterRagdollCore20261002/Reference/AlsCharacter_Actions.cpp']:
    candidate(path)
for folder,names in allow.items():
    for name in names:
        candidate(f'SourceAssets/Mutant3Khaimera20260923/{folder}/{name}')
# Existing Slag model publication covers V17 asset installation dependencies;
# include only its owned V17 repair recipe, never earlier rejected V16 payloads.
slag_root = ROOT / 'SourceAssets/HundredEyedSlagMeshy20260930'
for file in slag_root.rglob('*.py'):
    if re.search(r'ragdoll_?ground_?v17', file.as_posix(), re.I):
        candidate(file.relative_to(ROOT).as_posix())

manifest = []
review = []
for path,data in sorted(candidates.items()):
    file = OUT / 'Candidates' / path
    file.parent.mkdir(parents=True,exist_ok=True)
    # Preserve PowerShell UTF-8 BOM, as required by the project.
    file.write_text(data, encoding='utf-8-sig' if file.suffix == '.ps1' else 'utf-8')
    manifest.append(dict(path=path, candidate=str(file.relative_to(ROOT)).replace('\\','/'),
                         sha256=hashlib.sha256(file.read_bytes()).hexdigest(), bytes=file.stat().st_size))
    review.extend(difflib.unified_diff(head(path).splitlines(keepends=True),data.splitlines(keepends=True),
                                      fromfile='a/'+path,tofile='b/'+path))
(OUT / 'candidate-files.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT / 'candidate-review.diff').write_text(''.join(review),encoding='utf-8')
print(json.dumps(dict(files=len(manifest),bytes=sum(e['bytes'] for e in manifest),
                      review=str(OUT / 'candidate-review.diff')),ensure_ascii=False))
