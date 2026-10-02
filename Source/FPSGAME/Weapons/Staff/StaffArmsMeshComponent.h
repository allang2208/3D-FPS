#pragma once
#include "../../Skills/FPSCastingMeshComponent.h"
#include "StaffCastMotion.h"
#include "StaffArmsMeshComponent.generated.h"

/** V7 native skeleton; right-hand grip and arm support follow the casting staff. */
UCLASS()
class FPSGAME_API UStaffArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    virtual void FinalizeBoneTransform() override;
    FTransform AuthoredContactInCamera(const FStaffCastPose& Motion,int32 Variant,bool bCharge=false);
private:
    void CacheReferencePose();
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<FTransform> RefComponent,RefLocal;
};
