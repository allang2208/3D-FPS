#pragma once
#include "CoreMinimal.h"
#include "WolfMonster.h"
#include "BellowSacLobber.generated.h"

class ABellowSacProjectile;
class AMonsterAIController;
class UStaticMesh;
class UMaterialInterface;
class UAudioComponent;
class USoundBase;

UENUM()
enum class EBellowAttack : uint8 { None, Lob, Shove };

USTRUCT()
struct FBellowAttackClock
{
    GENERATED_BODY()
    UPROPERTY() EBellowAttack Kind = EBellowAttack::None;
    UPROPERTY() double StartedAt = 0.;
};

/** Original four-foot rig with a single clock for pressure, release and recovery. */
UCLASS(Blueprintable)
class FPSGAME_API ABellowSacLobber : public AWolfMonster
{
    GENERATED_BODY()
public:
    ABellowSacLobber(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual bool Busy() const override;
    virtual bool CanAttack(APawn* Victim) const override;
    virtual bool StartAttack(APawn* Victim) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    void NavigateCombat(AMonsterAIController* AI, APawn* VisibleTarget, const FVector& LastKnown);
    void NotifyDiscovery(bool DirectDiscovery);

    UPROPERTY(EditDefaultsOnly, Category="Bellow|Audio") TMap<FName,TObjectPtr<USoundBase>> BellowSounds;
    UPROPERTY(EditAnywhere, Category="Bellow|Audio", meta=(ClampMin="0")) float CreatureAudioGain = 1.35f;

    UPROPERTY(EditAnywhere, Category="Bellow|Projectile") TObjectPtr<UStaticMesh> SacMesh;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile") TObjectPtr<UStaticMesh> TelegraphMesh;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile") TObjectPtr<UMaterialInterface> SacMaterial;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile") TObjectPtr<UMaterialInterface> TelegraphMaterial;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile") float BlastDamage = 48.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile", meta=(Units="cm")) float BlastRadius = 140.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Projectile", meta=(Units="s")) float ImpactFuse = .65f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="cm")) float LobMinRange = 400.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="cm")) float LobMaxRange = 2800.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="cm")) float PreferredRange = 1800.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack") float ShoveDamage = 24.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="cm")) float ShoveRange = 450.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Hearing") bool bSoundSensitive = true;
    UPROPERTY(EditAnywhere, Category="Bellow|Hearing", meta=(ClampMin="0", Units="cm")) float HearingRadius = 3600.f;
    // Start-to-start interval, including pressure, release and recovery.
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="s")) float LobCooldownMin = 4.f;
    UPROPERTY(EditAnywhere, Category="Bellow|Attack", meta=(Units="s")) float LobCooldownMax = 4.f;
protected:
    virtual void OnDeathPresentationStarted() override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Attack) FBellowAttackClock AttackClock;
    UFUNCTION() void OnRep_Attack();
    TWeakObjectPtr<APawn> AttackTarget;
    TWeakObjectPtr<ABellowSacProjectile> ActiveCapsule;
    FVector LockedGround = FVector::ZeroVector;
    double NextLobAt = 0., NextShoveAt = 0., EncounterReadyAt = -1.;
    bool bLocked = false, bReleased = false;
    mutable double NextLaneQuery = 0.;
    mutable bool bClearLane = false;
    mutable TWeakObjectPtr<APawn> LaneTarget;
    double Clock() const;
    FVector Muzzle() const;
    bool Visible(APawn* Victim) const;
    bool GroundTarget(APawn* Victim, FVector& Ground) const;
    bool BuildArc(const FVector& Origin, const FVector& Ground, FVector& Velocity, const AActor* IntendedTarget = nullptr) const;
    bool HasLane(APawn* Victim) const;
    void SampleAttack(float Seconds, bool EvaluateMouth = false);
    void FinishAttack(bool Resume);
    void ReleaseCapsule();
    void ApplyShove();
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> PressureVoice;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> CreatureVoice;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> ContactVoice;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> FootstepVoice;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> HurtVoice;
    double AudioAttackStartedAt = -1., NextAlertSoundAt = 0.;
    double NextHurtSoundAt = 0.;
    float LastFootstepPhase = 0.f;
    bool bHadFootstepPhase = false;
    int32 LastFootstepVariant = 0, LastHurtVariant = 0;
    bool bDeathAudioPlayed = false, bCorpseImpactPlayed = false;
    void InitializeBellowAudio();
    void UpdatePressureAudio();
    void UpdateFootstepAudio(float DeltaSeconds);
    void StopBellowAudio();
    void PlayBellowVoice(UAudioComponent* Voice, FName CueRole, float Gain = 1.f, float Age = 0.f);
    void PlayDeathAudio();
    void OnCorpseGroundImpact(const FVector& Location, float SpeedCm);
    UFUNCTION(NetMulticast, Unreliable) void MulticastBellowAccent(FName CueRole, FVector_NetQuantize Location, double StartedAt, float Gain);
};
