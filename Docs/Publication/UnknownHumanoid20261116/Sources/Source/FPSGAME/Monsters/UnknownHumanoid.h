#pragma once

#include "CoreMinimal.h"
#include "AITypes.h"
#include "GameFramework/Character.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "../Characters/FPSBodyGunAimTypes.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Skills/FireballTypes.h"
#include "UnknownHumanoid.generated.h"

class AMonsterAIController;
struct FUnknownSpellbook;
struct FUnknownArchery;
struct FColdSteelSkillShot;
enum class EUnknownPosition : uint8 { Open, SeekCover, Sheltered, MoveToPeek, Peeking, Adjust };
class UColdSteelStatusModel;
class UMonsterCombatComponent;
class UCombatStatusFormula;
class UFPSModularOutfitComponent;
class UFPSBallisticsComponent;
class UFPSWeaponFXComponent;
class UFPSFireballComponent;
class UPoseableMeshComponent;
class USoundBase;
struct FMonsterCoreStats;
struct FColdSteelItem;
struct FStreamableHandle;

UENUM()
enum class EUnknownRole : uint8 { Melee, Gun, Magic, Bow };

USTRUCT()
struct FUnknownLoadout
{
    GENERATED_BODY()
    UPROPERTY() EUnknownRole Role = EUnknownRole::Melee;
    UPROPERTY() int32 Level = 10;
    UPROPERTY() FName Body;
    UPROPERTY() FString Weapon;
    UPROPERTY() FString Offhand;
    UPROPERTY() FString BackupBlade;
    UPROPERTY() TArray<FFPSBodyOutfitSlot> Outfit;
};

UENUM()
enum class EUnknownAction : uint8 { Ready, Swing, Fire, Reload, Cast, Stagger, Dead, DrawBow, SwapWeapon };

USTRUCT()
struct FUnknownMotion
{
    GENERATED_BODY()
    UPROPERTY() EUnknownAction Action = EUnknownAction::Ready;
    UPROPERTY() float Started = 0.f;
    UPROPERTY() float Duration = 0.f;
    UPROPERTY() uint16 Serial = 0;
    UPROPERTY() float Windup = 0.f;
    // Fixed phase boundaries survive a sustained spell extending Duration.
    UPROPERTY() float Preparation = 0.f;
    UPROPERTY() float Recovery = 0.f;
    UPROPERTY() FName Skill;
    UPROPERTY() uint8 ArrowKind = 0;
};

/** A hostile character with its own player-equipment sheet. Only the authority rolls the loadout. */
UCLASS()
class FPSGAME_API AUnknownHumanoid : public ACharacter
{
    GENERATED_BODY()
public:
    AUnknownHumanoid();
    bool Configure(EUnknownRole InRole, int32 Level);
    bool CanAttack(APawn* Target) const;
    bool StartAttack(APawn* Target);
    void Pursue(AMonsterAIController& AI, APawn* Visible, FVector LastKnown);
    APawn* ConsiderVisibleOpponent(AMonsterAIController& AI, APawn* Current, bool bVisible, bool bMaySwitch);
    void UpdateTactics(APawn* Target, bool bVisible, FVector LastKnown);
    bool CanActOutOfSight() const;
    bool FollowingRangedPlan() const { return IsRanged() && (Position!=EUnknownPosition::Open || BypassUntil>0.); }
    void Interrupt(float Duration);
    void FireballImpact(const FVector& Center, const FFireballCast& Cast, const FHitResult* Direct);
    float HitWithRound(const FHitResult& Hit, float Damage, FVector Direction, float CriticalRoll);
    float HitWithArrow(const FHitResult& Hit,float Damage,FVector Direction,const FColdSteelSkillShot& Shot);
    void CoreStats(FMonsterCoreStats& Out) const;
    bool Dead() const { return Motion.Action == EUnknownAction::Dead; }
    bool Busy() const { return Motion.Action != EUnknownAction::Ready; }
    bool Controlled() const;
    void SetTravelIntent(bool Moving,bool Returning) { if (!Moving || Returning) bSprintIntent=Moving && Returning; }
    float WeaponMagicFraction() const { return WeaponDamage.Total()>0 ? (WeaponDamage.BaseMagic+WeaponDamage.AddedMagic)/WeaponDamage.Total() : 0.f; }
    float Penetration(bool Magic) const { return Magic ? (Loadout.Role==EUnknownRole::Magic ? Spell.MagicPenetration : MagicPenetration) : PhysicalPenetration; }
    UColdSteelStatusModel* EquipmentModel() const;
    bool IsRanged() const { return Loadout.Role==EUnknownRole::Magic || Loadout.Role==EUnknownRole::Gun || (Loadout.Role==EUnknownRole::Bow && !bBowBlades); }
    bool CanPursueDuringSwing(const APawn* VisibleTarget) const;
    bool UsesMobileGunCombat() const { return Loadout.Role==EUnknownRole::Gun; }
    bool UsesMobileCombatTask() const { return IsRanged() || Loadout.Role==EUnknownRole::Bow; }
    bool CanPursueDuringAction(const APawn* Target,bool bVisible) const;
    float StopRange() const { return PreferredRange; }
    FVector Home = FVector::ZeroVector;
    UPROPERTY(Replicated) float Health = 1.f;
    UPROPERTY(Replicated) float MaxHealth = 1.f;

    virtual float TakeDamage(float Amount, const FDamageEvent& Event, AController* InstigatorController, AActor* Causer) override;
    virtual void Tick(float Delta) override;
    virtual void FaceRotation(FRotator NewControlRotation, float DeltaTime = 0.f) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Loadout) FUnknownLoadout Loadout;
    UPROPERTY(ReplicatedUsing=OnRep_Motion) FUnknownMotion Motion;
    UPROPERTY(Replicated) FVector_NetQuantize GunAimPoint;
    UPROPERTY(Replicated) bool bGunTracking=false;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Sheet;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> BowSheet;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> BladeSheet;
    UPROPERTY(ReplicatedUsing=OnRep_BowMode) bool bBowBlades=false;
    UFUNCTION() void OnRep_BowMode();
    TSharedPtr<FUnknownArchery> Archery;
    void PrepareArchery();
    void CacheBowStats();
    bool StartBowAttack(APawn* Target);
    void ReleaseBowAttack(APawn* Target);
    void UpdateBowTactics(APawn* Target,bool bVisible);
    bool PursueBowRetreat(AMonsterAIController& AI,APawn* Target);
    void UpdateBowPresentation();
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> BackupRight;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> BackupLeft;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> NockedArrow;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> BowStrings[2];
    UPROPERTY(Transient) TObjectPtr<class UBowFlexMeshComponent> BowFlex;
    UPROPERTY(Transient) TObjectPtr<class UElementalArrowVisual> HeldArrowElement;
    UPROPERTY(Transient) TObjectPtr<class UIlluminationArrowVisual> HeldArrowLight;
    FVector BowTips[2],BowBrace;
    float BowScale=1.f,BowStringRadius=.09f,BowFlexDistribution=1.15f;
    FTransform ArrowFromNock=FTransform::Identity;
    FDelegateHandle BowPoseFinalized;
    UPROPERTY(Transient) TSoftObjectPtr<USoundBase> BowReleaseSound;
    UFUNCTION(NetMulticast,Unreliable) void MulticastBowRelease();
    UPROPERTY() TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY() TObjectPtr<UCombatStatusFormula> Status;
    UPROPERTY() TObjectPtr<UFPSModularOutfitComponent> Clothing;
    UPROPERTY() TObjectPtr<UFPSBallisticsComponent> Ballistics;
    UPROPERTY(Transient) TObjectPtr<UFPSWeaponFXComponent> GunTracers;
    UPROPERTY() TObjectPtr<UFPSFireballComponent> Fireball;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> HeldWeapon;
    UPROPERTY(Transient) TObjectPtr<UPoseableMeshComponent> HeldGun;
    UPROPERTY(Transient) TSoftObjectPtr<USoundBase> FireSound;
    UPROPERTY(Transient) TSoftObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TSoftObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<class USoundAttenuation> ShotAttenuation;
    UPROPERTY(Transient) TObjectPtr<class USoundAttenuation> MeleeAttenuation;
    TSharedPtr<FStreamableHandle> WeaponAudioLoad;
    UPROPERTY(Transient) TObjectPtr<class UNiagaraSystem> MuzzleFlash;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Clips;
    TArray<TPair<int32,FQuat>> ImplementFingers;
    TSharedPtr<FStreamableHandle> AppearanceLoad;
    TWeakObjectPtr<APawn> AttackTarget;
    FWeaponDamageParts WeaponDamage;
    FFireballCast Spell;
    FName WeaponType;
    float WalkSpeed = 0, RunSpeed = 0, AimWalkSpeed = 0, Stamina = 0, MaxStamina = 0, StaminaCost = 0;
    float RecoveryRate = 0, SprintDrain = 0, ResourceDelay = 0;
    float HealthRegen = 0;
    float AttackRange = 180, PreferredRange = 115, AttackSeconds = 1, ReloadSeconds = 1;
    float MeleeContactFraction = .4f, MeleeSecondContact = 0.f, HammerBaseContact = 0.f;
    FTransform MeleeSupportGrip = FTransform::Identity;
    bool bHasMeleeSupport = false;
    float BurstRecovery = 0, PhysicalPenetration = 0, MagicPenetration = 0;
    float BulletSpeed = 0, EffectiveRange = 0, PelletCone = 0, AimSeconds = .25f;
    int32 ShotAccuracyPercent = 33;
    int32 Pellets = 1, Magazine = 0, Capacity = 0, BurstSize = 1, ShotsLeft = 0;
    float CriticalChance = 0, CriticalBonus = 0, WeakpointPercent = 0;
    UPROPERTY(Replicated) int32 Defense = 0;
    UPROPERTY(Replicated) int32 MagicDefense = 0;
    UPROPERTY(Replicated) int32 CritResistance = 0;
    UPROPERTY(Replicated) double AttributeWeight = 0;
    double NextAttack = 0, ContactAt = 0, NextReposition = 0;
    bool bPendingContact = false, bSprintIntent = false, bExhausted = false;
    bool bVisualReady = false;
    friend struct FUnknownHumanoidAnimProxy;
    friend class FUnknownCombatDecisionTest;
    friend class FUnknownObstacleTravelTest;
    friend class UUnknownGunRosterAuditCommandlet;
    friend class UMonsterDamageAuditCommandlet;
    friend struct FUnknownNetworkAuditAccess;
    friend struct FUnknownJoinAuditAccess;
    friend struct FUnknownLifeAuditAccess;
    bool EquipLoadout(UColdSteelStatusModel& Catalog,const class UColdSteelEnhancementSystem& Rules,
        EUnknownRole Role,int32 Level,FName Body,const FString& WeaponId);
    struct FSighting
    {
        TWeakObjectPtr<APawn> Pawn;
        FVector Feet;
        FVector Eye;
    };
    TArray<FSighting,TInlineAllocator<4>> OtherOpponents;
    double NextSightSample=0, NextTargetSwitch=0, LastSeenTime=-100;
    double FiringLaneLostSince=-1;
    bool bTacticalTargetVisible=false;
    FVector LastSeenDirection=FVector::ForwardVector, SearchPoint=FVector::ZeroVector;
    double NextSearchStep=0;
    uint8 SearchSteps=0;
    bool bSearchingPoint=false;
    bool PursueLastSighting(AMonsterAIController& AI,FVector LastKnown);
    FVector FailedCover=FVector::ZeroVector;
    struct FBlockedTravelSite { FVector Point; double Until; };
    TArray<FBlockedTravelSite,TInlineAllocator<4>> BlockedTravelSites;
    void RememberBlockedTravel(FVector Point);
    bool ShouldAvoidTravelPoint(FVector Point) const;
    FVector TravelSample=FVector::ZeroVector, BypassPoint=FVector::ZeroVector;
    FVector TravelGoal=FVector::ZeroVector, FailedBypass=FVector::ZeroVector;
    double AvoidBypassUntil=0., BlockedApproachUntil=0.;
    float RemainingTravel=MAX_flt;
    uint8 BypassAttempts=0;
    double NextRouteSample=0.;
    double LastTravelSample=-100., LastTravelCall=-100., BypassUntil=0., RetryTravelAt=0.;
    bool bHasFiringLane=false;
    bool bRetreating=false;
    bool bLastTravelWasTactical=false;
    bool bCrowdReposition=false;
    double NextCrowdCheck=0, CrowdYieldUntil=0, CrowdWaitUntil=0, CrowdMoveUntil=0, CrowdBlockedSince=-1;
    double CrowdSpeedUntil=0;
    float CrowdSpeedLimit=MAX_flt;
    FVector CrowdYieldPoint=FVector::ZeroVector, CrowdMoveDirection=FVector::ZeroVector;
    TWeakObjectPtr<AUnknownHumanoid> CrowdPasser, CrowdBlocker;
    FAIRequestID CrowdPausedRequest=FAIRequestID::InvalidRequest;
    void GatherCrowd(FVector Center,float Radius,TArray<AUnknownHumanoid*>& Out) const;
    float CrowdSpaceCost(FVector Point,const TArray<AUnknownHumanoid*>& Allies) const;
    bool CanYieldToCrowd() const;
    bool FindCrowdYield(AUnknownHumanoid& Passer,FVector Direction,FVector& Point);
    bool HandleCrowdTraffic(AMonsterAIController& AI,FVector Goal,bool bTravel);
    void HoldForCrowd(AMonsterAIController& AI);
    double AvoidCoverUntil=0;
    float TacticalReloadSeconds=1.f;
    bool WantsReload() const;
    bool UnderPressure() const;
    bool HasVisibleCluster(const APawn* Focus, float Radius) const;
    void LeaveCover(bool bAvoid);
    bool HasFiringLane(FVector Origin,const APawn& Target,FVector Aim) const;
    void MoveRanged(AMonsterAIController& AI,FVector Goal,float Acceptance,bool bTactical);
    bool FindBypass(AMonsterAIController& AI,FVector Goal,FVector Forward);
    EUnknownPosition Position = EUnknownPosition::Open;
    FVector CoverPoint = FVector::ZeroVector, FiringPoint = FVector::ZeroVector, PlannedTarget = FVector::ZeroVector;
    TWeakObjectPtr<APawn> TacticalTarget;
    bool bCombatFacing = false;
    float CombatAimPitch = 0.f;
    void UpdateCombatFocus(APawn* Target, bool bVisible, FVector LastKnown);
    bool FacingTarget(const APawn& Target) const;
    double PositionUntil = 0, LastIncomingHit = -100;
    bool bHasCover = false;
    bool FindFiringPosition(APawn* Target, FVector LastKnown, bool bVisible);
    TSharedPtr<FUnknownSpellbook> Spellbook;
    void PrepareMagic();
    void SelectMagic(float Distance, bool bVisible);
    bool HasChosenMagic() const;
    FName ChosenMagicId() const;
    void StartMagicAttack();
    void CancelRangedAction();
    bool ReleaseMagic(APawn* Target, FVector Aim);
    bool SelfCast() const;
    void CacheStats();
    void UpdateResources(float Delta);
    void SetAction(EUnknownAction Action, float Duration = 0);
    void ReleaseAttack();
    float RollDamage(APawn* Victim, float Damage, float Roll, bool Weak, float Bonus) const;
    FVector AimOrigin() const;
    FVector MeleeDirection(const APawn& Target) const;
    float MeleeWindup() const;
    bool InMeleeStartRange(const APawn& Target) const;
    float ServerTime() const;
    UFUNCTION() void OnRep_Loadout();
    UFUNCTION() void OnRep_Motion();
    FVector GunMuzzle(const FVector& LaunchStart) const;
    FVector TracerMuzzle(const FVector& LaunchStart,const FVector& SocketLocation) const;
    UFPSWeaponFXComponent* GetOrCreateGunTracers();
    UFUNCTION(NetMulticast,Unreliable) void MulticastShot(FVector_NetQuantize Start, FVector_NetQuantizeNormal Direction,
        float FlightSpeed,float RangeCM,APawn* MissedTarget);
    UFUNCTION(NetMulticast,Unreliable) void MulticastMeleeSound(bool bImpact, FVector_NetQuantize Location);
    UFUNCTION(NetMulticast,Unreliable) void MulticastMagicReleaseSound(FName Skill,FVector_NetQuantize Location);
    void PrepareWeaponAudio(const FColdSteelItem& Item);
    void UpdateGunRecoil();
    FTransform GunMount = FTransform::Identity;
    FFPSBodyGunAimFrame GunAimFrame;
    FTransform GunMuzzleInMesh=FTransform::Identity,GunSupportGrip=FTransform::Identity;
    bool bHasGunSupport=false;
    float LastShotTime = -10.f;
};
