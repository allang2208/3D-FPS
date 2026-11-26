#include "ColdSteelStatusModel.h"

namespace
{
// A short queue absorbs a shotgun blast or multi-target spell; the HUD takes all
// pending amounts at once and draws one readable number.
constexpr int32 MaxPendingExperienceNotices=16;
}

void UColdSteelStatusModel::QueueExperienceNotice(int64 Amount)
{
    if(Amount<=0)return;
    if(ExperienceNotices.Num()>=MaxPendingExperienceNotices)
    {
        int64& Last=ExperienceNotices.Last();
        Last+=FMath::Min(Amount,MAX_int64-Last);
        return;
    }
    ExperienceNotices.Add(Amount);
}

bool UColdSteelStatusModel::TakeExperienceNotice(int64& OutAmount)
{
    if(ExperienceNotices.IsEmpty())return false;
    OutAmount=0;
    for(const int64 Amount:ExperienceNotices)
        OutAmount+=FMath::Min(Amount,MAX_int64-OutAmount);
    ExperienceNotices.Reset();
    return OutAmount>0;
}

void UColdSteelStatusModel::ResetExperienceNotices(){ExperienceNotices.Reset();}
