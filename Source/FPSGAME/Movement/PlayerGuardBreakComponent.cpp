#include "PlayerGuardBreakComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "InputCoreTypes.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "TimerManager.h"

void UPlayerGuardBreakComponent::Apply(float Seconds)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!PC || GetNetMode()!=NM_Standalone || Seconds<=0.f)return;
    Pawn->SuspendWeaponForMenu();
    Pawn->StopJumping();Pawn->ConsumeMovementInputVector();Pawn->GetCharacterMovement()->StopMovementImmediately();
    if(!LockedController.IsValid())
    {
        LockedController=PC;PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);Pawn->DisableInput(PC);
    }
    Seconds=FMath::Max(Seconds,GetWorld()->GetTimerManager().GetTimerRemaining(Timer));
    GetWorld()->GetTimerManager().SetTimer(Timer,this,&UPlayerGuardBreakComponent::Release,Seconds,false);
    UStatusEffectsComponent::GetOrCreate(Pawn)->SetTimed(TEXT("stun"),Seconds);
}
void UPlayerGuardBreakComponent::Release()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    bool ResumeGuard=false;
    if(auto* PC=LockedController.Get())
    {
        PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);
        const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(Pawn && !Pawn->IsActorBeingDestroyed() && (!Health || !Health->IsDead()))
        {
            Pawn->EnableInput(PC);ResumeGuard=PC->IsInputKeyDown(EKeys::RightMouseButton);
        }
    }
    LockedController.Reset();
    if(ResumeGuard)if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>())Sword->BeginGuard();
}
void UPlayerGuardBreakComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorld()->GetTimerManager().ClearTimer(Timer);Release();Super::EndPlay(Reason);
}
