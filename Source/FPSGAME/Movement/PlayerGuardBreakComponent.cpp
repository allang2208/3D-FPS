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
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

UPlayerGuardBreakComponent::UPlayerGuardBreakComponent()
{SetIsReplicatedByDefault(true);}
void UPlayerGuardBreakComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UPlayerGuardBreakComponent,StunUntil,COND_OwnerOnly);
}
void UPlayerGuardBreakComponent::Apply(float Seconds)
{
    if(!GetOwner()->HasAuthority()||Seconds<=0.f)return;
    StunUntil=FMath::Max(StunUntil,GetWorld()->GetTimeSeconds()+Seconds);
    ApplyInputLock(float(StunUntil-GetWorld()->GetTimeSeconds()));GetOwner()->ForceNetUpdate();
}
void UPlayerGuardBreakComponent::OnRep_StunUntil()
{
    const auto* State=GetWorld()->GetGameState();
    const double Now=State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const float Remaining=float(StunUntil-Now);
    if(Remaining>0.f)ApplyInputLock(Remaining);else Release();
}
void UPlayerGuardBreakComponent::ApplyInputLock(float Seconds)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!PC||Seconds<=0.f)return;
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
    GetWorld()->GetTimerManager().ClearTimer(Timer);
    if(GetOwner()->HasAuthority()&&StunUntil>0.){StunUntil=0.;GetOwner()->ForceNetUpdate();}
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
