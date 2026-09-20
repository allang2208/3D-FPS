#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "FPSCharacterMovementComponent.h"
#include "FPSTraversalComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "GameFramework/ProjectileMovementComponent.h"

bool AFPSGAMECharacter::IsDodging() const
{
    const auto* Movement=Cast<UFPSCharacterMovementComponent>(GetCharacterMovement());
    return Movement && Movement->IsDodging();
}

bool AFPSGAMECharacter::TryDodge()
{
    if(IsWhirlwindMovementLocked())return false;
    if(RuneSword && RuneSword->IsGuarding())return false;
    auto* Movement=Cast<UFPSCharacterMovementComponent>(GetCharacterMovement());
    const auto* PC=Cast<APlayerController>(Controller);
    const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();
    if (!Movement || !PC || PC->IsMoveInputIgnored() || PC->bShowMouseCursor ||
        IsTraversing() || Traversal->IsCameraRecovering() || bIsSliding || IsDodging() ||
        (Health && Health->IsDead())) return false;
    const FRotationMatrix Basis(FRotator(0.f,GetViewRotation().Yaw,0.f));
    FVector Direction=Basis.GetUnitAxis(EAxis::X)*MoveInput.Y+Basis.GetUnitAxis(EAxis::Y)*MoveInput.X;
    if (Direction.IsNearlyZero()) Direction=Basis.GetUnitAxis(EAxis::X);
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const float Cost=Profile?Profile->DodgeStaminaCost():0;
    if(Profile&&!Profile->CanSpendStamina(Cost)){Profile->SpendStamina(Cost);return false;}
    const float Distance=DodgeDistance+(Profile?Profile->DodgeEffect().DodgeDistanceCM:0.f);
    if (!Movement->StartDodge(Direction,Distance,DodgeDuration)) return false;
    if(Profile&&!Profile->SpendStamina(Cost)){Movement->CancelDodge();return false;}
    bDodgeMeleeRewarded=bDodgeRangedRewarded=false;
    ExitSprintForWeapon();
    JumpBufferRemaining=0.f;
    StopJumping();
    Traversal->SetJumpHeld(false);
    if(Profile)Profile->TrainDodge(Profile->DodgeDefinition().UseExperience);
    return true;
}

float AFPSGAMECharacter::DodgePresentationWeight() const
{
    const auto* Movement=Cast<UFPSCharacterMovementComponent>(GetCharacterMovement());
    return Movement && Movement->IsDodging() ? FMath::Sin(PI*Movement->GetDodgeProgress()) : 0.f;
}

float AFPSGAMECharacter::TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
    AController* EventInstigator, AActor* DamageCauser)
{
    const bool DebugInvincible=UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(this,EDevelopmentTuningOption::Invincible);
    // Retain guard/parry reactions under the existing invincibility option,
    // as in gamedev; the health result still remains zero.
    if(DebugInvincible && !(RuneSword && RuneSword->IsGuarding()))return 0.f;
    // Reject before point/radial/any-damage events and their feedback are emitted.
    const bool Direct=DamageEvent.DamageTypeClass&&DamageEvent.DamageTypeClass->IsChildOf(UCombatDirectDamage::StaticClass());
    if (IsDodging()&&!Direct)
    {
        const auto* Type=DamageEvent.DamageTypeClass?DamageEvent.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr;
        AActor* Source=EventInstigator?EventInstigator->GetPawn():DamageCauser;
        if((!Source||!Source->FindComponentByClass<UMonsterCombatComponent>())&&DamageCauser)
        {
            if(auto* AttackPawn=DamageCauser->GetInstigator())Source=AttackPawn;
            else if(auto* AttackOwner=DamageCauser->GetOwner())Source=AttackOwner;
        }
        const auto* Enemy=Source?Source->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        const bool Eligible=DamageAmount>0&&Enemy&&!Enemy->IsDead()&&!Source->ActorHasTag(TEXT("Summoned"))&&!Source->ActorHasTag(TEXT("NoSkillTraining"))&&!(Type&&Type->IsA<UMaggotPoisonDamage>());
        const bool Melee=Type&&Type->IsA<UEnemyMeleeDamage>();
        const bool Ranged=!Melee&&((Type&&Type->IsA<UEnemyRangedDamage>())||DamageEvent.IsOfType(FPointDamageEvent::ClassID)||(DamageCauser&&DamageCauser->FindComponentByClass<UProjectileMovementComponent>()));
        if(Eligible&&((Melee&&!bDodgeMeleeRewarded)||(Ranged&&!bDodgeRangedRewarded)))
            if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            {
                if(Melee)bDodgeMeleeRewarded=true;else bDodgeRangedRewarded=true;
                Profile->TrainDodge(Melee?Profile->DodgeDefinition().MeleeDodgeExperience:Profile->DodgeDefinition().RangedDodgeExperience);
            }
        return 0.f;
    }
    if(DamageAmount<=0.f)return 0.f;
    const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health && Health->IsDead())return 0.f;
    const auto* Type=DamageEvent.DamageTypeClass?DamageEvent.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr;
    if(Health)DamageAmount=Health->DamageAfterArmor(DamageAmount,Type);
    if(!Direct && RuneSword && RuneSword->IsEquipped())DamageAmount=RuneSword->ResolveGuardDamage(DamageAmount,Type,EventInstigator,DamageCauser);
    if(DebugInvincible)return 0.f;
    // A parry returns zero to the attack caller before damage events or its
    // on-hit status effects are emitted. Armor has already been applied once.
    return DamageAmount>0.f?Super::TakeDamage(DamageAmount,DamageEvent,EventInstigator,DamageCauser):0.f;
}
