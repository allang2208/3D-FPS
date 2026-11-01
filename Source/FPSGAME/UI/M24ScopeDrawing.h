#pragma once
#include "CoreMinimal.h"
#include "Rendering/DrawElements.h"

class APlayerController;

// Owned by the widget; reuse the bounded drawing buffers between frames.
struct FM24ScopeReticleCache
{
    TArray<FSlateVertex> Vertices;
    TArray<SlateIndex> Indices;
};

namespace M24ScopeDrawing
{
void PaintReticle(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geometry,
    const FVector2f& Center, float Radius, float Alpha, const APlayerController* Controller,
    FM24ScopeReticleCache& Cache,float OpticalFieldOfView=0.f);
}
