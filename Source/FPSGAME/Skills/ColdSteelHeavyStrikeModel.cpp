#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"

bool UColdSteelStatusModel::TrainHeavyStrike(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("heavyStrike"));
    // One completed release, one highest achieved tier. Counts are unique victims
    // from this swing's direct damage window, never poison or later attacks.
    const int32 XP=Kills>=5?D.HeavyKill5Experience:Hits>=5?D.HeavyHit5Experience:
        Kills>=2?D.HeavyKill2Experience:Hits>=2?D.HeavyHit2Experience:D.UseExperience;
    if(MasteryProgress(D.Id).Level>=D.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);return CommitState(P);
}
