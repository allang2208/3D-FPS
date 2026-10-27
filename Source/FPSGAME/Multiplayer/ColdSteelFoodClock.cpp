#include "ColdSteelPlayerState.h"
#include "../Items/FoodSpoilage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"

void AColdSteelPlayerState::PublishFoodClock(const FFoodClockSample& Sample)
{
    if(!HasAuthority()||!Sample.Id.IsValid()||!FMath::IsFinite(Sample.Day)||Sample.Day<0.)return;
    FoodClockState.Id=Sample.Id;FoodClockState.Day=Sample.Day;
}
void AColdSteelPlayerState::OnRep_FoodClock()
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->IsLocalController()||HasAuthority())return;
    if(auto* GI=GetGameInstance())if(auto* Model=GI->GetSubsystem<UColdSteelStatusModel>())
        Model->ObserveFoodClock({FoodClockState.Id,FoodClockState.Day});
}
