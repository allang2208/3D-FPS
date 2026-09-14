#include "FatZombiePusPool.h"
#include "FPSCombatHealthComponent.h"
#include "MonsterCombatComponent.h"
#include "../Skills/CorrosivePusDamage.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GenericTeamAgentInterface.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
FName FactionOf(const APawn* Pawn)
{
    if (!Pawn) return NAME_None;
    if (Pawn->IsPlayerControlled() || Pawn->ActorHasTag(TEXT("Friendly")) || Pawn->ActorHasTag(TEXT("Player"))) return TEXT("Player");
    if (Pawn->ActorHasTag(TEXT("Enemy")) || Pawn->FindComponentByClass<UMonsterCombatComponent>()) return TEXT("Enemy");
    return NAME_None;
}
uint8 TeamOf(const APawn* Pawn)
{
    if (const auto* Agent = Cast<IGenericTeamAgentInterface>(Pawn->GetController()))
        if (Agent->GetGenericTeamId() != FGenericTeamId::NoTeam) return Agent->GetGenericTeamId().GetId();
    if (const auto* Agent = Cast<IGenericTeamAgentInterface>(Pawn)) return Agent->GetGenericTeamId().GetId();
    return FGenericTeamId::NoTeam.GetId();
}
}

AFatZombiePusPool::AFatZombiePusPool()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .05f;
    Surface = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("PusFilm"));
    SetRootComponent(Surface);
    Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Surface->SetGenerateOverlapEvents(false);
    Surface->SetCanEverAffectNavigation(false);
    Surface->SetCastShadow(false);
    Surface->bEnableComplexCollision = false;
    Surface->SetDeferredCollisionUpdatesEnabled(true, false);
    Surface->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    SetCanBeDamaged(false);
    Tags.Add(TEXT("CorrosivePus"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Game/Monsters/FatZombieMeshy/Pus/MI_FatZombie_Pus.MI_FatZombie_Pus"));
    PusMaterial = Material.Object;
}

void AFatZombiePusPool::InitializeFrom(APawn* Source, const FFatZombiePusSettings& Settings)
{
    Tuning = Settings;
    Tuning.Interval = FMath::Max(.1f, Tuning.Interval);
    Tuning.Duration = FMath::Max(Tuning.Interval, Tuning.Duration);
    Tuning.SpreadSeconds = FMath::Clamp(Tuning.SpreadSeconds, 0.f, Tuning.Duration);
    Tuning.LongRadius = FMath::Max(30.f, Tuning.LongRadius);
    Tuning.ShortRadius = FMath::Max(20.f, Tuning.ShortRadius);
    Tuning.MinDroplets = FMath::Clamp(Tuning.MinDroplets, 0, 24);
    Tuning.MaxDroplets = FMath::Clamp(Tuning.MaxDroplets, Tuning.MinDroplets, 24);
    Tuning.FadeSeconds = FMath::Max(0.f, Tuning.FadeSeconds);
    Seed = Tuning.ShapeSeed != 0 ? Tuning.ShapeSeed : FMath::RandRange(1, MAX_int32-1);
    SourcePawn = Source;
    SourceFaction = FactionOf(Source);
    if (Source)
    {
        DamageInstigator = Source->GetController();
        SourceTeam = TeamOf(Source);
        SetOwner(Source->GetOwner());
        if (Source->ActorHasTag(TEXT("DevelopmentSpawned"))) Tags.AddUnique(TEXT("DevelopmentSpawned"));
    }
}

void AFatZombiePusPool::BeginPlay()
{
    Super::BeginPlay();
    if (!PusMaterial || !BuildFootprint())
    {
        UE_LOG(LogTemp, Warning, TEXT("FAT_PUS_NO_SURFACE material=%s location=%s"), *GetNameSafe(PusMaterial), *GetActorLocation().ToString());
        Destroy();
        return;
    }
    Liquid = Surface->CreateDynamicMaterialInstance(0, PusMaterial);
    StartTime = GetWorld()->GetTimeSeconds();
    SetActorTickInterval(Tuning.SpreadSeconds > 0.f ? 0.f : .05f);
    Liquid->SetScalarParameterValue(TEXT("SpreadProgress"), GetSpreadProgress(0.f));
    Liquid->SetScalarParameterValue(TEXT("Visibility"), 1.f);
    Liquid->SetScalarParameterValue(TEXT("Dryness"), 0.f);
    FRandomStream TintRandom(Seed ^ 0x713AC);
    Liquid->SetScalarParameterValue(TEXT("Variation"), TintRandom.FRand());
    // First pulse at +interval; include the pulse exactly at duration, never after it.
    if (HasAuthority()) GetWorldTimerManager().SetTimer(DamageTimer, this, &ThisClass::PulseDamage, Tuning.Interval, true, Tuning.Interval);
    SetLifeSpan(Tuning.Duration + Tuning.FadeSeconds + .1f);
    UE_LOG(LogTemp, Display, TEXT("FAT_PUS_SPAWN seed=%d triangles=%d duration=%.2f interval=%.2f magic_damage=%.2f faction=%s spread=%.2f"),
        Seed, GroundTriangles.Num(), Tuning.Duration, Tuning.Interval, Tuning.Damage, *SourceFaction.ToString(), Tuning.SpreadSeconds);
}

float AFatZombiePusPool::GetSpreadProgress(float Age) const
{
    if (Tuning.SpreadSeconds <= 0.f) return 1.f;
    const float T = FMath::Clamp(Age / Tuning.SpreadSeconds, 0.f, 1.f);
    // A small initial wet spot, followed by fast flow that settles at the rim.
    return .06f + .94f * (1.f - FMath::Square(1.f - T));
}

void AFatZombiePusPool::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Liquid) return;
    const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartTime);
    Liquid->SetScalarParameterValue(TEXT("SpreadProgress"), GetSpreadProgress(Age));
    if (Age >= Tuning.SpreadSeconds && PrimaryActorTick.TickInterval == 0.f) SetActorTickInterval(.05f);
    const float Dry = Tuning.FadeSeconds > 0.f ? FMath::Clamp((Age-Tuning.Duration)/Tuning.FadeSeconds, 0.f, 1.f) : (Age>Tuning.Duration?1.f:0.f);
    Liquid->SetScalarParameterValue(TEXT("Visibility"), 1.f-Dry);
    Liquid->SetScalarParameterValue(TEXT("Dryness"), Dry);
}

bool AFatZombiePusPool::IsHostile(const APawn* Target) const
{
    if (!IsValid(Target) || Target == SourcePawn.Get() || !Target->CanBeDamaged()) return false;
    if (const auto* Health = Target->FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead()) return false;
    if (const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>(); Combat && Combat->IsDead()) return false;
    const uint8 OtherTeam = TeamOf(Target);
    if (SourceTeam != 255 && OtherTeam != 255)
        return FGenericTeamId::GetAttitude(FGenericTeamId(SourceTeam), FGenericTeamId(OtherTeam)) == ETeamAttitude::Hostile;
    const FName OtherFaction = FactionOf(Target);
    return !OtherFaction.IsNone() && !SourceFaction.IsNone() && OtherFaction != SourceFaction;
}

void AFatZombiePusPool::PulseDamage()
{
    const float ScheduledTime = (DamagePulses+1)*Tuning.Interval;
    if (!HasAuthority() || ScheduledTime > Tuning.Duration+KINDA_SMALL_NUMBER)
    { GetWorldTimerManager().ClearTimer(DamageTimer); return; }
    ++DamagePulses;
    const float Spread = GetSpreadProgress(static_cast<float>(GetWorld()->GetTimeSeconds() - StartTime));
    if (Liquid) Liquid->SetScalarParameterValue(TEXT("SpreadProgress"), Spread);
    TArray<FOverlapResult> Contacts;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FatPusTargets), false, this);
    GetWorld()->OverlapMultiByObjectType(Contacts, GetActorLocation()+FVector(0,0,55), FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeSphere(QueryRadius+100.f), Query);
    TSet<APawn*> Visited;
    for (const auto& Contact : Contacts)
    {
        auto* Target = Cast<APawn>(Contact.GetActor());
        if (!Target || Visited.Contains(Target)) continue;
        Visited.Add(Target); // Multiple limbs and multiple splashes still mean one hit per pool/pulse.
        if (!IsHostile(Target) || !TouchesGround(Target, Spread)) continue;
        if (UGameplayStatics::ApplyDamage(Target, Tuning.Damage, DamageInstigator.Get(), this, UCorrosivePusDamage::StaticClass()) > 0.f) ++SuccessfulHits;
    }
    if ((DamagePulses+1)*Tuning.Interval > Tuning.Duration+KINDA_SMALL_NUMBER) GetWorldTimerManager().ClearTimer(DamageTimer);
}

void AFatZombiePusPool::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DamageTimer);
    Super::EndPlay(Reason);
}
