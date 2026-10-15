#include "ProductionToolComponent.h"
#include "ProductionToolMeshComponent.h"
#include "WarhammerGuardMotion.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

bool UProductionToolComponent::IsGuardActive() const
{
    const auto* Guard=Character.IsValid()?Character->RuneSword.Get():nullptr;
    return IsWarhammerEquipped()&&Guard&&Guard->IsToolGuardPoseActive();
}
bool UProductionToolComponent::HasAuthorityAttackInFlight() const
{
    return bBluntServerCharging||bBluntUppercut||bBluntWhirlwind||
        (GetWorld()&&GetWorld()->GetTimeSeconds()<BluntServerReadyAt);
}
bool UProductionToolComponent::CanQueueGuard() const
{
    if(!IsWarhammerEquipped()||!CanUse()||!HasReadyPresentation()||bBluntUppercut||bBluntWhirlwind
        ||(bBluntSprintAttack&&Elapsed>=0.f)||IsQuickCombatActive())return false;
    for(const TCHAR* Clip:WarhammerGuard::Clips)if(!Motions.FindRef(Clip))return false;
    return true;
}
bool UProductionToolComponent::CanStartGuard() const
{
    return CanQueueGuard()&&Elapsed<0.f&&EquipElapsed<0.f&&!bBluntCharging&&!bBluntReturningCharge&&
        (!Character->HasAuthority()||!HasAuthorityAttackInFlight());
}
void UProductionToolComponent::PrepareGuard()
{
    CancelInspect();bQueuedBluntAttack=false;
    if(bBluntCharging)CancelHeavyCharge();
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;SprintBlend=0.f;
}
bool UProductionToolComponent::PresentGuardPose()
{
    if(!IsGuardActive()||!Viewmodel)return false;
    FName Clip;float Seconds=0.f,Age=0.f;
    if(!Character->RuneSword->GetToolGuardPose(Clip,Seconds,Age))return false;
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    SampleMotion(Clip,Seconds);
    return true;
}
void UProductionToolComponent::PlayGuardSound(bool Parried)
{
    const int32 Index=Parried?2:(FMath::RandBool()?0:1);
    if(GuardSounds.IsValidIndex(Index)&&GuardSounds[Index])
        UGameplayStatics::PlaySound2D(this,GuardSounds[Index],.85f,Parried?1.15f:1.f);
}
