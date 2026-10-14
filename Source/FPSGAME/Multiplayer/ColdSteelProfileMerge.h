#pragma once
#include "../UI/ColdSteelInventoryTypes.h"

namespace ColdSteelProfileMerge
{
    template<typename T> inline void Progress(int32& Level,T& XP,int32 OtherLevel,T OtherXP)
    {
        if(OtherLevel>Level){Level=OtherLevel;XP=OtherXP;}
        else if(OtherLevel==Level)XP=FMath::Max(XP,OtherXP);
    }

    inline int64 AttributeTotal(const FColdSteelProfile& P)
    {
        int64 Total=0;
        for(const auto& Pair:P.Attributes)Total+=Pair.Value;
        return Total;
    }

    inline void Progression(FColdSteelProfile& Into,const FColdSteelProfile& Other)
    {
        // Allocation moves one point from Points to Attributes. Their sum is
        // unchanged by spending, so an old mirror cannot refund that spend.
        // Both peers merge the same cumulative entitlement, not deltas per upload.
        const int64 Entitlement=FMath::Max(int64(Into.Points)+AttributeTotal(Into),int64(Other.Points)+AttributeTotal(Other));
        for(const auto& Pair:Other.Attributes)
            Into.Attributes.FindOrAdd(Pair.Key)=FMath::Max(Into.Attributes.FindRef(Pair.Key),Pair.Value);
        Into.Points=int32(FMath::Clamp<int64>(Entitlement-AttributeTotal(Into),0,1000000));
        Progress(Into.Level,Into.Experience,Other.Level,Other.Experience);
        Into.Kills=FMath::Max(Into.Kills,Other.Kills);
        for(const auto& Pair:Other.Skills)
        {
            auto& Skill=Into.Skills.FindOrAdd(Pair.Key);
            Progress(Skill.Level,Skill.Experience,Pair.Value.Level,Pair.Value.Experience);
        }
    }

    inline void OfferingUsage(FColdSteelProfile& Into,const FColdSteelProfile& Other)
    {
        for(auto& Buff:Into.FormulaBuffs)if(Buff.bTribute)
            if(const auto* Previous=Other.FormulaBuffs.FindByPredicate([&](const auto& B)
                {return B.bTribute&&B.Id==Buff.Id&&B.OfferingId==Buff.OfferingId;}))
            {
                Buff.bPeachUsed|=Previous->bPeachUsed;
                Buff.bMoonshadowUsed|=Previous->bMoonshadowUsed;
                Buff.RemainingSeconds=FMath::Min(Buff.RemainingSeconds,Previous->RemainingSeconds);
            }
    }
}
