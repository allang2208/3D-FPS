#include "RuneSwordComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerGuardMotion.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "Engine/World.h"

const FColdSteelItem* URuneSwordComponent::GuardItem(const UColdSteelStatusModel* Profile) const
{
    if(!Profile)return nullptr;
    const auto* Tool=Profile->ActiveProductionTool();
    return Tool&&ColdSteelInventory::IsTwoHandedBlunt(*Tool)?Tool:Profile->Equipped();
}

void URuneSwordComponent::RefreshToolGuardEquipment(UColdSteelStatusModel* Profile)
{
    const auto* Item=GuardItem(Profile);
    const FString Next=Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item)?Item->InstanceId:FString();
    if(Next!=ToolGuardInstance){ClearGuard();ToolGuardInstance=Next;}
    if(!Next.IsEmpty())ToolGuardModifiers=ColdSteelMelee::Evaluate(*Item,Profile).Modifiers;
}

float URuneSwordComponent::GuardRaiseSeconds() const
{ return ToolGuardInstance.IsEmpty()?RuneSwordGuardTuning::RaiseSeconds:WarhammerGuard::EnterSeconds; }

void URuneSwordComponent::CancelToolGuard()
{ if(!ToolGuardInstance.IsEmpty())ClearGuard(); }

bool URuneSwordComponent::GetToolGuardPose(FName& Clip,float& Seconds,float& Age) const
{
    if(!IsToolGuardPoseActive()||ToolGuardClip.IsNone())return false;
    Clip=ToolGuardClip;Age=ToolGuardAge;
    Seconds=Clip==TEXT("GuardHold")?FMath::Fmod(ToolGuardAge,WarhammerGuard::HoldSeconds):ToolGuardAge;
    return true;
}

void URuneSwordComponent::AdvanceToolGuard(float Delta)
{
    if(ToolGuardInstance.IsEmpty()||!Character.IsValid())return;
    if(!CanPresent()){ClearGuard();return;}
    // The shared break deliberately locks input. Its presentation must continue
    // during that lock instead of cancelling itself through CanUse().
    if(bGuardBreakPose)
    {
        ToolGuardAge=FMath::Min(WarhammerGuard::BreakSeconds,ToolGuardAge+Delta);
        const auto* Broken=Character->FindComponentByClass<UPlayerGuardBreakComponent>();
        if(!Broken||!Broken->IsActive()){bGuardBreakPose=false;ToolGuardClip=NAME_None;}
        return;
    }
    if(!CanUse()||Character->IsCastBlockingLeftHandAction()||Character->IsDodging()||Character->IsSliding())
    {ClearGuard();return;}
    TryBeginGuard();
    if(bGuardReacting)
    {
        ToolGuardAge=FMath::Min(WarhammerGuard::HitSeconds,ToolGuardAge+Delta*GuardReactionRate);
        if(ToolGuardAge>=WarhammerGuard::HitSeconds)
        {bGuardReacting=false;ToolGuardClip=TEXT("GuardHold");ToolGuardAge=0.f;}
        return;
    }
    if(bGuarding)
    {
        ToolGuardAge+=Delta;
        if(ToolGuardClip==TEXT("GuardEnter"))
        {
            GuardPoseTime=FMath::Min(WarhammerGuard::EnterSeconds,ToolGuardAge);
            if(ToolGuardAge>=WarhammerGuard::EnterSeconds)
            {ToolGuardAge-=WarhammerGuard::EnterSeconds;ToolGuardClip=TEXT("GuardHold");}
        }
        return;
    }
    if(bReturningGuard)
    {
        if(ToolGuardClip==TEXT("GuardEnter"))
        {
            ToolGuardAge=FMath::Max(0.f,ToolGuardAge-Delta*WarhammerGuard::EnterSeconds/WarhammerGuard::ExitSeconds);
            GuardPoseTime=ToolGuardAge;
            if(ToolGuardAge<=0.f){bReturningGuard=false;ToolGuardClip=NAME_None;}
            return;
        }
        ToolGuardAge=FMath::Min(WarhammerGuard::ExitSeconds,ToolGuardAge+Delta);
        GuardPoseTime=WarhammerGuard::EnterSeconds*(1.f-ToolGuardAge/WarhammerGuard::ExitSeconds);
        if(ToolGuardAge>=WarhammerGuard::ExitSeconds){bReturningGuard=false;ToolGuardClip=NAME_None;}
    }
}
