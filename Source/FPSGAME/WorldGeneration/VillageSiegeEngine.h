#pragma once

#include "CoreMinimal.h"
#include "VillageDefenseSection.h"
#include "VillageSiegeUpgrades.h"
#include "VillageSiegeEngine.generated.h"

class USphereComponent;
class UAudioComponent;
class USoundWave;
class UProjectileMovementComponent;

USTRUCT()
struct FVillageSiegeShot
{
    GENERATED_BODY()
    UPROPERTY() uint64 UpgradeRanks=0;
    UPROPERTY() double Started = -1.;
    UPROPERTY() bool bReleased = false;
    UPROPERTY() float Yaw = 0.f;
    UPROPERTY() float Pitch = 0.f;
    UPROPERTY() FRotator TraverseFrom = FRotator::ZeroRotator;
    UPROPERTY() FVector_NetQuantize Aim = FVector::ZeroVector;
};

struct FVillageSiegeSight
{
    FVector Camera = FVector::ZeroVector;
    FRotator View = FRotator::ZeroRotator;
    FVillageSiegeShot Plan;
    TArray<FVector> Arc;
    FVector Impact = FVector::ZeroVector;
    FVector ImpactNormal = FVector::UpVector;
    bool bHitUnit = false;
    bool HasImpact = false;
    bool CanFire = false;
};

/** Fixed village engine. Only the authority chooses targets and creates missiles. */
UCLASS()
class FPSGAME_API AVillageSiegeEngine : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    AVillageSiegeEngine();
    static FSoftObjectPath MeshAsset(const TCHAR* Suffix);
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    bool IsTrebuchet() const { return bStone; }
    virtual bool IsLightningSpire() const { return false; }
    virtual bool UsesCrosshair() const { return !bStone; }
    virtual const TCHAR* DisplayName() const { return bStone?TEXT("配重投石机"):TEXT("固定式弩炮"); }
    virtual const TCHAR* ReloadActionName() const { return bStone?TEXT("投石机装填"):TEXT("弩炮装填"); }
    bool IsOccupied() const { return IsValid(OperatorPawn); }
    bool IsOperatedBy(const APawn* Pawn) const { return Pawn && OperatorPawn==Pawn; }
    float LastShotYaw() const { return Shot.Yaw; }
    virtual FRotator ClaimedAim() const;
    bool CanOperate() const;
    virtual bool Claim(APawn* Pawn);
    virtual void Vacate(APawn* Pawn);
    virtual double ReloadRemaining() const;
    virtual bool GetReloadProgress(float& Fraction) const;
    virtual double Range() const;
    virtual double BlastRadius() const;
    bool HasTrebuchetHotOil() const { return bStone && VillageSiegeUpgrades::HasTrebuchetHotOil(CurrentAllRanks()); }
    bool IsNextShotHotOil() const { return HasTrebuchetHotOil() && HotOilShotCounter>=3; }
    int32 HotOilChargeCount() const { return HotOilShotCounter; }
    virtual double MinimumRange() const { return bStone?1650.:340.; }
    double ResolveAimYaw(double Degrees) const
    {
        return FRotator::NormalizeAxis(Degrees);
    }
    virtual void ManualSight(const APawn* Pawn,float Yaw,float Elevation,FVillageSiegeSight& Sight,bool Preview) const;
    virtual void ComputeManualCamera(float Yaw,float Elevation,double CachedGroundZ,FVector& OutLocation,FRotator& OutRotation,FRotator& OutFacing) const;
    virtual void DisplaySight(const FVillageSiegeShot* Plan);
    virtual void SetManualBearing(APawn* Pawn,const FRotator& Bearing);
    virtual void FireManual(APawn* Pawn,float Yaw,float Elevation);
    virtual bool BlocksPassage() const override { return false; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnRep_Setup() override;
    virtual void ApplyHealth() override;
    virtual void PresentCollapse(const FVector& Direction,int32 NoiseSeed,float Travel) override;
    // Local to the carriage. These transforms also exist on a headless server.
    TMap<FName,FTransform> UsePartPoses;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Carriage;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY(ReplicatedUsing=OnRep_Shot) FVillageSiegeShot Shot;
    UFUNCTION() virtual void OnRep_Shot();
    UPROPERTY(ReplicatedUsing=OnRep_Shot) TObjectPtr<APawn> OperatorPawn;
    UPROPERTY(ReplicatedUsing=OnRep_Shot) FRotator ManualBearing=FRotator::ZeroRotator;
    UPROPERTY(Replicated) uint8 HotOilShotCounter=0;
    TOptional<FRotator> LocalSightBearing;
    bool bManualShot = false;
    FTimerHandle SearchTimer;
    FTimerHandle ReleaseTimer;
    TWeakObjectPtr<APawn> Tracked;
    uint64 CurrentRanks() const;
    VillageSiegeUpgrades::FRanks CurrentAllRanks() const;
    double Clock() const;
    virtual double AnimationTime(double Elapsed) const;
    virtual double Duration() const;
    virtual double ReleaseAt() const;
    virtual void FindTarget();
    virtual void Release();
    virtual void Pose(double Elapsed);
    virtual void SetUpSiegeAudio();
    virtual void UpdateSiegeAudio(double Elapsed);
    void StartShot(FVillageSiegeShot Plan,APawn* Target,bool Manual);
    void CancelWindup();
    static bool IsThreatUnit(AActor* Actor,AActor* Engine);
    static const TArray<TWeakObjectPtr<APawn>>& CachedThreatPawns(UWorld* World);
private:
#if WITH_DEV_AUTOMATION_TESTS
    friend class FVillageSiegePreviewTest;
    friend class FVillageTrebuchetHotOilTest;
#endif
    friend class UVillageSiegeUseTargets;
    friend class AVillageSmartTurret;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> TensionAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> ReleaseAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> ReloadAudio;
    enum class ESiegeSoundPhase : uint8 { Tension, Release, Reload, Done };
    ESiegeSoundPhase NextSound=ESiegeSoundPhase::Tension;
    double AudioShotStart=-1.;
    TSharedPtr<FStreamableHandle> StoneImpactFXHandle;
    bool MakePlan(const FVector& Point,FVillageSiegeShot& Plan) const;
    bool bStone = false;
    void AddPart(const TCHAR* Key, const TCHAR* Suffix);
    FVector ReleaseOrigin(const FVillageSiegeShot& Plan) const;
};

UCLASS()
class FPSGAME_API AVillageSiegeMissile : public AActor
{
    GENERATED_BODY()
public:
    static constexpr float StoneImpactRadius = 500.f;
    static constexpr float StoneBodyRadius = 16.f;
    AVillageSiegeMissile();
    virtual void Tick(float DeltaSeconds) override;
    void Launch(bool bStoneShot, const FVector& InitialVelocity,uint64 Ranks=0,bool bHotOil=false);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void BeginPlay() override;
private:
#if WITH_DEV_AUTOMATION_TESTS
    friend class FVillageTrebuchetHotOilTest;
#endif
    UPROPERTY() TObjectPtr<USphereComponent> Body;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Model;
    UPROPERTY() TObjectPtr<UProjectileMovementComponent> Movement;
    uint64 UpgradeRanks=0;
    UPROPERTY(Replicated) bool bHotOilPayload=false;
    UPROPERTY(ReplicatedUsing=OnRep_Model) bool bStone = false;
    UPROPERTY(Replicated) FVector_NetQuantize10 FlightOrigin = FVector::ZeroVector;
    UPROPERTY(Replicated) FVector_NetQuantize10 FlightVelocity = FVector::ZeroVector;
    UPROPERTY(Replicated) double FlightStart = -1.;
    UFUNCTION() void OnRep_Model();
    UPROPERTY(Transient) TObjectPtr<USoundWave> StoneImpactSound;
    UFUNCTION() void Impact(const FHitResult& Hit);
    UFUNCTION(NetMulticast, Reliable) void PlayStoneImpact(FVector_NetQuantize HitPoint, FVector_NetQuantize SurfacePoint, FVector_NetQuantizeNormal SurfaceNormal, bool bSurfaceHit, float EffectRadius);
};
