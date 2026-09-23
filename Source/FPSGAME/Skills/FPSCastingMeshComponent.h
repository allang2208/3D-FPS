#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "../Weapons/PKMCarryHandleDynamics.h"
#include "../Weapons/PKMOutgoingBeltDynamics.h"
#include "FPSCastingMeshComponent.generated.h"

class UFPSFireballComponent;
class UFPSQuickCombatComponent;

// Apply the shared cast after the weapon/tool/traversal animation is evaluated.
// 只改左臂（火球施法）；手枪砸击已改为作者源 clip，不再走这里的程序化姿态层。
UCLASS()
class FPSGAME_API UFPSCastingMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    bool bApplyLeftHandCast=true;
    FPKMOutgoingBeltDynamics OutgoingBeltDynamics;
    virtual void FinalizeBoneTransform() override;
    /** 快速进战打击探针：握把底的世界位置（命中射线起点与画面同源）。 */
    bool GetQuickCombatStrikeProbe(FVector& OutOrigin) const;
    /** 跟随当前姿态的近战探针：参考动作取各枪枪托，旧动作保留枪身前段。 */
    bool GetRifleStockMeleeProbe(FVector& OutOrigin,bool bM4StockPoint=false) const;
private:
    FPKMCarryHandleDynamics CarryHandleDynamics;
    TWeakObjectPtr<USkeletalMesh> PoseMesh;
    TArray<FTransform> ReferencePose, SourcePose, GoalPose, EntryLocal;
    TArray<int32> LeftBones;
    int32 CastClavicleIndex=INDEX_NONE,CastUpperIndex=INDEX_NONE,CastLowerIndex=INDEX_NONE,CastHandIndex=INDEX_NONE;
    uint32 EntrySerial=0;
    FQuat ReferencePalm=FQuat::Identity;
    void CacheCastSkeleton();
    void ApplyCastPose(UFPSFireballComponent* Magic);
    int32 BashHandR=INDEX_NONE;   // 打击探针读取的握把手骨
};
