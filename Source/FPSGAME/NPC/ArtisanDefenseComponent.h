#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ArtisanDefenseComponent.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;
class UAnimSequence;
class USoundAttenuation;
class UBowFlexMeshComponent;
struct FStreamableHandle;

UENUM()
enum class EArtisanGuardState : uint8
{
    AtWork, Approach, Ready, Attack, Release, Returning, Downed, Watching
};

UCLASS()
class FPSGAME_API UArtisanDefenseComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UArtisanDefenseComponent();
    void SetDowned(bool bDowned);
    void SetAttackDamage(float NewDamage) { AttackDamage = FMath::Max(1.f, NewDamage); }
    bool IsAtWork() const { return State == EArtisanGuardState::AtWork; }
    bool IsKeepingWatch() const { return State == EArtisanGuardState::Watching; }
    bool IsAlerted() const;
    void RefreshPresentation();
    FSimpleMulticastDelegate OnResumeWork;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_State) EArtisanGuardState State = EArtisanGuardState::AtWork;
    // A short release or ready state may be coalesced between network updates.
    UPROPERTY(ReplicatedUsing=OnRep_State) float StateStartedAt = 0.f;
    UFUNCTION() void OnRep_State();
    void ChangeState(EArtisanGuardState NewState);
    bool IsBow() const;
    void StepGuard(float Dt, double Now);
    void SetTarget(AActor* NewTarget);
    void StartWatching(double Now);
    void StartReturning(double Now);
    bool AcquireNearbyThreat(double Now);
    bool CanSee(AActor* Other) const;
    void ShootArrow(AActor* Other);
    void StepHammerSwing(AActor* Target, float Dt, double Now);
    bool SweepHammer(float FromTime, float ToTime);
    UPROPERTY(Replicated) float HammerPitch = 0.f;
    UPROPERTY(Replicated) bool bCloseHammer = false;
    float HammerTraceTime = 0.f;
    UFUNCTION(NetMulticast, Unreliable) void MulticastHammerSound(bool bImpact, FVector_NetQuantize Location);
    UPROPERTY(Transient) TObjectPtr<USoundAttenuation> HammerAttenuation;
    TSharedPtr<FStreamableHandle> HammerAudioAssets;
    bool bPlayedHammerSwing = false;
    void TurnToward(const FVector& Direction, float Dt);
    bool MoveToward(const FVector& Goal, float Dt, double Now);
    bool BuildRoute(const FVector& Goal);
    void ClearRoute();
    void RestoreStation(double Now, float Dt);
    bool CanStandAt(const FVector& Center) const;
    bool bWaitingBesideStation = false;
    void UpdateGrip();
    void WarmPresentation();
    TSharedPtr<FStreamableHandle> PresentationAssets;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Hammer;
    UPROPERTY(Transient) TObjectPtr<UBowFlexMeshComponent> Bow;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Strings;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> NockedArrow;
    UPROPERTY(Transient) TMap<EArtisanGuardState, TObjectPtr<UAnimSequence>> Clips;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> HammerCloseClip;
    TWeakObjectPtr<AActor> Threat;
    FVector Station = FVector::ZeroVector;
    FRotator StationRotation = FRotator::ZeroRotator;
    FVector LastSeen = FVector::ZeroVector;
    FVector PreviousGoal = FVector::ZeroVector;
    FVector ProgressSample = FVector::ZeroVector;
    FVector SmithProbeHeading = FVector::ZeroVector;
    FVector SmithClearDirection = FVector::ZeroVector;
    double NextSmithProbe = 0.;
    TArray<FVector> Route;
    int32 RouteIndex = 0;
    int32 Detour = 0;
    double NextScan = 0, NextPath = 0, LastSeenAt = 0, AttackStarted = 0, NextAttack = 0;
    double ProgressAt = 0, LastReturnProgress = 0, LastThreatProgress = 0;
    double NextSight = 0;
    double BestReturnDistance = 0, BestThreatDistance = 0;
    struct FUnreachableThreat
    {
        FVector Location;
        double RetryAfter;
    };
    TMap<TWeakObjectPtr<AActor>, FUnreachableThreat> UnreachableThreats;
    float AttackDamage = 0.f;
    float HammerClipContact = 0.f;
    bool bStruck = false;
    bool bLastVisible = false;
    bool bNavigationInvokerRegistered = false;
    friend struct FSmithHammerAnimProxy;
};
