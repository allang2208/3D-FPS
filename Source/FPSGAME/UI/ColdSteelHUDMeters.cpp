#include "ColdSteelHUDWidget.h"
#include "ColdSteelResourceMeter.h"
#include "../FPSGAMECharacter.h"
#include "Components/ProgressBar.h"
#include "HAL/PlatformTime.h"

void UColdSteelHUDWidget::SetAnimatedBarValue(UProgressBar* Bar, float Ratio, bool bLevelUp)
{
    if (!Bar) return;
    const double Now = FPlatformTime::Seconds();
    auto& Transition = ResourceBarTransitions.FindOrAdd(TWeakObjectPtr<UProgressBar>(Bar));
    Transition.SetTarget(Ratio, Now, false, bLevelUp);
    const float Display = Transition.ValueAt(Now);
    if (Bar->GetPercent() != Display) Bar->SetPercent(Display);
}

void UColdSteelHUDWidget::TickResourceBarAnimations()
{
    const double Now = FPlatformTime::Seconds();
    auto* Pawn = GetOwningPlayerPawn();
    if (ResourceMeterPawn.Get() != Pawn)
    {
        ResourceMeterPawn = Pawn;
        ResourceBarTransitions.Reset();
        ExperienceBarLevel = INDEX_NONE;
        for (auto* Meter : {TopHealthMeter.Get(), TopManaMeter.Get(), StaminaMeter.Get()})
            if (Meter) Meter->ResetAnimation();
        for (const auto& Meter : SurvivalMeters) if (Meter) Meter->ResetAnimation();
        RefreshTopVitals();
        RefreshStamina();
        RefreshExpBar();
    }

    // Only interpolate the handful of already-bound bars. No gameplay queries per bar.
    for (auto It = ResourceBarTransitions.CreateIterator(); It; ++It)
    {
        auto* Bar = It.Key().Get();
        if (!Bar) { It.RemoveCurrent(); continue; }
        const float Display = It.Value().ValueAt(Now);
        if (Bar->GetPercent() != Display) Bar->SetPercent(Display);
    }

    FMonsterHitFeedback Hit;
    const auto* Character = Cast<AFPSGAMECharacter>(Pawn);
    if (Character && Character->GetMonsterHitFeedback(Hit))
    {
        const bool bNewTarget = HUDMeterTarget != Hit.Target;
        HUDMeterTarget = Hit.Target;
        HUDTargetHealthTransition.SetTarget(Hit.Health / FMath::Max(1.f, Hit.MaxHealth), Now, bNewTarget);
        HUDTargetToughnessTransition.SetTarget(Hit.Toughness / FMath::Max(1.f, Hit.ToughnessThreshold), Now, bNewTarget);
    }
    else
    {
        HUDMeterTarget.Reset();
        HUDTargetHealthTransition = FColdSteelMeterTransition{};
        HUDTargetToughnessTransition = FColdSteelMeterTransition{};
    }
}
