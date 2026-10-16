#pragma once

#include "CoreMinimal.h"
#include "Components/PoseableMeshComponent.h"
#include "BookLeafComponent.generated.h"

/** Reusable double-sided sheet. Printing stays on its material slots as bones move. */
UCLASS()
class FPSGAME_API UBookLeafComponent : public UPoseableMeshComponent
{
    GENERATED_BODY()
public:
    UBookLeafComponent();
    bool InitializeTemplate(class USkeletalMesh* Mesh);
    // 0 rests on the right, 1 rests on the left. Coordinates are centimetres.
    void SetPagePose(float Turn,float CurlDirection=1.f,float CornerLift=0.f);

    UPROPERTY(EditAnywhere,Category="Book|Paper") float PaperWidth=15.51884842f;
    UPROPERTY(EditAnywhere,Category="Book|Paper") float PaperHeight=24.18600941f;
    UPROPERTY(EditAnywhere,Category="Book|Paper") float RestArch=.22f;
    UPROPERTY(EditAnywhere,Category="Book|Paper") float TurnBend=.58f;
private:
    TArray<int32> Chain;
    TArray<FTransform> ReferenceComponentPose;
    TArray<FTransform> WorkingComponentPose;
};
