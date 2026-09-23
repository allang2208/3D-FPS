#pragma once
#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"
#include "PKMBipodComponent.generated.h"

class USkeletalMeshComponent;

namespace PKMBipodAssets
{
inline constexpr const TCHAR* Base = TEXT("/Game/Weapons/PKMLowpoly20260922/Bipod26/SM_PKM_Bipod_Base");
inline constexpr const TCHAR* LegA = TEXT("/Game/Weapons/PKMLowpoly20260922/Bipod26/SM_PKM_Bipod_LegA");
inline constexpr const TCHAR* LegB = TEXT("/Game/Weapons/PKMLowpoly20260922/Bipod26/SM_PKM_Bipod_LegB");
}

/** Articulated visual: free inertial motion or deployment-controller contacts. */
UCLASS()
class FPSGAME_API UPKMBipodComponent : public UStaticMeshComponent
{
    GENERATED_BODY()
public:
    UPKMBipodComponent();
    bool Configure(USkeletalMeshComponent* Rifle, bool Enabled);
    FVector GetHingeWorld() const;
    FVector GetRestFootWorld(int32 Leg) const;
    bool CanReachContacts(const FVector& A,const FVector& B,const FVector& MountDelta) const;
    void SetDeploymentContacts(const FVector& A,const FVector& B,float Weight);
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
private:
    void ResetMotion();
    void ApplyAngle();
    TWeakObjectPtr<USkeletalMeshComponent> Weapon;
    double LastTime = -1.;
    FVector LastPosition = FVector::ZeroVector, LastVelocity = FVector::ZeroVector;
    FVector LastSpin = FVector::ZeroVector, Acceleration = FVector::ZeroVector, SpinAcceleration = FVector::ZeroVector;
    FQuat LastRotation = FQuat::Identity;
    float Angles[2] = {}, AngularSpeeds[2] = {};
    FVector ContactPoints[2]={FVector::ZeroVector,FVector::ZeroVector};
    float ContactWeight=0.f;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> FirstLeg;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> SecondLeg;
};
