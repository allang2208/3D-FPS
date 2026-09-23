#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/EngineTypes.h"
#include "WeaponBipodDeploymentComponent.generated.h"

class AFPSGAMECharacter;
class UPKMBipodComponent;
class UPrimitiveComponent;
struct FWeaponHandling;

UENUM(BlueprintType)
enum class EWeaponBipodDeploymentState : uint8
{
    Unavailable, Available, Deploying, Deployed, Releasing
};

/** Local single-player mounting controller. Geometry/contact presentation is
 * supplied by the equipped bipod; the supporting world object is never moved. */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UWeaponBipodDeploymentComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeaponBipodDeploymentComponent();
    // Called on entry to ADS, not continuously while the aim input is held.
    UFUNCTION(BlueprintCallable, Category="Weapon|Bipod") bool TryDeployFromADS();
    UFUNCTION(BlueprintCallable, Category="Weapon|Bipod") void Release(bool bImmediate=false);
    UFUNCTION(BlueprintPure, Category="Weapon|Bipod") EWeaponBipodDeploymentState GetDeploymentState() const;
    UFUNCTION(BlueprintPure, Category="Weapon|Bipod") bool IsDeployed() const { return bRequested && Blend>=.999f; }
    UFUNCTION(BlueprintPure, Category="Weapon|Bipod") float GetDeploymentBlend() const { return Blend; }
    FString GetHint() const;
    float RecoilMultiplier() const { return FMath::Lerp(1.f,MountedRecoilScale,Blend); }
    float SpreadMultiplier() const { return FMath::Lerp(1.f,MountedSpreadScale,Blend); }
    float MotionMultiplier() const { return FMath::Lerp(1.f,.16f,Blend); }
    FWeaponHandling ApplyStability(const FWeaponHandling& Base) const;
    bool BlocksFire() const { return bRequested && Blend<.999f; }
    // 架枪锁定：部署请求或解除过渡期间移动/跳跃/冲刺/滑铲输入被忽略（非解除）。
    bool BlocksMovement() const { return bRequested || Blend>UE_SMALL_NUMBER; }

    // Called in character order: before camera, before firing, then after pose.
    void Advance(float DeltaSeconds);
    void RestoreCameraOffset();
    void ApplyPresentation(bool bAfterPose=false);
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* Tick) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
public:
    // 2026-09-23 用户要求放宽架设条件：高度/前后窗口、坡面与相机校正上限整体放宽。
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Placement", meta=(ClampMin="1")) float MaximumHeightSnap=30.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Placement", meta=(ClampMin="0")) float ForwardSearch=20.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Placement", meta=(ClampMin="0",ClampMax="45")) float MaximumSlopeDegrees=24.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Placement", meta=(ClampMin="1")) float MaximumCameraReach=60.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Placement") TEnumAsByte<ECollisionChannel> SupportChannel=ECC_Visibility;
    // 2026-09-23 用户要求：架枪视域窗翻倍为偏航±30°、俯仰±12°；镜头仍不允许移出。
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Aim", meta=(ClampMin="1",ClampMax="45")) float YawLimitDegrees=30.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Aim", meta=(ClampMin="1",ClampMax="20")) float PitchLimitDegrees=12.f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Handling", meta=(ClampMin="0.1",ClampMax="1")) float MountedRecoilScale=.34f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Handling", meta=(ClampMin="1")) float MountedStabilityMultiplier=1.66f;
    UPROPERTY(EditAnywhere, Category="Weapon|Bipod|Handling", meta=(ClampMin="0.1",ClampMax="1")) float MountedSpreadScale=.55f;
private:
    struct FSupport
    {
        FVector Feet[2]={FVector::ZeroVector,FVector::ZeroVector};
        FVector Anchor=FVector::ZeroVector;
        TWeakObjectPtr<UPrimitiveComponent> Components[2];
        FTransform Transforms[2];
    };
    bool Eligible() const;
    UPKMBipodComponent* EquippedBipod() const;
    // Coarse HUD hint only. ADS entry always performs FindSupport in full.
    bool HasSupportHint(UPKMBipodComponent& Part) const;
    bool FindSupport(UPKMBipodComponent& Part,FSupport& Out) const;
    bool SupportStillValid(bool bProbeSurface) const;
    bool ClearPlacement(const FVector& Eye,const FVector& Delta,const FVector& Hinge,const FVector& Forward,
        bool bCheckWeapon=true) const;
    void ClampAim() const;
    // 架设两拍反馈：起手播 BeltLift，落位播 BeltSeat 并起枪身衰减抖。
    void FireDeployCue(bool bSeat);
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    TWeakObjectPtr<UPKMBipodComponent> Bipod;
    FSupport Support;
    FVector AppliedCameraOffset=FVector::ZeroVector;
    FVector PawnAnchor=FVector::ZeroVector;
    FRotator InitialAim=FRotator::ZeroRotator;
    float Blend=0.f;
    float SettleClock=-1.f;
    bool bSeatFired=false;
    double NextHintProbe=0.;
    double NextSupportProbe=0.;
    bool bRequested=false;
    bool bCandidate=false;
};
