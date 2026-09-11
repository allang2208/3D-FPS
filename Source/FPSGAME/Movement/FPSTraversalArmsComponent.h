#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "FPSTraversalArmsComponent.generated.h"

// Manually evaluated, single-player traversal view mesh. Adjust the evaluated
// pose before its component-space buffers are published to sockets and skinning.
UCLASS()
class FPSGAME_API UFPSTraversalArmsComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void SetSurfaceContact(UPrimitiveComponent* Surface, FVector Edge, FVector Outward, float Weight);
    void ResetSurfaceContact();
    virtual void FinalizeBoneTransform() override;
    int32 SurfaceCorrections=0;
    float MaxBoneLengthError=0.f;
private:
    TWeakObjectPtr<UPrimitiveComponent> ContactSurface;
    FVector EdgePoint=FVector::ZeroVector, WallOut=FVector::ForwardVector;
    FVector Anchors[2], SurfaceNormals[2];
    bool bAnchored[2]={false,false};
    float ContactWeight=0.f;
    TArray<FTransform> SourcePose;
    void FitSurfacePose();
};
