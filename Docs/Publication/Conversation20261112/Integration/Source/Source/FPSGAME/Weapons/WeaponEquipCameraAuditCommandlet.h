#pragma once
#include "Commandlets/Commandlet.h"
#include "WeaponEquipCameraAuditCommandlet.generated.h"

/** Explicit, headless equip camera sampling; isolated audit profile, no render. */
UCLASS()
class UWeaponEquipCameraAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 RunM249WristReview(const FString& Params);
};
