#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "HeQueMonster.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UPhysicsAsset;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UAudioComponent;
class USoundBase;
class USoundAttenuation;
UENUM()
enum class EHeQueReaction : uint8 { None, Hit, Stunned, Airborne, Landing, Down, GetUp, Dying };
USTRUCT()
struct FHeQueReactionState
{
    GENERATED_BODY()
    UPROPERTY() EHeQueReaction Phase=EHeQueReaction::None;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() double EndsAt=0.;
    UPROPERTY() uint8 Direction=0;
    UPROPERTY() float DeathLead=.65f;
};
USTRUCT()
struct FHeQueSweepFrame
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) float Time=0.f;
    UPROPERTY(EditAnywhere) TArray<FVector> Points;
};
USTRUCT()
struct FHeQueSweepState
{
    GENERATED_BODY()
    UPROPERTY() bool Active=false;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
};
USTRUCT()
struct FHeQuePressurePacket
{
    GENERATED_BODY()
    UPROPERTY() bool Released=false;
    UPROPERTY() FVector Origin=FVector::ZeroVector;
    UPROPERTY() float Stop=-1.f;
    UPROPERTY() FVector ImpactPoint=FVector::ZeroVector;
    UPROPERTY() FVector ImpactNormal=FVector::UpVector;
    UPROPERTY() bool HitWorld=false;
};
USTRUCT()
struct FHeQueRiftState
{
    GENERATED_BODY()
    UPROPERTY() bool Active=false;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() FVector Origin=FVector::ZeroVector;
    UPROPERTY() FVector Direction=FVector::ForwardVector;
    UPROPERTY() FHeQuePressurePacket PacketA;
    UPROPERTY() FHeQuePressurePacket PacketB;
};
USTRUCT()
struct FHeQuePsychicState
{
    GENERATED_BODY()
    UPROPERTY() bool Active=false;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() uint8 ReleasedMask=0;
    UPROPERTY() TArray<FVector> Origins;
};
UENUM()
enum class EHeQueJumpPhase : uint8 { None, Charge, Rising, Falling, Recovery };
USTRUCT()
struct FHeQueJumpState
{
    GENERATED_BODY()
    UPROPERTY() EHeQueJumpPhase Phase=EHeQueJumpPhase::None;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() FVector ImpactPoint=FVector::ZeroVector;
    UPROPERTY() FVector ImpactNormal=FVector::UpVector;
};
/** HeQue locomotion, heavy clamp, side crush, rift pressure and shared reactions. */
UCLASS(Blueprintable)
class FPSGAME_API AHeQueMonster : public ACharacter
{
    GENERATED_BODY()
public:
    AHeQueMonster(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Landed(const FHitResult& Hit) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HeQue") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,Category="HeQue") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Assets") TObjectPtr<UPhysicsAsset> HitSurfacePhysics;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|SideCrush") TObjectPtr<UAnimSequence> SweepClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|SideCrush") TArray<FHeQueSweepFrame> SweepFrames;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|SideCrush") TObjectPtr<USoundBase> SweepSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|SideCrush") TObjectPtr<USoundAttenuation> SweepAttenuation;
    UPROPERTY(EditAnywhere,Category="HeQue|SideCrush",meta=(ClampMin="0")) float SweepDamage=60.f;
    UPROPERTY(EditAnywhere,Category="HeQue|SideCrush",meta=(ClampMin="0",Units="cm")) float SweepPushDistance=1000.f;
    UPROPERTY(EditAnywhere,Category="HeQue|SideCrush",meta=(ClampMin="1",Units="cm")) float SweepTriggerRange=355.f;
    /** Lateral padding around the swept kick volume, in world centimetres. */
    UPROPERTY(EditDefaultsOnly,Category="HeQue|SideCrush",meta=(ClampMin="1",Units="cm")) float SweepHitRadius=45.f;
    UPROPERTY(EditAnywhere,Category="HeQue|SideCrush",meta=(ClampMin="3.2",Units="s")) float SweepCooldown=4.6f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|HeavyClamp") TObjectPtr<UAnimSequence> ClampClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|HeavyClamp") TArray<FHeQueSweepFrame> ClampFrames;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|HeavyClamp") TObjectPtr<USoundBase> ClampSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|HeavyClamp") TObjectPtr<USoundAttenuation> ClampAttenuation;
    UPROPERTY(EditAnywhere,Category="HeQue|HeavyClamp",meta=(ClampMin="0")) float ClampDamage=85.f;
    UPROPERTY(EditAnywhere,Category="HeQue|HeavyClamp",meta=(ClampMin="1",Units="cm")) float ClampTriggerRange=310.f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|HeavyClamp",meta=(ClampMin="1",Units="cm")) float ClampHitRadius=18.f;
    UPROPERTY(EditAnywhere,Category="HeQue|HeavyClamp",meta=(ClampMin="4.2",Units="s")) float ClampCooldown=6.8f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UAnimSequence> RiftClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UStaticMesh> PressureMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UStaticMesh> PressureMembraneMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UStaticMesh> PressureMistMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UStaticMesh> PressureImpactMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UMaterialInterface> PressureMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UMaterialInterface> MembraneMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UMaterialInterface> PressureMistMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UMaterialInterface> PressureImpactMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<UMaterialInterface> PressureDustMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TArray<FVector> RiftReleasePoints;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<USoundBase> RiftSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<USoundBase> RiftImpactSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|RiftPressure") TObjectPtr<USoundAttenuation> RiftAttenuation;
    UPROPERTY(EditAnywhere,Category="HeQue|RiftPressure") float RiftDamage=38.f;
    UPROPERTY(EditAnywhere,Category="HeQue|RiftPressure") float RiftRange=4800.f;
    UPROPERTY(EditAnywhere,Category="HeQue|RiftPressure") float RiftSpeed=1400.f;
    UPROPERTY(EditAnywhere,Category="HeQue|RiftPressure") float RiftCooldown=7.5f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<UAnimSequence> PsychicClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<UStaticMesh> PsychicWaveMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<UMaterialInterface> PsychicWaveMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<UMaterialInterface> PsychicCoreMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<UMaterialInterface> PsychicFearViewMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<USoundBase> PsychicSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<USoundBase> PsychicFearSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TObjectPtr<USoundAttenuation> PsychicAttenuation;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") TArray<FVector> PsychicReleasePoints;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") FVector PsychicCoreOffset=FVector::ZeroVector;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Psychic") int32 PsychicBodyMaterialSlot=0;
    UPROPERTY(EditAnywhere,Category="HeQue|Psychic") float PsychicRadius=1000.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Psychic") float PsychicDamage=25.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Psychic") float PsychicCooldown=30.f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UAnimSequence> JumpChargeClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UAnimSequence> JumpAirClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UAnimSequence> JumpDiveClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UAnimSequence> JumpRecoverClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UStaticMesh> JumpWaveMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UStaticMesh> JumpImpactMesh;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UMaterialInterface> JumpWaveMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<UMaterialInterface> JumpImpactMaterial;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<USoundBase> JumpChargeSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<USoundBase> JumpAirSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<USoundBase> JumpImpactSound;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|JumpSlam") TObjectPtr<USoundAttenuation> JumpAttenuation;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpHeight=210.f;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpImpactRadius=220.f;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpImpactDamage=75.f;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpWaveRadius=700.f;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpWaveDamage=45.f;
    UPROPERTY(EditAnywhere,Category="HeQue|JumpSlam") float JumpCooldown=14.f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TArray<TObjectPtr<UAnimSequence>> HitClips;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TObjectPtr<UAnimSequence> StunClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TObjectPtr<UAnimSequence> AirClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TObjectPtr<UAnimSequence> LandClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TObjectPtr<UAnimSequence> GetUpClip;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Reactions") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere,Replicated,Category="HeQue|Stats") float MaxHealth=6000.f;
    UPROPERTY(VisibleAnywhere,Replicated,Category="HeQue|Stats") float Health=6000.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Stats") int32 Level=12;
    UPROPERTY(EditAnywhere,Category="HeQue|Stats") EMonsterRank Rank=EMonsterRank::Boss;
    UPROPERTY(EditAnywhere,Category="HeQue|Stats") int32 ExperienceReward=0;
    UPROPERTY(EditAnywhere,Category="HeQue|Death") float CorpseSeconds=25.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Movement") float WalkSpeed=100.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Movement") float ReturnSpeed=80.f;
    UPROPERTY(EditAnywhere,Category="HeQue|Movement") float TurnSpeed=120.f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") float StrideDistance=198.5294f;
    UPROPERTY(EditDefaultsOnly,Category="HeQue|Animation") float TurnStrideDegrees=82.f;
    UPROPERTY(EditAnywhere,Category="HeQue|AI") float AggroRadius=2200.f;
    UPROPERTY(EditAnywhere,Category="HeQue|AI") float LeashRadius=3200.f;
    UPROPERTY(EditAnywhere,Category="HeQue|AI") float StoppingDistance=280.f;
    FVector Home=FVector::ZeroVector;
    bool Dead() const {return Health<=0.f||Reaction.Phase==EHeQueReaction::Dying;}
    bool IsKnockedDown() const;
    bool Controlled() const {return !Dead()&&Reaction.Phase!=EHeQueReaction::None;}
    bool Busy() const {return Dead()||Controlled()||Sweep.Active||IsRifting()||Clamp.Active||Psychic.Active||IsJumpSlamming();}
    void SetCombatTarget(APawn* Victim);
    APawn* PreferredCombatTarget(APawn* Victim) const;
    bool IsWeakpointHit(const FHitResult& Hit) const;
    void ResolveRemoteHit(const FVector& Origin,const FVector& Point,FHitResult& Hit) const;
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void CancelAttack();
    bool DesiredCombatFacing(float& Yaw) const;
    bool IsSweeping() const {return Sweep.Active&&!Dead()&&!Controlled();}
    float SweepAge() const;
    uint32 SweepSerial() const {return Sweep.Serial;}
    bool IsClamping() const {return Clamp.Active&&!Dead()&&!Controlled();}
    float ClampAge() const;
    uint32 ClampSerial() const {return Clamp.Serial;}
    bool IsRifting() const;
    float RiftAge() const;
    uint32 RiftSerial() const;
    bool IsPsychic() const {return Psychic.Active&&!Dead()&&!Controlled();}
    float PsychicAge() const;
    uint32 PsychicSerial() const {return Psychic.Serial;}
    bool IsJumpSlamming() const {return JumpSlam.Phase!=EHeQueJumpPhase::None&&!Dead()&&!Controlled();}
    EHeQueJumpPhase JumpPhase() const {return JumpSlam.Phase;}
    uint32 JumpSerial() const {return JumpSlam.Serial;}
    float JumpAge() const;
    UAnimSequence* JumpClip(float& Seconds) const;
    void SetLocomotion(bool Moving,bool Returning);
    void InterruptAttack(float Seconds);
    void FinishHitReaction();
    void ExtendControl(float Seconds);
    bool StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds);
    EHeQueReaction ReactionPhase() const {return Reaction.Phase;}
    uint32 ReactionSerial() const {return Reaction.Serial;}
    float ReactionAge() const;
    double ActionClock() const;
    UAnimSequence* ReactionClip(float& Seconds,bool& Loop) const;
    bool SamplingDeathHandoff() const {return Reaction.Phase==EHeQueReaction::Dying&&Reaction.DeathLead>0.f&&ReactionAge()>=Reaction.DeathLead;}
    UFUNCTION(BlueprintCallable,Category="HeQue|Authoring") static UPhysicsAsset* BuildHitSurfacePhysics(USkeletalMesh* InMesh,const FString& AssetPath);
private:
    enum class EAttackChoice : uint8 { None, Kick, Clamp, Jump, Rift, Psychic };
    EAttackChoice ChooseAttack(APawn* Victim) const;
    bool StartSweep(APawn* Victim);
    uint8 NextCloseAttack=0;
    bool bPreferPsychicNext=true;
    bool CanJumpSlam(APawn* Victim) const;
    float JumpClearanceHeight() const;
    bool StartJumpSlam(APawn* Victim);
    void SetJumpPhase(EHeQueJumpPhase Phase);
    void CancelJumpSlam();
    void LandJumpSlam(const FHitResult& Hit);
    void TickJumpSlam();
    void ApplyJumpWave(float Radius,bool bImpact);
    void PresentJumpSlam(float Age);
    UPROPERTY(ReplicatedUsing=OnRep_JumpSlam) FHeQueJumpState JumpSlam;
    UFUNCTION() void OnRep_JumpSlam();
    UPROPERTY() TObjectPtr<UStaticMeshComponent> JumpWave;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> JumpImpact;
    UPROPERTY() TObjectPtr<UAudioComponent> JumpVoice;
    UPROPERTY() TObjectPtr<UAudioComponent> JumpImpactVoice;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> JumpWaveMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> JumpImpactMID;
    TSet<TWeakObjectPtr<AActor>> JumpVictims;
    double NextJumpAt=0.;
    float JumpPreviousRadius=0.f;
    uint32 PresentedJumpSerial=0;
    bool bJumpWaveFinished=false;
    bool CanPsychic(APawn* Victim) const;
    bool StartPsychic(APawn* Victim);
    void CancelPsychic();
    void TickPsychic();
    void PresentPsychic(float Age);
    void AdvancePsychic(int32 Index,float Age);
    FVector PsychicCore() const;
    UPROPERTY(ReplicatedUsing=OnRep_Psychic) FHeQuePsychicState Psychic;
    UFUNCTION() void OnRep_Psychic();
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PsychicWaves;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PsychicWaveMIDs;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PsychicCoreMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> PreviousPsychicOverlay;
    UPROPERTY() TObjectPtr<UAudioComponent> PsychicVoice;
    TSet<TWeakObjectPtr<AActor>> PsychicVictims[3];
    TSet<TWeakObjectPtr<AActor>> PsychicFeared;
    double NextPsychicAt=0.;
    float PsychicTravel[3]={-1.f,-1.f,-1.f};
    uint32 PresentedPsychicSerial=0;
    void ApplyRig();
    void RefreshPoseTick();
    void SetReaction(EHeQueReaction Phase);
    void TickReaction(float Dt);
    void BeginDeath();
    void PresentDeath();
    void TickSweep();
    bool CanSweep(APawn* Victim) const;
    bool SweepBlocked() const;
    bool HasSweepSight(const APawn* Victim) const;
    FVector SweepPointWorld(const FVector& Point) const;
    void SweepContact(int32 Index);
    void MeleeContact(const TArray<FHeQueSweepFrame>& Frames,int32 Index,float Radius,float Damage,float PushDistance,
        TSet<TWeakObjectPtr<AActor>>& Victims,bool bClamp);
    bool CanClamp(APawn* Victim) const;
    bool StartClamp(APawn* Victim);
    void CancelClamp();
    void TickClamp();
    UPROPERTY(ReplicatedUsing=OnRep_Clamp) FHeQueSweepState Clamp;
    UFUNCTION() void OnRep_Clamp();
    UPROPERTY() TObjectPtr<UAudioComponent> ClampVoice;
    TSet<TWeakObjectPtr<AActor>> ClampVictims;
    double NextClampAt=0.;
    int32 NextClampFrame=1;
    uint32 PresentedClampSerial=0;
    FVector RiftMouth() const;
    bool HasRiftSight(const APawn* Victim) const;
    bool CanRift(APawn* Victim) const;
    bool StartRift(APawn* Victim);
    void CancelRift();
    void TickRift();
    void PresentRift(float Age);
    void PresentPressureDust(int32 Index,float Age,const FVector& Position,bool Flying);
    void AdvancePressure(int32 Index,float Age);
    UPROPERTY(ReplicatedUsing=OnRep_Rift) FHeQueRiftState Rift;
    UFUNCTION() void OnRep_Rift();
    UPROPERTY() TObjectPtr<UStaticMeshComponent> PressureMembrane;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureWaves;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> PressureIntake;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureMuzzles;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureTrails;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureImpacts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureDust;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MembraneMID;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PressureMIDs;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> IntakeMID;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> MuzzleMIDs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> TrailMIDs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> ImpactMIDs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> DustMIDs;
    UPROPERTY() TObjectPtr<UAudioComponent> RiftVoice;
    UPROPERTY() TArray<TObjectPtr<UAudioComponent>> RiftImpactVoices;
    double NextRiftAt=0.;
    bool bRiftRecoveryFinished=false;
    float PressureTravel[2]={0.f,0.f};
    uint32 PresentedRiftSerial=0;
    bool ImpactSoundPlayed[2]={false,false};
    float NextDustProbe[2]={0.f,0.f};
    float DustTouchedAt[2]={-100.f,-100.f};
    FVector DustPoint[2]={FVector::ZeroVector,FVector::ZeroVector};
    FVector DustNormal[2]={FVector::UpVector,FVector::UpVector};
    UPROPERTY(ReplicatedUsing=OnRep_Sweep) FHeQueSweepState Sweep;
    UFUNCTION() void OnRep_Sweep();
    UPROPERTY() TObjectPtr<UAudioComponent> SweepVoice;
    uint32 PresentedSweepSerial=0;
    TWeakObjectPtr<APawn> CombatTarget;
    TSet<TWeakObjectPtr<AActor>> SweepVictims;
    double NextSweepAt=0.;
    int32 NextSweepFrame=0;
    UPROPERTY(ReplicatedUsing=OnRep_Reaction) FHeQueReactionState Reaction;
    UFUNCTION() void OnRep_Reaction();
    double ControlUntil=0.;
    uint8 LastHitDirection=0;
    bool bDeathPrepared=false,bDeathHandoff=false,bDeathFallback=false;
};
