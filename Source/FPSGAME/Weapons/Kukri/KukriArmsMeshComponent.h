#pragma once

#include "CoreMinimal.h"
#include "../../Skills/FPSCastingMeshComponent.h"
#include "KukriArmsMeshComponent.generated.h"

/**
 * 尼泊尔弯刀视模（共享剑臂 SK_FrostSword_Arms，V9 裸手由外观配置按网格档案接管）。
 * - clip 切换时做局部空间短淡化，刀柄由右手刚性带动（握持关系一致）；拔刀抛接时作者把刀带离拳头，
 *   锁定随作者偏离量淡出、接住时淡回，飞行段按作者轨迹播放；
 * - 双持弯刀进出双持握姿时左臂单独淡化（第二把刀挂在 hand_l，由 UKukriWeaponComponent 管理）；
 * - 副手持枪／魔法书时收起本视模的左臂，避免出现两条左臂；
 * - 其余左手施法叠加沿用 UFPSCastingMeshComponent。
 */
UCLASS()
class FPSGAME_API UKukriArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureEntry(float Seconds);
    /** Left arm only (into / out of the dual kukri hold): its own local blend, independent of the whole-rig entry. */
    void CaptureLeftEntry(float Seconds);
    void AdvanceEntry(float Delta);
    void ClearEntry(){EntryLocal.Reset();EntryTime=EntryDuration=0.f;LeftEntryLocal.Reset();LeftEntryTime=LeftEntryDuration=0.f;}
    /** Dual kukri run: the kukri turned in the right fist (reverse grip) by Angle (rad) about its grip-frame Axis.
     *  bHold keeps the grip lock on the turned relation instead of releasing to the clip's own WPN_root. */
    void SetGripFlip(float Angle,const FVector& Axis,bool bHold){GripFlipAngle=Angle;GripFlipAxis=Axis;bGripFlipHold=bHold;}
    virtual void FinalizeBoneTransform() override;
private:
    void CacheBones();
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<int32> LeftChain;
    TArray<int32> WeaponChain;   // descendants of WPN_root, carried with the grip lock
    int32 HandR=INDEX_NONE, Weapon=INDEX_NONE, ClavicleL=INDEX_NONE;
    TArray<FTransform> EntryLocal;
    float EntryTime=0.f, EntryDuration=0.f;
    TArray<FTransform> LeftEntryLocal;   // parent-space left chain at the capture, indexed like LeftChain
    float LeftEntryTime=0.f, LeftEntryDuration=0.f;
    float GripFlipAngle=0.f;
    FVector GripFlipAxis=FVector::YAxisVector;
    bool bGripFlipHold=false;
    bool bLeftCollapsed=false;
};
