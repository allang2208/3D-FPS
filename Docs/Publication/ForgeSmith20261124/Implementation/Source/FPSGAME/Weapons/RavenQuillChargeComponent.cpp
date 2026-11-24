#include "RavenQuillChargeComponent.h"
#include "GunsmithSystem.h"
#include "EagleTalonGuardComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

namespace
{
constexpr double ChargeSeconds=3.;
constexpr double HitWindow=5.;
constexpr int32 GlowIndex=0;
const FName GuardMesh(TEXT("SM_ForgedSteelGreatsword_RavenQuillGuard"));
const FName WideGuardMesh(TEXT("SM_ForgedSteelGreatsword_RavenQuillGuard_ExecutionerSeat"));

bool IsRavenMesh(const UStaticMeshComponent* Component)
{
    const UStaticMesh* Mesh=Component?Component->GetStaticMesh():nullptr;
    return Mesh&&(Mesh->GetFName()==GuardMesh||Mesh->GetFName()==WideGuardMesh);
}
}

URavenQuillChargeComponent::URavenQuillChargeComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
}

void URavenQuillChargeComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(URavenQuillChargeComponent,Charge);
}

double URavenQuillChargeComponent::Clock() const
{
    const auto* World=GetWorld();
    if(const auto* State=World->GetGameState())return State->GetServerWorldTimeSeconds();
    return World->GetTimeSeconds();
}

void URavenQuillChargeComponent::Equip(const FColdSteelItem* Item)
{
    if(!GetOwner()->HasAuthority())return;
    FString Equipped;
    if(Item&&Item->Definition==TEXT("ue_forged_steel_greatsword"))
        if(const auto* Smith=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            if(Smith->Installed(*Item).FindRef(TEXT("guard"))==TEXT("raven_quill_guard"))Equipped=Item->InstanceId;
    if(Equipped==Weapon)return;
    Weapon=MoveTemp(Equipped);
    Charge={};EmpoweredAttacks.Reset();
    Present(Clock());
    SetComponentTickEnabled(!Weapon.IsEmpty());
    GetOwner()->ForceNetUpdate();
}

bool URavenQuillChargeComponent::AdvanceDeadlines(double Now)
{
    if(Charge.RunStartedAt>=0.)
    {
        const double FullAt=Charge.RunStartedAt+ChargeSeconds-Charge.BankedSeconds;
        if(Now<FullAt)return false;
        Charge.RunStartedAt=-1.;Charge.BankedSeconds=ChargeSeconds;
        Charge.ReadyUntil=FullAt+HitWindow;
    }
    else if(Charge.ReadyUntil<0.||Now<Charge.ReadyUntil)return false;
    if(Now>=Charge.ReadyUntil)Charge={};
    return true;
}

float URavenQuillChargeComponent::Progress(double Now) const
{
    if(Charge.ReadyUntil>=0.)return Now<Charge.ReadyUntil?1.f:0.f;
    const double Running=Charge.RunStartedAt>=0.?FMath::Max(0.,Now-Charge.RunStartedAt):0.;
    if(Running+Charge.BankedSeconds>=ChargeSeconds+HitWindow)return 0.f;
    return FMath::Clamp(float((Charge.BankedSeconds+Running)/ChargeSeconds),0.f,1.f);
}

bool URavenQuillChargeComponent::IsMovingSprint() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Move=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    return Move&&Move->IsMovingOnGround()&&!Pawn->IsSliding()&&!Pawn->IsTraversing()
        &&!Pawn->IsMeleeSkillMovementLocked()&&Profile&&Profile->CanSprint()
        &&(Pawn->IsLocallyControlled()?Pawn->IsSprinting():Move->bWantsToSprint)
        &&Pawn->GetVelocity().SizeSquared2D()>2500.f;
}

void URavenQuillChargeComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const double Now=Clock();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Pawn&&Pawn->HasAuthority()&&!Weapon.IsEmpty())
    {
        bool Changed=false;
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Health&&Health->IsDead())
        {
            Changed=Charge.BankedSeconds>0.f||Charge.RunStartedAt>=0.||Charge.ReadyUntil>=0.;
            Charge={};EmpoweredAttacks.Reset();
        }
        else
        {
            Changed=AdvanceDeadlines(Now);
            if(Charge.ReadyUntil<0.)
            {
                const bool Running=IsMovingSprint();
                if(Running!=(Charge.RunStartedAt>=0.))
                {
                    if(Running)Charge.RunStartedAt=Now;
                    else
                    {
                        Charge.BankedSeconds+=float(FMath::Max(0.,Now-Charge.RunStartedAt));
                        Charge.RunStartedAt=-1.;
                    }
                    Changed=true;
                }
            }
        }
        if(Changed)Pawn->ForceNetUpdate();
    }
    Present(Now);
}

bool URavenQuillChargeComponent::Matches(const FColdSteelSkillShot& Shot) const
{
    return Shot.bMelee&&!Shot.bRicochet&&Shot.ItemDefinition==TEXT("ue_forged_steel_greatsword")
        &&!Weapon.IsEmpty()&&Shot.ItemInstance==Weapon;
}

float URavenQuillChargeComponent::ContactBonus(const FColdSteelSkillShot& Shot)
{
    if(!GetOwner()->HasAuthority()||!Matches(Shot))return 0.f;
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return 0.f;
    const uint64 Attack=Shot.ForgedGuardAttackKey ? Shot.ForgedGuardAttackKey : uint64(Shot.MasteryAttackSerial);
    if(Attack && EmpoweredAttacks.Contains(Attack))return 25.f;
    const double Now=Clock();
    if(AdvanceDeadlines(Now))GetOwner()->ForceNetUpdate();
    if(Charge.ReadyUntil<=Now)return 0.f;
    if(Attack)
    {
        if(EmpoweredAttacks.Num()==8)EmpoweredAttacks.RemoveAt(0);
        EmpoweredAttacks.Add(Attack);
    }
    Charge={};GetOwner()->ForceNetUpdate();Present(Now);
    return 25.f;
}

void URavenQuillChargeComponent::BindGuard(UStaticMeshComponent* Mesh)
{
    if(!Mesh||!Mesh->GetOwner()||Mesh->GetOwner()->GetNetMode()==NM_DedicatedServer)return;
    if(auto* Effect=Mesh->GetOwner()->FindComponentByClass<URavenQuillChargeComponent>())
    {
        if(!IsRavenMesh(Mesh))
        {
            if(Effect->Guards.Remove(Mesh)>0 && !UEagleTalonGuardComponent::IsEagleMesh(Mesh))
                Mesh->SetCustomPrimitiveDataFloat(GlowIndex,0.f);
            return;
        }
        Effect->Guards.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
        Effect->Guards.AddUnique(Mesh);
        Mesh->SetCustomPrimitiveDataFloat(GlowIndex,Effect->Progress(Effect->Clock()));
    }
}

void URavenQuillChargeComponent::Present(double Now)
{
    const float Glow=Progress(Now);
    if(Glow==LastGlow)return;
    LastGlow=Glow;
    for(int32 i=Guards.Num()-1;i>=0;--i)
    {
        if(auto* Mesh=Guards[i].Get();IsRavenMesh(Mesh))Mesh->SetCustomPrimitiveDataFloat(GlowIndex,Glow);
        else Guards.RemoveAtSwap(i);
    }
}

void URavenQuillChargeComponent::OnRep_Charge()
{
    Present(Clock());
    SetComponentTickEnabled(Charge.RunStartedAt>=0.||Charge.ReadyUntil>=0.);
}
