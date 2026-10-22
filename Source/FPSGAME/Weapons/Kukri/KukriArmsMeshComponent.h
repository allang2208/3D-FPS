#pragma once

#include "CoreMinimal.h"
#include "../../Skills/FPSCastingMeshComponent.h"
#include "KukriArmsMeshComponent.generated.h"

/**
 * 尼泊尔弯刀视模（共享剑臂 SK_FrostSword_Arms，V9 裸手由外观配置按网格档案接管）。
 * - clip 切换时做局部空间短淡化，刀柄始终由右手刚性带动（所有 clip 握持关系一致）；
 * - 副手持枪／魔法书时收起本视模的左臂，避免出现两条左臂；
 * - 其余左手施法叠加沿用 UFPSCastingMeshComponent。
 */
UCLASS()
class FPSGAME_API UKukriArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureEntry(float Seconds);
    void AdvanceEntry(float Delta);
    void ClearEntry(){EntryLocal.Reset();EntryTime=EntryDuration=0.f;}
    virtual void FinalizeBoneTransform() override;
private:
    void CacheBones();
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<int32> LeftChain;
    TArray<int32> WeaponChain;   // descendants of WPN_root, carried with the grip lock
    int32 HandR=INDEX_NONE, Weapon=INDEX_NONE, ClavicleL=INDEX_NONE;
    TArray<FTransform> EntryLocal;
    float EntryTime=0.f, EntryDuration=0.f;
    bool bLeftCollapsed=false;
};
