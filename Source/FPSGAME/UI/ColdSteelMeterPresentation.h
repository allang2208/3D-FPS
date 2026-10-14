#pragma once

#include "CoreMinimal.h"

/** Presentation only. The owner keeps authoritative values and warning thresholds. */
struct FColdSteelMeterTransition
{
    float Target = 0.f;
    float From = 0.f;
    float To = 0.f;
    double StartedAt = 0.;
    float Duration = 0.f;
    bool bInitialized = false;

    float UnwrappedValue(double Now) const
    {
        if (Duration <= 0.f) return To;
        const float T = FMath::Clamp(float((Now - StartedAt) / Duration), 0.f, 1.f);
        const float R = 1.f - T;
        return FMath::Lerp(From, To, 1.f - R * R * R);
    }

    bool IsAnimating(double Now) const { return Duration > 0.f && Now < StartedAt + Duration; }
    float ValueAt(double Now) const
    {
        if (!IsAnimating(Now)) return Target;
        const float Value = UnwrappedValue(Now);
        return Value > 1.f ? FMath::Frac(Value) : Value;
    }

    void SetTarget(float InRatio, double Now, bool bSnap = false, bool bLevelUp = false)
    {
        const float Next = FMath::IsFinite(InRatio) ? FMath::Clamp(InRatio, 0.f, 1.f) : 0.f;
        if (!bInitialized || bSnap)
        {
            Target = From = To = Next;
            Duration = 0.f;
            bInitialized = true;
            return;
        }
        if (Target == Next && !bLevelUp) return;
        // Keep an in-flight experience wrap when the next low-frequency sample arrives.
        const bool bWrapping = IsAnimating(Now) && To > 1.f;
        From = bWrapping ? UnwrappedValue(Now) : ValueAt(Now);
        To = Next + (bLevelUp ? FMath::FloorToFloat(bWrapping ? To : From) + 1.f : bWrapping ? FMath::FloorToFloat(To) : 0.f);
        Target = Next;
        StartedAt = Now;
        Duration = bLevelUp ? .40f : To < From ? .24f : .32f;
    }
};

class FSlateWindowElementList;
struct FGeometry;

namespace ColdSteelUI
{
    /** Shared rounded track and semantic gradient for player and monster resources. */
    FPSGAME_API int32 PaintResourceMeter(const FGeometry& Geometry, FSlateWindowElementList& Out,
        int32 Layer, FVector2D Offset, FVector2D Size, float DisplayRatio,
        const FLinearColor& Fill, const FLinearColor& Deep, const FLinearColor& BorderColor,
        const FLinearColor& Tint);
}
