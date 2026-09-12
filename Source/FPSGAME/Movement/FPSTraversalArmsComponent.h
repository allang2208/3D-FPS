#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "FPSTraversalArmsComponent.generated.h"

struct FFPSTraversalTarget;

// Manually evaluated, single-player traversal view mesh. Adjust the evaluated
// pose before its component-space buffers are published to sockets and skinning.
UCLASS()
class FPSGAME_API UFPSTraversalArmsComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void SetSurfaceContact(const FFPSTraversalTarget& Target,float Weight);
    void ResetSurfaceContact();
    virtual void FinalizeBoneTransform() override;
    int32 SurfaceCorrections=0;
    float MaxBoneLengthError=0.f;
    int32 AnchoredHandCount() const { return int32(bAnchored[0])+int32(bAnchored[1]); }
private:
    TWeakObjectPtr<UPrimitiveComponent> ContactSurface;
    FVector WallOut=FVector::ForwardVector;
    FVector Anchors[2], SurfaceNormals[2];
    bool bAnchored[2]={false,false};
    float ContactWeight=0.f;
    TArray<FTransform> SourcePose;
    void FitSurfacePose();
};
