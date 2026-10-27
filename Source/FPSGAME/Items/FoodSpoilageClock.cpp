#include "FoodSpoilageClock.h"
#include "../FPSWeatherManager.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

bool UFoodSpoilageClock::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}

FFoodClockSample UFoodSpoilageClock::Sample()
{
    UWorld* W=GetWorld();if(!W)return {};
    if(W->GetNetMode()==NM_Client){Current={};bSeeded=false;return {};}
    // PreExit removes the net driver before the profile's final save. A client
    // then reports Standalone: never invent a new authority domain during teardown.
    // An actual authority may still flush its last sampled checkpoint.
    if(W->bIsTearingDown)return Current;
    auto* GI=W->GetGameInstance();auto* Host=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Host)return {};
    if(!bSeeded)
    {
        const auto P=Host->Snapshot();if(!P.NetworkProfileId.IsValid())return {};
        Current={P.NetworkProfileId,FMath::Max(0.,P.FoodClockDay)};bSeeded=true;
    }
    const double Time=W->GetTimeSeconds();
    if(!Weather.IsValid()&&Time>=SearchAfter)
    {
        SearchAfter=Time+1.;
        for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
        {
            Weather=*It;
            // A replacement manager establishes a new sample. The first manager
            // starts at zero; elapsed time before a food is created is excluded by Stamp.
            LastNatural=bHadWeather?It->GetNaturalDayProgress():0.;bHadWeather=true;break;
        }
    }
    if(Weather.IsValid())
    {
        const double Natural=Weather->GetNaturalDayProgress();
        Current.Day+=FMath::Max(0.,Natural-LastNatural);LastNatural=Natural;
    }
    // No weather authority means no inferred real-time aging. Pauses, offline
    // time and manual calendar jumps never increase NaturalDayProgress.
    return Current;
}

void UFoodSpoilageClock::Tick(float Delta)
{
    UWorld* W=GetWorld();if(!W)return;
    if(W->GetNetMode()==NM_Client){Current={};bSeeded=false;return;}
    if(W->bIsTearingDown||W->IsPaused())return;
    Sample();SettlementSeconds+=Delta;if(SettlementSeconds<1.f)return;SettlementSeconds=0.f;
    auto* GI=W->GetGameInstance();auto* Host=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(Host)Host->SettleFoodSpoilage(true);
    for(auto It=W->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
        if(PS)PS->PublishFoodClock(Current);
        if(PS&&PS->GetShadowModel())PS->GetShadowModel()->SettleFoodSpoilage(true);
    }
}
void UFoodSpoilageClock::Deinitialize()
{
    if(auto* GI=GetWorld()?GetWorld()->GetGameInstance():nullptr)
        if(auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();Host&&GetWorld()->GetNetMode()!=NM_Client)
            Host->ObserveFoodClock(Sample());
    Super::Deinitialize();
}
