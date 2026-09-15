#pragma once

#include "CoreMinimal.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "MonsterCharacterMovementComponent.generated.h"

/** Shares swept step collision with the player; smooths the existing monster mesh in place. */
UCLASS()
class FPSGAME_API UMonsterCharacterMovementComponent : public UFPSCharacterMovementComponent
{
    GENERATED_BODY()
public:
    UMonsterCharacterMovementComponent();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void OnTeleported() override;
    virtual bool IsWalkable(const FHitResult& Hit) const override;
    float GetMeshStairOffset() const { return MeshStairOffset; }

private:
    bool CanOffsetMesh() const;
    void ApplyMeshOffset(float Offset);
    float MeshStairOffset = 0.f;
    FVector AppliedRelativeOffset = FVector::ZeroVector;
    double FrameFloorZ = 0;
    bool bHaveFrameFloor = false;
};
