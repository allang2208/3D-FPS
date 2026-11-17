#pragma once

#include "CoreMinimal.h"

class ATemperateHillsWorld;
class UTexture2D;
class UTextureRenderTarget2D;

// Builds terrain geometry and contour pixels off-thread, then renders the ground
// material once on the game thread. Closing the map cancels unneeded CPU work.
class FColdSteelHillsMap
{
public:
    explicit FColdSteelHillsMap(const ATemperateHillsWorld& Terrain);
    ~FColdSteelHillsMap();
    bool IsReady() const;
    bool Finish(ATemperateHillsWorld& Terrain, UTextureRenderTarget2D*& Photo, UTexture2D*& Lines);
private:
    struct FJob;
    TUniquePtr<FJob> Job;
};
