#pragma once

#include "CoreMinimal.h"
#include "VillageSiegeEngine.h"
#include "VillageLightningSpire.generated.h"

class UPointLightComponent;
class UNiagaraSystem;
class USoundBase;
struct FStreamableHandle;

/** Rune Lightning Spire: roof-mounted tower defense with chain AFPSLightningArc, stun interrupt, 感电 & manual aim. */
UCLASS()
class FPSGAME_API AVillageLightningSpire final : public AVillageSiegeEngine
{
    GENERATED_BODY()
    friend class FVillageLightningSpireTest;
public:
    AVillageLightningSpire();
    static FSoftObjectPath MeshAsset(const TCHAR* Suffix);
    virtual bool IsLightningSpire() const override { return true; }
    virtual bool UsesCrosshair() const override { return true; }
    virtual const TCHAR* DisplayName() const override { return TEXT("符文引雷塔"); }
    virtual const TCHAR* ReloadActionName() const override { return TEXT("引雷塔充能"); }
    virtual double Range() const override;
    virtual double BlastRadius() const override { return 320.; }
    virtual double MinimumRange() const override { return 0.; }
    virtual FRotator ClaimedAim() const override;
    virtual bool Claim(APawn* Pawn) override;
    virtual void ManualSight(const APawn* Pawn,float Yaw,float Elevation,FVillageSiegeSight& Sight,bool Preview) const override;
    virtual void ComputeManualCamera(float Yaw,float Elevation,double CachedGroundZ,FVector& OutLocation,FRotator& OutRotation,FRotator& OutFacing) const override;
    virtual void SetManualBearing(APawn* Pawn,const FRotator& Bearing) override;
    virtual void FireManual(APawn* Pawn,float Yaw,float Elevation) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
    virtual void OnRep_Setup() override;
    virtual void OnRep_Shot() override;
    virtual void ApplyHealth() override;
    virtual void Pose(double Elapsed) override;
    virtual double Duration() const override;
    virtual double ReleaseAt() const override;
    virtual double AnimationTime(double Elapsed) const override { return Elapsed; }
    virtual void FindTarget() override;
    virtual void Release() override;
    virtual void SetUpSiegeAudio() override {}
    virtual void UpdateSiegeAudio(double Elapsed) override {}
private:
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Mast;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Crystal;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Rings;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> CrownLight;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ChainArcAsset;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> CastSounds;
    TSharedPtr<FStreamableHandle> FXHandle;
    mutable TWeakObjectPtr<AActor> SupportStructure;
    mutable bool bSupportSampled = false;
    double LastFlashStart = -100.;
    float LastChargePower = -1.f;
    float CrystalYaw = 0.f;
    FRotator RingRot = FRotator::ZeroRotator;
    void EnsureFXAssets();
    void ApplyVisualPower(float Power,float LightLumens,float LightRadius);
    FVector CrownWorldOrigin() const;
    AActor* FindSupportingStructure() const;
    bool InSpireRange(const FVector& Crown,const FVector& TargetPt,double MaxRange) const;
    bool HasSpireLineOfSight(const FVector& Crown,const FVector& TargetPt,const AActor* Target,const AActor* Carrier,FVector& OutKnee,bool& bOutBent) const;
    void TriggerOverload(AActor* Origin,float SplashDamage,APawn* InstigatorPawn,AController* InstigatorCtrl,TSet<AActor*>& Overloaded,int32 Depth);
    UFUNCTION(NetMulticast,Unreliable) void MulticastDischargeFX(FVector_NetQuantize Origin,FVector_NetQuantize Impact);
};
