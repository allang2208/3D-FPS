#pragma once
#include "Commandlets/Commandlet.h"
#include "ShotgunAmmoIconDiagnosisCommandlet.generated.h"

/** Offscreen reproduction of the Super90 ammo wheel; never initializes a save profile. */
UCLASS()
class UShotgunAmmoIconDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
