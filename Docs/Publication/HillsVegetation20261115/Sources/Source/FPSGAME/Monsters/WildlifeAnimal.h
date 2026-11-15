#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/DamageType.h"
#include "Perception/AIPerceptionTypes.h"
#include "WildlifeAnimal.generated.h"

class UQuadrupedAnimationSet;
class UQuadrupedTemplateAnimInstance;
class UMonsterCorpseRagdollComponent;
class UHillsWildlifeAudio;
class UWildlifeDistanceActivity;

/** One loot row; the roll happens once on the authoritative death. */
struct FWildlifeLootRow
{
    FString Item;
    int32 Min = 1;
    int32 Max = 1;
    float Chance = 1.f;
};

/**
 * Absolute source seconds, not a percentage of the clip. Values shipped in
 * wildlife.json are design estimates until someone watches the source frames.
 */
struct FWildlifeAttack
{
    float Damage = 0.f;
    float Range = 160.f;
    float Cooldown = 3.f;
    float Windup = .25f;
    float ContactStart = -1.f;
    float ContactEnd = -1.f;

    bool Damaging() const { return Damage > 0.f && ContactStart >= 0.f && ContactEnd > ContactStart; }
};

struct FWildlifeSpecies
{
    FString Id;
    FString DisplayName;
    FString Behavior = TEXT("skittish");
    FString AnimationSet;
    FString CharacterClass;
    float MeshYaw = -90.f;
    float CapsuleRadius = 34.f;
    float CapsuleHalfHeight = 60.f;
    int32 Level = 1;
    FString Rank = TEXT("Normal");
    float Health = 100.f;
    float PhysicalDefense = 0.f;
    float MagicDefense = 0.f;
    int32 Experience = 0;
    float WalkSpeed = 110.f;
    float RunSpeed = 450.f;
    float AlertRadius = 1200.f;
    float FleeRadius = 800.f;
    float AggroRadius = 0.f;
    float LeashRadius = 0.f;
    float HomeRadius = 1500.f;
    FString Activity = TEXT("always");
    float CorpseSeconds = 5.f;
    bool bUseRagdoll = true;
    int32 HerdMin = 1;
    int32 HerdMax = 1;
    int32 SpawnWeight = 10;
    TArray<FWildlifeLootRow> Loot;
    FWildlifeAttack Attack;

    bool Aggressive() const { return Behavior == TEXT("aggressive") || Behavior == TEXT("predator"); }
};

struct FWildlifeSpawnSettings
{
    int32 TargetPopulation = 24;
    float PopulationRadius = 9000.f;
    float ActivityRadius = 9000.f;
    float SpawnMinDistance = 4200.f;
    float SpawnMaxDistance = 8200.f;
    float DespawnDistance = 14000.f;
    float IntervalSeconds = 3.f;
    int32 MaxGlobal = 60;
    float DayStart = .26f;
    float DayEnd = .76f;
    float GroundTraceUp = 600.f;
    float GroundTraceDown = 2000.f;
    float MaxSlopeZ = .72f;
    float MinPlayerDistance = 3000.f;
};

struct FHillsWildlifeSettings
{
    float PastureDistance = 2400.f;
    float ForageSeconds = 15.f;
    float RegroupDistance = 800.f;
    float EscapeDistance = 2600.f;
    float FlightDistance = 4600.f;
    float FlightHeight = 1300.f;
    float FlightSpeed = 720.f;
};

struct FWildlifeCatalog
{
    TArray<FWildlifeSpecies> Species;
    FWildlifeSpawnSettings Spawn;
    FHillsWildlifeSettings HillsGroups;

    const FWildlifeSpecies* Find(const FString& Id) const;
    TArray<const FWildlifeSpecies*> ForActivity(bool bDay) const;
};

/** Cached reader for Content/ColdSteelData/wildlife.json. */
namespace WildlifeCatalog
{
    FPSGAME_API const FWildlifeCatalog& Get();
    FPSGAME_API void Reload();
}

UENUM(BlueprintType)
enum class EWildlifeState : uint8 { Idle, Graze, Alert, Wander, Flee, Chase, Attack, Hit, Dying, Corpse,
    TakeOff, Fly, Glide, Land, AirFall, HerdForage };

/** One replicated action, including repeated hits and the authoritative clock. */
USTRUCT()
struct FWildlifePresentationState
{
    GENERATED_BODY()
    UPROPERTY() EWildlifeState State = EWildlifeState::Idle;
    UPROPERTY() FName HitAction = NAME_None;
    UPROPERTY() double StartedAt = 0.;
    UPROPERTY() uint32 Revision = 0;
};

UCLASS()
class FPSGAME_API UWildlifeGunDamage : public UDamageType
{
    GENERATED_BODY()
};

/**
 * Ambient animal with server-owned behaviour, ground loot and a timed corpse.
 * Clients replay presentation; they never decide hits, rewards or cleanup.
 */
UCLASS(Blueprintable)
class FPSGAME_API AColdSteelAnimal : public ACharacter
{
    GENERATED_BODY()
public:
    AColdSteelAnimal(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

    /** Stable id from wildlife.json. Set on the per-species Blueprint. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wildlife") FString SpeciesId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wildlife|Animation") TObjectPtr<UQuadrupedAnimationSet> AnimationSet;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wildlife|Death") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;

    UPROPERTY(Replicated, VisibleAnywhere, BlueprintReadOnly, Category="Wildlife") float Health = 100.f;
    UPROPERTY(Replicated, VisibleAnywhere, BlueprintReadOnly, Category="Wildlife") float MaxHealth = 100.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wildlife") EWildlifeState State = EWildlifeState::Idle;

    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void PostInitializeComponents() override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;

    UFUNCTION(BlueprintCallable, Category="Wildlife") void ApplySpecies(const FString& InSpeciesId);
    UFUNCTION(BlueprintPure, Category="Wildlife") FText GetDisplayName() const;
    UFUNCTION(BlueprintPure, Category="Wildlife") bool IsDead() const { return State == EWildlifeState::Dying || State == EWildlifeState::Corpse || State == EWildlifeState::AirFall; }
    const FWildlifeSpecies* Species() const { return Row; }
    bool IsDistancePaused() const;
    void ResumeWildlifeStateClock();
    void SetHerdOrder(const FVector& Waypoint, bool bAtSlot, bool bRun, bool bPanic);
    void SetFlightOrder(const FVector& Waypoint, EWildlifeState Phase, bool bAlarm);
    bool InFlockFlight() const;
    virtual void Landed(const FHitResult& Hit) override;
    virtual void LifeSpanExpired() override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wildlife|Behaviour", meta=(ClampMin="0", Units="s"))
    float IdleMinSeconds = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wildlife|Behaviour", meta=(ClampMin="0", Units="s"))
    float IdleMaxSeconds = 9.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wildlife|Death", meta=(ClampMin="0", ClampMax="1"))
    float DeathAnimationFraction = .6f;

protected:
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
    UPROPERTY() TObjectPtr<UHillsWildlifeAudio> WildlifeAudio;
    UPROPERTY() TObjectPtr<UWildlifeDistanceActivity> DistanceActivity;
    UPROPERTY(Replicated)
    FString ReplicatedSpeciesId;

    UPROPERTY(ReplicatedUsing=OnRep_Presentation) FWildlifePresentationState Presentation;
    UFUNCTION() void OnRep_Presentation();
    double PresentationClock() const;
    void ApplyDeadCollision();
    friend struct FWildlifeWireAuditAccess;
    UFUNCTION() void OnHillsNoise(AActor* Source, FAIStimulus Stimulus);
    UFUNCTION(NetMulticast, Unreliable) void MulticastModelHit(FName Bone, FVector_NetQuantize Point,
        FVector_NetQuantizeNormal Direction, float Applied);
    void RememberThreat(const FVector& Source);
    void ListenForHillsNoise();

    void LoadSpecies();
    void AlignVisual();
    UQuadrupedTemplateAnimInstance* Animation() const;
    float ClipLength(FName Action) const;
    void SampleAction(FName Action, float SourceSeconds);

    void TickAuthoritative(float DeltaSeconds);
    void TickHillsOrder(float DeltaSeconds);
    void TickPresentation(float DeltaSeconds);
    void EnterState(EWildlifeState NewState);
    void PickWanderPoint();
    void PickFleePoint(APawn* Threat);
    void SteerTo(const FVector& Destination, float Speed, float ArriveRadius);
    bool PlayerThreat(APawn*& OutThreat, float& OutDistance) const;
    bool BlockedTooLong(float DeltaSeconds);
    void StartAttack(APawn* Victim);
    void TryContact();
    void FinishAttack();
    void Die(AController* Killer);
    void EnterRagdoll();

    const FWildlifeSpecies* Row = nullptr;
    TWeakObjectPtr<APawn> Target;
    FVector Home = FVector::ZeroVector;
    FVector Goal = FVector::ZeroVector;
    FVector IncomingHit = FVector::ZeroVector;
    FVector LastProgress = FVector::ZeroVector;
    FRandomStream Random;
    float StateSeconds = 0.f;
    float IdleSeconds = 0.f;
    float AttackCooldownLeft = 0.f;
    float StuckSeconds = 0.f;
    float HitSeconds = 0.f;
    FName HitAction = NAME_None;
    FVector ThreatPosition = FVector::ZeroVector;
    double ThreatUntil = -1.;
    double NextEscapeStep = 0.;
    bool bAttackConsumed = false;
    bool bSpeciesReady = false;
    bool bHillsGroup = false;
    bool bHerdAtSlot = true;
    bool bHerdRun = false;
    bool bHerdPanic = false;
    FVector GroupWaypoint = FVector::ZeroVector;
};
