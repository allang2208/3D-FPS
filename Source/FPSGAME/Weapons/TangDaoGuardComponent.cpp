#include "TangDaoGuardComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

UTangDaoGuardComponent::UTangDaoGuardComponent()
{
    PrimaryComponentTick.bCanEverTick=false;
    SetIsReplicatedByDefault(true);
}

void UTangDaoGuardComponent::Configure(const UColdSteelStatusModel* InProfile)
{
    Profile=InProfile;
    const auto* Item=InProfile&&!InProfile->ActiveProductionTool()?InProfile->Equipped():nullptr;
    const auto* Gunsmith=InProfile?InProfile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    FString NextInstance,NextGuard;
    FMeleeModifiers NextModifiers;
    if(Item&&Item->Definition==TEXT("ue_tang_dao")&&Gunsmith)
    {
        const FString Part=Gunsmith->Installed(*Item).FindRef(TEXT("guard"));
        if(Part==TEXT("xuan_cloud_dragon")||Part==TEXT("phoenix_feather"))
            if(const auto* Option=Gunsmith->Option(Item->Definition,TEXT("guard"),Part))
            {NextInstance=Item->InstanceId;NextGuard=Part;NextModifiers=Option->Melee;}
    }
    const bool Changed=NextInstance!=EquippedInstance||NextGuard!=GuardId;
    EquippedInstance=MoveTemp(NextInstance);GuardId=MoveTemp(NextGuard);Modifiers=NextModifiers;
    if(Changed)ClearTransient(); // Cooldowns survive swapping away and back.
}

bool UTangDaoGuardComponent::IsActive() const
{
    if(EquippedInstance.IsEmpty()||!Profile.IsValid()||Profile->ActiveProductionTool())return false;
    const auto* Item=Profile->Equipped();
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return Item&&Item->InstanceId==EquippedInstance&&Item->Definition==TEXT("ue_tang_dao")&&(!Health||!Health->IsDead());
}

double UTangDaoGuardComponent::Clock() const
{
    const auto* World=GetWorld();
    const auto* State=World?World->GetGameState():nullptr;
    return State?State->GetServerWorldTimeSeconds():World?World->GetTimeSeconds():0.;
}

float UTangDaoGuardComponent::DamageTakenMultiplier() const {return IsActive()?Modifiers.DamageTaken:1.f;}
float UTangDaoGuardComponent::DodgeStaminaMultiplier() const {return IsActive()?Modifiers.DodgeStamina:1.f;}
float UTangDaoGuardComponent::SprintStaminaMultiplier() const {return IsActive()?Modifiers.SprintStamina:1.f;}
float UTangDaoGuardComponent::AttackStaminaMultiplier() const {return IsActive()?Modifiers.Stamina:1.f;}
float UTangDaoGuardComponent::AttackSpeedMultiplier() const {return PhoenixRemaining()>0.f?Modifiers.PhoenixSpeed:1.f;}
float UTangDaoGuardComponent::DragonRemaining() const
{return IsActive()&&Modifiers.DragonSeconds>0&&ProcInstance==EquippedInstance?FMath::Max(0.f,float(DragonEndsAt-Clock())):0.f;}
float UTangDaoGuardComponent::PhoenixRemaining() const
{return IsActive()&&Modifiers.PhoenixSeconds>0&&ProcInstance==EquippedInstance?FMath::Max(0.f,float(PhoenixEndsAt-Clock())):0.f;}

void UTangDaoGuardComponent::GrantDragon()
{
    const double Now=Clock();
    if(!GetOwner()->HasAuthority()||!IsActive()||Modifiers.DragonSeconds<=0||Now<DragonReadyAt)return;
    ProcInstance=EquippedInstance;DragonEndsAt=Now+Modifiers.DragonSeconds;
    DragonReadyAt=Now+Modifiers.DragonCooldown;Publish();
}

void UTangDaoGuardComponent::GrantPhoenix()
{
    const double Now=Clock();
    if(!GetOwner()->HasAuthority()||!IsActive()||Modifiers.PhoenixSeconds<=0||Now<PhoenixReadyAt)return;
    ProcInstance=EquippedInstance;PhoenixEndsAt=Now+Modifiers.PhoenixSeconds;
    PhoenixReadyAt=Now+Modifiers.PhoenixCooldown;
    PhoenixHits=FMath::Max(0,FMath::RoundToInt(Modifiers.PhoenixHealHits));
    HealedAttacks.Reset();Publish();
}

void UTangDaoGuardComponent::StampBladeAttack(AActor* Owner,FColdSteelSkillShot& Shot)
{
    if(auto* Guard=Owner?Owner->FindComponentByClass<UTangDaoGuardComponent>():nullptr;Guard&&Guard->IsActive())
    {
        if(++Guard->AttackSerial==0)++Guard->AttackSerial;
        Shot.GuardAttackSerial=Guard->AttackSerial;Shot.GuardSourceInstance=Guard->EquippedInstance;
    }
}

bool UTangDaoGuardComponent::IsBladeHit(const FColdSteelSkillShot& Shot) const
{
    return GetOwner()->HasAuthority()&&IsActive()&&Shot.bMelee&&!Shot.bRicochet
        &&!(Shot.AttackMeta&(0x40|0x80))&&Shot.GuardAttackSerial!=0
        &&Shot.ItemDefinition==TEXT("ue_tang_dao")&&Shot.GuardSourceInstance==EquippedInstance;
}

float UTangDaoGuardComponent::ConsumeDragon(const FColdSteelSkillShot& Shot,float& BonusToughness)
{
    BonusToughness=0.f;
    if(!IsBladeHit(Shot)||DragonRemaining()<=0.f)return 1.f;
    const float Multiplier=Modifiers.DragonDamage;BonusToughness=Modifiers.DragonToughness;
    DragonEndsAt=0.;Publish();return Multiplier;
}

void UTangDaoGuardComponent::ConfirmBladeHit(const FColdSteelSkillShot& Shot)
{
    if(!IsBladeHit(Shot)||PhoenixRemaining()<=0.f||PhoenixHits<=0||HealedAttacks.Contains(Shot.GuardAttackSerial))return;
    HealedAttacks.Add(Shot.GuardAttackSerial);--PhoenixHits;
    if(auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&!Health->IsDead())
        Health->Health=FMath::Min(Health->MaxHealth,Health->Health+Health->MaxHealth*float(Modifiers.PhoenixHealRatio));
    Publish();
}

void UTangDaoGuardComponent::ClearTransient()
{
    const bool HadState=DragonEndsAt>0.||PhoenixEndsAt>0.||PhoenixHits>0;
    DragonEndsAt=PhoenixEndsAt=0.;PhoenixHits=0;ProcInstance.Reset();HealedAttacks.Reset();
    if(HadState)Publish();
}

void UTangDaoGuardComponent::Publish()
{
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    UStatusEffectsComponent::Notify(GetOwner());
}
void UTangDaoGuardComponent::OnRep_Proc(){UStatusEffectsComponent::Notify(GetOwner());}
void UTangDaoGuardComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UTangDaoGuardComponent,ProcInstance,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UTangDaoGuardComponent,DragonEndsAt,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UTangDaoGuardComponent,PhoenixEndsAt,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UTangDaoGuardComponent,PhoenixHits,COND_OwnerOnly);
}
