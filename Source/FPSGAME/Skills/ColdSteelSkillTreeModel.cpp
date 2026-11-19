// Skill tree + specialization operations on the profile model (2026-11-15).
// Writes reuse the F6 development path: SyncRuntime -> Snapshot -> mutate -> CommitState (checked save,
// shadow-profile authority in multiplayer). Notices come from the same Before/After diff as level-ups.
#include "ColdSteelSkillTree.h"
#include "../UI/ColdSteelStatusModel.h"

namespace
{
    FString SkillName(const UColdSteelStatusModel& Model, FName Id) { return Model.DevelopmentSkillDefinition(Id).Name; }
    FString RequirementLabel(const UColdSteelStatusModel& Model, const ColdSteelSkillTree::FRequirement& R)
    {
        using namespace ColdSteelSkillTree;
        switch(R.Kind)
        {
        case EReqKind::CharacterLevel: return FString::Printf(TEXT("角色 Lv%d"), R.Level);
        case EReqKind::PointsInvested: return FString::Printf(TEXT("已投入 %d 点"), R.Level);
        case EReqKind::AnyOf:
        {
            FString Names; for(FName Id : R.Skills) Names += (Names.IsEmpty() ? TEXT("") : TEXT("/")) + SkillName(Model, Id);
            return FString::Printf(TEXT("%s 任一 Lv%d"), *Names, R.Level);
        }
        default: return FString::Printf(TEXT("%s Lv%d"), R.Skills.Num() ? *SkillName(Model, R.Skills[0]) : TEXT("?"), R.Level);
        }
    }
}

bool UColdSteelStatusModel::IsSkillLearned(FName Id) const { return ColdSteelSkillTree::IsLearned(Current, Id); }
bool UColdSteelStatusModel::CanLearnSkill(FName Id, FString* Reason) const { return ColdSteelSkillTree::CanLearn(Current, Id, Reason); }
bool UColdSteelStatusModel::LearnSkill(FName Id)
{
    FString Reason;
    if(!ColdSteelSkillTree::CanLearn(Current, Id, &Reason)) { Message = Reason; return false; }
    SyncRuntime(); auto Next = Snapshot();
    ColdSteelSkillTree::Migrate(Next);
    Next.LearnedSkills.AddUnique(Id);
    // A learned skill starts its training at Lv1 / 0 XP; legacy keys already exist from ColdSteelSkills::Migrate.
    auto& Progress = Next.Skills.FindOrAdd(Id); Progress.Level = FMath::Max(1, Progress.Level);
    return CommitState(MoveTemp(Next));
}
int32 UColdSteelStatusModel::SpecRank(FName Skill, FName Node) const { return ColdSteelSkillTree::SpecRank(Current, Skill, Node); }
int32 UColdSteelStatusModel::SpecPointsFree(FName Skill) const
{ return FMath::Max(0, ColdSteelSkillTree::SpecPointsEarned(Current, Skill) - ColdSteelSkillTree::SpecPointsSpent(Current, Skill)); }
bool UColdSteelStatusModel::CanInvestSpec(FName Skill, FName Node, FString* Reason) const { return ColdSteelSkillTree::CanInvest(Current, Skill, Node, Reason); }
bool UColdSteelStatusModel::InvestSpec(FName Skill, FName Node)
{
    FString Reason;
    if(!ColdSteelSkillTree::CanInvest(Current, Skill, Node, &Reason)) { Message = Reason; return false; }
    SyncRuntime(); auto Next = Snapshot();
    Next.SkillSpecs.FindOrAdd(Skill).Ranks.FindOrAdd(Node) += 1;
    return CommitState(MoveTemp(Next));
}
int32 UColdSteelStatusModel::ResetSpecs(FName Skill)
{
    SyncRuntime(); auto Next = Snapshot();
    int32 Refunded = 0;
    for(auto It = Next.SkillSpecs.CreateIterator(); It; ++It)
    {
        if(!Skill.IsNone() && It.Key() != Skill) continue;
        Refunded += ColdSteelSkillTree::SpecPointsSpent(Next, It.Key());
        It.RemoveCurrent();
    }
    if(Refunded == 0) return 0;
    return CommitState(MoveTemp(Next)) ? Refunded : -1;
}
float UColdSteelStatusModel::SpecStat(FName Skill, const TCHAR* Stat) const { return ColdSteelSkillTree::SpecStat(Current, Skill, Stat); }
float UColdSteelStatusModel::InheritedFireSpecStat(const TCHAR* Stat) const { return ColdSteelSkillTree::InheritedFireStat(Current, Stat); }

void UColdSteelStatusModel::QueueSkillTreeNotices(const FColdSteelProfile& Before, const FColdSteelProfile& After)
{
    using namespace ColdSteelSkillTree;
    const FTree& Tree = Get();
    if(!Tree.bLoaded || After.SkillTreeVersion < 1) return;
    // The migration itself is not news: an old save becoming version 1 must not announce 30 skills.
    const bool bMigrating = Before.SkillTreeVersion < 1;
    for(const FNode& N : Tree.Nodes)
    {
        const FColdSteelSkillDefinition& D = DevelopmentSkillDefinition(N.Id);
        const bool bWasLearned = IsLearned(Before, N.Id), bLearned = IsLearned(After, N.Id);
        if(!bMigrating && bLearned && !bWasLearned)
        {
            FColdSteelProgressNotice Notice; Notice.bUpgrade = true; Notice.Icon = D.Icon;
            const FBranch* B = Tree.FindBranch(N.Branch);
            static const TCHAR* TierNames[] = { TEXT("根基"), TEXT("初级 I"), TEXT("中级 II"), TEXT("高级 III"), TEXT("终极 IV") };
            Notice.Title = FString::Printf(TEXT("习得 %s"), *D.Name);
            Notice.Detail = FString::Printf(TEXT("%s · %s　从 Lv 1 开始修炼"), B ? *B->Name : TEXT(""), TierNames[FMath::Clamp(N.Tier, 0, 4)]);
            ProgressNotices.Add(MoveTemp(Notice));
            continue;
        }
        if(bLearned || bMigrating) continue;
        const bool bWasReady = CanLearn(Before, N.Id), bReady = CanLearn(After, N.Id);
        if(bReady && !bWasReady)
        {
            FColdSteelProgressNotice Notice; Notice.bUpgrade = true; Notice.Icon = D.Icon;
            Notice.Title = FString::Printf(TEXT("可以习得：%s"), *D.Name);
            FString Conditions; for(const auto& R : N.Requires) Conditions += (Conditions.IsEmpty() ? TEXT("") : TEXT(" · ")) + RequirementLabel(*this, R);
            Notice.Detail = FString::Printf(TEXT("%s 已满足　按 P 免费习得"), *Conditions);
            ProgressNotices.Add(MoveTemp(Notice));
        }
    }
    for(const auto& Pair : Tree.Specs)
    {
        const FName Skill = Pair.Key; const FSpec& S = Pair.Value;
        const FColdSteelSkillDefinition& D = DevelopmentSkillDefinition(Skill);
        const int32 EarnedBefore = SpecPointsEarned(Before, Skill), EarnedAfter = SpecPointsEarned(After, Skill);
        if(!bMigrating && IsLearned(Before, Skill) && EarnedAfter > EarnedBefore)
        {
            FColdSteelProgressNotice Notice; Notice.bUpgrade = true; Notice.Icon = D.Icon;
            Notice.Title = FString::Printf(TEXT("%s专精点 +%d"), *D.Name, EarnedAfter - EarnedBefore);
            Notice.Detail = FString::Printf(TEXT("可用 %d 点　在技能树的%s详情中打开专精"), FMath::Max(0, EarnedAfter - SpecPointsSpent(After, Skill)), *D.Name);
            ProgressNotices.Add(MoveTemp(Notice));
        }
        for(const FSpecNode& Node : S.Nodes)
            if(ColdSteelSkillTree::SpecRank(Before, Skill, Node.Id) == 0 && ColdSteelSkillTree::SpecRank(After, Skill, Node.Id) > 0)
            {
                FColdSteelProgressNotice Notice; Notice.bUpgrade = true; Notice.Icon = D.Icon;
                Notice.Title = FString::Printf(TEXT("专精解锁：%s"), *Node.Name);
                Notice.Detail = Node.Text;
                ProgressNotices.Add(MoveTemp(Notice));
            }
    }
}
