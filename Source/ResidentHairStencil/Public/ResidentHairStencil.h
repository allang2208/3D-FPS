#pragma once

#include "Templates/SharedPointer.h"

class ISceneViewExtension;
class UWorld;

namespace ResidentHairStencil
{
    constexpr int32 FocusBase = 144;
    constexpr int32 ShopBase = 176;
    constexpr int32 SlotCount = 16;

    RESIDENTHAIRSTENCIL_API TSharedRef<ISceneViewExtension, ESPMode::ThreadSafe> CreateViewExtension(UWorld* World);
}
