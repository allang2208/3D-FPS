#pragma once
#include "TemperateHillsPCG.h"
#include "TemperateHillsCaptureSource.generated.h"

/** Review-only local ground anchor while a camera is elevated. Never spawned in normal play. */
UCLASS(Transient)
class UTemperateHillsCaptureSource : public UTemperateHillsGuestSource
{
    GENERATED_BODY()
public:
    virtual bool IsLocal() const override { return true; }
};
