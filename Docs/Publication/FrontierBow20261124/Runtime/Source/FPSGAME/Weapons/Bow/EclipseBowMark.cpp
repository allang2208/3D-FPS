#include "EclipseBowMark.h"
#include "BowStats.h"

#include "../../Combat/CombatStatusFormula.h"
#include "../../Combat/RangedAttackQuery.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../Props/FPSPracticeTarget.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/StatusEffectsComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

TSharedPtr<FEclipseBowShot> FEclipseBowShot::Capture(APawn* Shooter)
{
    if (!Shooter || !Shooter->HasAuthority() || !Shooter->IsPlayerControlled()) return nullptr;
    const auto* Profile = ColdSteelAuthority::ForPawn(Shooter);
    const auto* Bow = Profile ? Profile->ActiveBow() : nullptr;
    if (!ColdSteelBow::EclipseRiser(Profile, Bow)) return nullptr;
    auto Shot = MakeShared<FEclipseBowShot>();
    Shot->Shooter = Shooter;
    return Shot;
}

UEclipseBowMark::UEclipseBowMark()
{
    SetIsReplicatedByDefault(true);
    if (!IsRunningDedicatedServer())
    {
        static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Game/Weapons/FrontierCompoundBow/EclipseAuraR3/M_EclipseGroundAura.M_EclipseGroundAura"));
        AuraMaterial = Material.Object;
    }
}

double UEclipseBowMark::Clock() const
{
    const auto* World = GetWorld();
    const auto* GS = World->GetGameState();
    return GS ? GS->GetServerWorldTimeSeconds() : World->GetTimeSeconds();
}

int32 UEclipseBowMark::ActiveLayers() const
{
    return Mark.ExpiresAt > Clock() ? Mark.Layers : 0;
}

double UEclipseBowMark::DamageMultiplier(const AActor* Target)
{
    const auto* Effect = Target ? Target->FindComponentByClass<UEclipseBowMark>() : nullptr;
    return Effect ? 1. + .03 * Effect->ActiveLayers() : 1.;
}

bool UEclipseBowMark::CanMark(AActor* Target, APawn* Shooter)
{
    if (!IsValid(Target) || !Target->HasAuthority() || Target->IsActorBeingDestroyed() || !Target->CanBeDamaged()) return false;
    if (RangedAttackQuery::IsFriendlyUnit(Shooter, Target)) return false;
    if (!Shooter && (Target->ActorHasTag(TEXT("Friendly")) || Target->ActorHasTag(TEXT("Companion")) || Target->ActorHasTag(TEXT("Player")))) return false;
    if (const auto* Status = Target->FindComponentByClass<UCombatStatusFormula>(); Status && Status->IsImmune()) return false;
    if (Target->IsA<AFPSPracticeTarget>()) return true;
    const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>();
    return Combat && !Combat->IsDead();
}

void UEclipseBowMark::Add(AActor* Target, APawn* Shooter, int32 Count)
{
    auto* Effect = Target->FindComponentByClass<UEclipseBowMark>();
    if (!Effect)
    {
        Effect = NewObject<UEclipseBowMark>(Target);
        Target->AddInstanceComponent(Effect);
        Effect->RegisterComponent();
    }
    Effect->Mark.Layers = FMath::Min(MaxLayers, Effect->ActiveLayers() + Count);
    Effect->Mark.ExpiresAt = Effect->Clock() + Duration;
    if (Shooter) Effect->LastShooter = Shooter;
    Target->GetWorldTimerManager().SetTimer(Effect->ExpiryTimer, Effect, &UEclipseBowMark::Clear, Duration, false);
    Effect->OnRep_Mark();
    Target->ForceNetUpdate();
}

void UEclipseBowMark::Clear()
{
    GetWorld()->GetTimerManager().ClearTimer(ExpiryTimer);
    Mark = {};
    LastShooter.Reset();
    OnRep_Mark();
    GetOwner()->ForceNetUpdate();
}

void UEclipseBowMark::OnRep_Mark()
{
    static const FName Type(TEXT("eclipsePhase"));
    const float Remaining = float(Mark.ExpiresAt - Clock());
    if (Mark.Layers && Remaining > 0.f)
    {
        UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(Type, Remaining, Mark.Layers);
        StartGroundAura();
    }
    else
    {
        StopGroundAura();
        if (auto* Display = GetOwner()->FindComponentByClass<UStatusEffectsComponent>())
            Display->Remove(Type);
    }
}

void UEclipseBowMark::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UEclipseBowMark, Mark);
}

thread_local FEclipseBowImpact* FEclipseBowImpact::Current = nullptr;

FEclipseBowImpact::FEclipseBowImpact(FEclipseBowShot* InShot, AActor* InTarget)
    : Previous(Current), Shot(InShot), Target(InTarget)
{
    if (Shot && !Shot->MarkedTargets.Contains(Target) && UEclipseBowMark::CanMark(Target, Shot->Shooter.Get()))
        Current = this;
    else
        Shot = nullptr;
}

FEclipseBowImpact::~FEclipseBowImpact()
{
    Current = Previous;
}

void FEclipseBowImpact::Confirm(float Damage)
{
    if (!Shot || Damage <= 0 || Shot->MarkedTargets.Contains(Target) || !UEclipseBowMark::CanMark(Target, Shot->Shooter.Get())) return;
    Shot->MarkedTargets.Add(Target);
    UEclipseBowMark::Add(Target, Shot->Shooter.Get(), 1);
}

void FEclipseBowImpact::OnDeath(AActor* Victim)
{
    auto* Effect = Victim->FindComponentByClass<UEclipseBowMark>();
    int32 Layers = Effect ? Effect->ActiveLayers() : 0;
    APawn* Shooter = Effect ? Effect->LastShooter.Get() : nullptr;
    // Death is reported synchronously, before ApplyDamage returns the lethal hit.
    if (Current && Current->Target == Victim && !Current->Shot->MarkedTargets.Contains(Victim))
    {
        Current->Shot->MarkedTargets.Add(Victim);
        Layers = FMath::Min(UEclipseBowMark::MaxLayers, Layers + 1);
        Shooter = Current->Shot->Shooter.Get();
    }
    if (!Layers) return;
    if (Effect) Effect->Clear();
    const FVector Center = Victim->GetActorLocation();
    FCollisionObjectQueryParams Types(ECC_Pawn);
    Types.AddObjectTypesToQuery(ECC_WorldDynamic);
    Types.AddObjectTypesToQuery(ECC_PhysicsBody);
    Types.AddObjectTypesToQuery(ECC_WorldStatic); // Practice targets use the BlockAll collision profile.
    TArray<FOverlapResult> Results;
    Victim->GetWorld()->OverlapMultiByObjectType(Results, Center, FQuat::Identity, Types,
        FCollisionShape::MakeSphere(UEclipseBowMark::SpreadRadius), FCollisionQueryParams(SCENE_QUERY_STAT(EclipseBowSpread), false, Victim));
    TSet<AActor*> Seen;
    for (const auto& Result : Results)
    {
        AActor* Other = Result.GetActor();
        if (!Other || Seen.Contains(Other)) continue;
        Seen.Add(Other);
        if (FVector::DistSquared(Center, Other->GetActorLocation()) <= FMath::Square(UEclipseBowMark::SpreadRadius)
            && UEclipseBowMark::CanMark(Other, Shooter))
            UEclipseBowMark::Add(Other, Shooter, Layers);
    }
}
