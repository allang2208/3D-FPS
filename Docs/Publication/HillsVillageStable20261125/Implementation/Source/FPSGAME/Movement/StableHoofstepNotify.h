#pragma once

#include "Animation/AnimNotifies/AnimNotify.h"
#include "StableHoofstepNotify.generated.h"

class USoundWave;

UCLASS(meta=(DisplayName="Stable Horse Hoofstep"))
class FPSGAME_API UStableHoofstepNotify : public UAnimNotify
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, Category="Hoofstep") FName HoofBone;
    UPROPERTY(EditAnywhere, Category="Hoofstep") TArray<TObjectPtr<USoundWave>> Variations;
    UPROPERTY(EditAnywhere, Category="Hoofstep", meta=(ClampMin="0.0")) float Gain=1.f;
    UPROPERTY(EditAnywhere, Category="Hoofstep") bool bReverseOnly=false;

    void Notify(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
        const FAnimNotifyEventReference& EventReference) override;
};
