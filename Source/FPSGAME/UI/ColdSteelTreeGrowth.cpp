#include "ColdSteelStatusModel.h"
#include "../FPSWeatherManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"

bool UColdSteelStatusModel::HasTreeGrowth(const FString& Id) const
{ return Current.TreeGrowth.Contains(Id); }

bool UColdSteelStatusModel::IsTreeMature(const FString& Id) const
{
    const auto* G=Current.TreeGrowth.Find(Id);
    return !G || Current.TreeGrowthDay-G->CutAtDay>=G->MatureDays;
}

float UColdSteelStatusModel::TreeGrowthScale(const FString& Id) const
{
    const auto* G=Current.TreeGrowth.Find(Id);if(!G)return 1;
    const double Age=FMath::Max(0.0,Current.TreeGrowthDay-G->CutAtDay);
    if(Age<G->DormantDays)return 0;
    const double T=FMath::Clamp((Age-G->DormantDays)/FMath::Max(.1,double(G->MatureDays-G->DormantDays)),0.0,1.0);
    auto Smooth=[](double V){V=FMath::Clamp(V,0.0,1.0);return V*V*(3-2*V);};
    if(T<.2)return FMath::Lerp(.04,.18,Smooth(T/.2));
    if(T<.6)return FMath::Lerp(.18,.55,Smooth((T-.2)/.4));
    return FMath::Lerp(.55,1.0,Smooth((T-.6)/.4));
}

float UColdSteelStatusModel::TreeStumpScale(const FString& Id) const
{
    const auto* G=Current.TreeGrowth.Find(Id);if(!G)return 1;
    const double T=FMath::Clamp((Current.TreeGrowthDay-G->CutAtDay-G->DormantDays)/
        FMath::Max(.1,double(G->MatureDays-G->DormantDays)*.2),0.0,1.0);
    return 1-T*T*(3-2*T);
}

void UColdSteelStatusModel::TickTreeGrowthClock(float Delta)
{
    if(!GetWorld() || GetWorld()->GetNetMode()!=NM_Standalone || Delta<=0)return;
    // Legacy depleted tree IDs receive a fresh cycle, keeping ore/soil untouched.
    // The tagged sub-schema travels with the same profile transaction as the drops.
    if(Current.TreeGrowthVersion==0)
    {
        for(const auto& Pair:Current.HarvestProgress)
            if(Pair.Value>=3 && Pair.Key.Contains(TEXT(":v1:0:")) && !Current.TreeGrowth.Contains(Pair.Key))
            {FColdSteelTreeGrowth G;G.CutAtDay=Current.TreeGrowthDay;Current.TreeGrowth.Add(Pair.Key,G);}
        Current.TreeGrowthVersion=1;
    }
    TreeGrowthWeatherSearch-=Delta;
    if(TreeGrowthWeather.IsValid() && TreeGrowthWeather->GetWorld()!=GetWorld())TreeGrowthWeather.Reset();
    if(!TreeGrowthWeather.IsValid() && TreeGrowthWeatherSearch<=0)
    {
        TreeGrowthWeatherSearch=5;
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){TreeGrowthWeather=*It;break;}
    }
    const double DaySeconds=TreeGrowthWeather.IsValid()?FMath::Max(60.f,TreeGrowthWeather->RealSecondsPerGameDay):2160.0;
    Current.TreeGrowthDay+=Delta/DaySeconds;
}
