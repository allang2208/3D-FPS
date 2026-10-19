#pragma once

#include "CoreMinimal.h"
#include "Components/PoseableMeshComponent.h"
#include "FPSHeadEquipmentMeshComponent.generated.h"

/** Cosmetic spring bones for flexible headwear; no gameplay physics or replicated pose. */
UCLASS(ClassGroup=(Player))
class FPSGAME_API UFPSHeadEquipmentMeshComponent : public UPoseableMeshComponent
{
    GENERATED_BODY()
public:
    UFPSHeadEquipmentMeshComponent();
    void ConfigureTip(const TArray<FName>& Bones,float MaxDegrees,float Frequency,float Damping);
    void SetDynamicsVisible(bool bVisible);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    TArray<int32> TipBones;
    TArray<FTransform> RestPose;
    TArray<FVector> TipAxesX,TipAxesY;
    FVector2D Bend=FVector2D::ZeroVector,Speed=FVector2D::ZeroVector;
    FVector PreviousLocation=FVector::ZeroVector,PreviousVelocity=FVector::ZeroVector;
    FQuat PreviousRotation=FQuat::Identity;
    float Limit=.174533f,Omega=15.7f,DampingRatio=.6f;
    bool bSampled=false;
    void ResetTip();
    void ApplyTip();
};
