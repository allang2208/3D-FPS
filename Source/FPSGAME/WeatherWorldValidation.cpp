#include "WeatherWorldValidation.h"
#include "FPSWeatherManager.h"
#include "UI/ColdSteelHUDWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/Image.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"

namespace
{
    int32 RouteIndex = 0, TotalFailures = 0, TotalChecks = 0;
    const TCHAR* Route[] = {TEXT("DayNight_Lighting"), TEXT("L_Normandy_FPS_Test"), TEXT("L_MilitaryTrench_FPS_Test"), TEXT("DayNight_Lighting")};
    const TCHAR* Regions[] = {TEXT("天空基地"), TEXT("诺曼底村庄"), TEXT("战壕"), TEXT("天空基地")};
    bool IsWet(EFPSWeatherState State) { return State >= EFPSWeatherState::LightRain; }
}

// Opt-in standalone acceptance. No weather presets are forced during the random phase.
// Speed up the map's real clock, record a live forecast, then wait for it to occur.
struct FWeatherWorldAudit
{
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle Timer;
    float Started = 0, NormalStart = 0, NormalFraction = 0, AcceleratedStart = 0;
    float ForecastStart = -1, ForecastEnd = -1, MarkerBefore = 0;
    EFPSWeatherState ForecastState = EFPSWeatherState::Clear;
    int32 Step = 0, Checks = 0, Failures = 0, Samples = 0, Mismatches = 0, Transitions = 0;
    int32 LastState = -1;
    TSet<int32> States;
    bool bForecastFulfilled = false;

    void Check(bool Pass, const TCHAR* Name)
    {
        ++Checks; ++TotalChecks; Failures += !Pass; TotalFailures += !Pass;
        UE_LOG(LogTemp, Display, TEXT("WEATHER_WORLD_CHECK %s map=%s %s"), Pass ? TEXT("PASS") : TEXT("FAIL"), Route[RouteIndex], Name);
    }

    UColdSteelHUDWidget* FindHUD(UWorld* World, int32& Count) const
    {
        Count = 0; UColdSteelHUDWidget* Result = nullptr;
        for (TObjectIterator<UColdSteelHUDWidget> It; It; ++It)
            if (It->GetWorld() == World && It->IsInViewport()) { ++Count; Result = *It; }
        return Result;
    }

    void Capture(const TCHAR* Label)
    {
        const FString Dir = FPaths::ProjectSavedDir() / TEXT("WeatherWorldAudit20260912/images");
        IFileManager::Get().MakeDirectory(*Dir, true);
        FScreenshotRequest::RequestScreenshot(Dir / (FString(Route[RouteIndex]) + TEXT("-") + Label + TEXT(".png")), true, false);
    }

    bool InsideHUD(UColdSteelHUDWidget* HUD, UWidget* Widget) const
    {
        const FGeometry& G = Widget->GetCachedGeometry();
        const FVector2D Min = HUD->GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute(FVector2D::ZeroVector));
        const FVector2D Max = HUD->GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute(G.GetLocalSize()));
        const FVector2D Limit = HUD->GetCachedGeometry().GetLocalSize();
        return G.GetLocalSize().X > 0 && G.GetLocalSize().Y > 0 && Min.X >= -1 && Min.Y >= -1 && Max.X <= Limit.X + 1 && Max.Y <= Limit.Y + 1;
    }

    void Accelerate(AFPSWeatherManager* W)
    {
        W->RealSecondsPerGameDay = 60; W->TransitionSeconds = .2f;
        W->WeatherClockSeconds = 0; W->NormalizedDayTime = 0; W->DaySerial = 0; W->LastSkyTimeUnits = 0;
        int32 ClockFields = 0;
        for (TActorIterator<AActor> It(W->GetWorld()); It; ++It)
            if (It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager")))
                for (TFieldIterator<FProperty> P(It->GetClass()); P; ++P)
                {
                    const FString Name = P->GetName().Replace(TEXT(" "), TEXT("")).Replace(TEXT("_"), TEXT(""));
                    const bool Height = Name.Contains(TEXT("SunHeight")), Speed = Name.Contains(TEXT("SunSpeed"));
                    if (!Height && !Speed) continue;
                    if (auto* F = CastField<FFloatProperty>(*P)) { F->SetPropertyValue_InContainer(*It, Height ? 0 : 40); ++ClockFields; }
                    if (auto* F = CastField<FDoubleProperty>(*P)) { F->SetPropertyValue_InContainer(*It, Height ? 0 : 40); ++ClockFields; }
                }
        Check(!W->IsSkyClockConnected() || ClockFields == 2, TEXT("accelerates the authoritative external or native clock"));
        AcceleratedStart = W->GetWorld()->GetTimeSeconds();
    }

    void Finish(UWorld* World)
    {
        UE_LOG(LogTemp, Display, TEXT("WEATHER_WORLD_RESULT map=%s route=%d checks=%d failures=%d samples=%d transitions=%d states=%d"),
            Route[RouteIndex], RouteIndex, Checks, Failures, Samples, Transitions, States.Num());
        World->GetTimerManager().ClearTimer(Timer);
        if (++RouteIndex == UE_ARRAY_COUNT(Route))
        {
            UE_LOG(LogTemp, Display, TEXT("WEATHER_WORLD_AUDIT_%s checks=%d failures=%d worlds=3 travels=3"), TotalFailures ? TEXT("FAIL") : TEXT("PASS"), TotalChecks, TotalFailures);
            if (auto* PC = UGameplayStatics::GetPlayerController(World, 0)) PC->ConsoleCommand(TEXT("quit"));
            return;
        }
        // Same OpenLevel path used by the portals; it destroys the old HUD and weather owner.
        UGameplayStatics::OpenLevel(World, FName(*(FString(TEXT("/Game/GameMaps/")) + Route[RouteIndex])));
    }

    void Tick()
    {
        if (!Weather.IsValid()) return;
        auto* W = Weather.Get(); auto* World = W->GetWorld();
        const float Time = World->GetTimeSeconds() - Started;
        int32 HUDCount = 0; auto* HUD = FindHUD(World, HUDCount);
        auto* PC = UGameplayStatics::GetPlayerController(World, 0);
        if (!HUD || !PC)
        {
            if (Time > 30) { Check(false, TEXT("live player and HUD ready within 30 seconds")); Finish(World); }
            return;
        }
        if (Step == 0 && Time >= 3)
        {
            int32 Managers = 0; for (TActorIterator<AFPSWeatherManager> It(World); It; ++It) ++Managers;
            Check(Managers == 1 && HUDCount == 1 && W->bAutomaticSchedule, TEXT("one automatic weather owner and one live HUD after map entry"));
            Check(W->RealSecondsPerGameDay == 2160 && W->RainSystem && W->GetPresentationAssets(), TEXT("36-minute day and rain presentation loaded"));
            Check(W->IsSkyClockConnected() || W->IsSceneDayNightActive(), TEXT("map has an active sky or scene clock"));
            NormalStart = World->GetTimeSeconds(); NormalFraction = W->NormalizedDayTime;
            if (PC->GetPawn()) PC->GetPawn()->SetCanBeDamaged(false);
            Step = 1;
        }
        if (Step == 1 && World->GetTimeSeconds() - NormalStart >= 3)
        {
            const float Elapsed = World->GetTimeSeconds() - NormalStart;
            const float ClockElapsed = FMath::Fmod(W->NormalizedDayTime - NormalFraction + 1, 1) * 2160;
            UE_LOG(LogTemp, Display, TEXT("WEATHER_WORLD_CLOCK map=%s external=%d elapsed=%.3f clock=%.3f"), Route[RouteIndex], W->IsSkyClockConnected(), Elapsed, ClockElapsed);
            Check(FMath::Abs(Elapsed - ClockElapsed) < .6f, TEXT("normal clock advances at 2160 seconds per game day"));
            Check(HUD->bTimelineHasEvent && HUD->TimelineMarkerImage->GetBrush().GetResourceObject() && InsideHUD(HUD, HUD->TimelineWidthBox), TEXT("compact live event marker has an icon and visible geometry"));
            Check(HUD->TimelineEventLabel.Contains(Regions[RouteIndex]), TEXT("live forecast names the current world"));
            Capture(RouteIndex == 3 ? TEXT("return") : TEXT("compact")); Step = 2;
        }
        if (Step == 2 && Time >= 8)
        {
            if (RouteIndex == 3) { Finish(World); return; }
            TSet<int32> Possibilities;
            for (int32 Day = 0; Day < 32; ++Day) for (int32 Segment = 0; Segment < 8; ++Segment)
                Possibilities.Add(static_cast<int32>(W->GetScheduledStateAt(Day, Segment)));
            Check(Possibilities.Num() == 5, TEXT("seeded schedule can produce all five weather states"));
            Accelerate(W); Step = 3;
        }
        if (Step < 3) return;
        const float FastTime = World->GetTimeSeconds() - AcceleratedStart;
        const float Calendar = (W->GetScheduleDay() + W->NormalizedDayTime) * 60;
        if (FastTime > 1 && FastTime < 89)
        {
            const int32 State = static_cast<int32>(W->CurrentState);
            States.Add(State); if (LastState != State) { if (LastState != -1) ++Transitions; LastState = State; }
            // Exclude the HUD's 250ms refresh window on segment edges.
            const float Within = FMath::Fmod(Calendar, 7.5f);
            if (Within > .75f && Within < 6.75f)
            {
                ++Samples;
                Mismatches += !W->bAutomaticSchedule || HUD->TimelineDaySerial != W->GetScheduleDay()
                    || HUD->bTimelineEventActive != IsWet(W->CurrentState);
            }
            if (ForecastStart >= 0 && Calendar > ForecastStart + 1 && Calendar < ForecastEnd - 1 && !bForecastFulfilled)
            {
                Check(W->CurrentState == ForecastState && HUD->bTimelineEventActive, TEXT("previously displayed forecast occurs automatically at its scheduled time"));
                bForecastFulfilled = true;
            }
        }
        if (Step == 3 && FastTime >= 12)
        {
            Check(FMath::Abs(Calendar - FastTime) < .65f, TEXT("accelerated calendar advances from real elapsed time"));
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftAlt, IE_Pressed, 1.f)); Step = 4;
        }
        if (Step == 4 && FastTime >= 13)
        {
            Check(PC->bShowMouseCursor, TEXT("holding Left Alt enables timeline interaction"));
            HUD->TimelineToggleButton->OnClicked.Broadcast(); Step = 5;
        }
        if (Step == 5 && FastTime >= 15)
        {
            Check(!HUD->bTimelineCompact && InsideHUD(HUD, HUD->TimelineWidthBox), TEXT("expand button opens the live timeline within the viewport"));
            ForecastStart = HUD->TimelineEventStart; ForecastEnd = HUD->TimelineStageEnds[0];
            ForecastState = static_cast<EFPSWeatherState>(HUD->TimelineStageStates[0]); MarkerBefore = HUD->TimelineEventFraction;
            Check(!HUD->bTimelineEventActive && ForecastStart > Calendar, TEXT("dry interval shows a future rain event with countdown"));
            Capture(TEXT("expanded")); Step = 6;
        }
        if (Step == 6 && FastTime >= 17)
        {
            HUD->TimelineMarkerButton->OnClicked.Broadcast(); Step = 7;
        }
        if (Step == 7 && FastTime >= 19)
        {
            Check(HUD->TimelinePopover->IsVisible() && InsideHUD(HUD, HUD->TimelinePopover), TEXT("event detail popover is visible and inside the viewport"));
            bool HasRegion = false;
            TArray<UWidget*> Children; HUD->WidgetTree->GetAllWidgets(Children);
            for (UWidget* Child : Children) if (auto* Text = Cast<UTextBlock>(Child)) HasRegion |= Text->GetText().ToString() == Regions[RouteIndex];
            Check(HasRegion, TEXT("event detail world field is correct"));
            Check(HUD->TimelineEventFraction < MarkerBefore, TEXT("event marker approaches now as the real clock advances"));
            Capture(TEXT("details")); Step = 8;
        }
        if (Step == 8 && FastTime >= 22)
        {
            HUD->TimelineWeatherFilterButton->OnClicked.Broadcast();
            Check(HUD->bTimelineWeatherFilter && HUD->bTimelineHasEvent && !HUD->TimelinePopover->IsVisible(), TEXT("weather filter preserves the live event and closes details"));
            HUD->TimelineAllFilterButton->OnClicked.Broadcast();
            Check(!HUD->bTimelineWeatherFilter && HUD->TimelineInvasionText->GetText().ToString().Contains(TEXT("暂无")), TEXT("all filter works without fabricated invasion events"));
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftAlt, IE_Released, 0.f)); Step = 9;
        }
        if (Step == 9 && FastTime >= 24)
        {
            Check(!PC->bShowMouseCursor, TEXT("releasing Left Alt returns gameplay cursor mode")); Step = 10;
        }
        if (Step == 10 && FastTime >= 70)
        {
            Check(W->GetScheduleDay() >= 1 && W->CurrentState == EFPSWeatherState::Storm && HUD->TimelineMarkerTimeText->GetText().ToString() == TEXT("进行中"), TEXT("natural midnight rollover reaches storm and an active event marker"));
            auto* LateHUD = CreateWidget<UColdSteelHUDWidget>(PC);
            LateHUD->RefreshEventTimeline(true);
            Check(LateHUD->TimelineGradientTexture != HUD->TimelineGradientTexture, TEXT("rebuilt HUD does not overwrite the live timeline texture"));
            Check(LateHUD->TimelineDaySerial == W->GetScheduleDay() && LateHUD->TimelineEventStart == HUD->TimelineEventStart
                && LateHUD->TimelineEventEnd == HUD->TimelineEventEnd && LateHUD->TimelineStageStates == HUD->TimelineStageStates,
                TEXT("HUD created after midnight uses the authoritative calendar and forecast"));
            Capture(TEXT("storm")); Step = 11;
        }
        if (Step == 11 && FastTime >= 89)
        {
            Check(Samples > 150 && Mismatches == 0, TEXT("live timeline stays synchronized throughout random weather and midnight"));
            Check(States.Contains(0) && States.Contains(1) && States.Contains(3) && States.Contains(4) && Transitions >= 6 && bForecastFulfilled,
                TEXT("automatic sequence reaches clear cloudy rain and storm without forced presets"));
            W->SetWeatherState(EFPSWeatherState::Rain); Step = 12;
        }
        if (Step == 12 && FastTime >= 91)
        {
            Check(HUD->bTimelineManual && HUD->bTimelineEventActive && HUD->TimelineDurationLabel.Contains(TEXT("手动")), TEXT("manual rain displays active weather without inventing an end time"));
            W->SetWeatherState(EFPSWeatherState::Clear); Step = 13;
        }
        if (Step == 13 && FastTime >= 93)
        {
            Check(!HUD->bTimelineHasEvent && !HUD->TimelineMarkerButton->IsVisible(), TEXT("manual clear hides the rain event"));
            W->ResumeAutomaticSchedule(); Step = 14;
        }
        if (Step == 14 && FastTime >= 95)
        {
            Check(W->bAutomaticSchedule && !HUD->bTimelineManual && HUD->bTimelineHasEvent, TEXT("resume automatic restores the live forecast"));
            Finish(World);
        }
    }
};

void StartWeatherWorldValidation(AFPSWeatherManager* Weather)
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("WeatherWorldAudit"))) return;
    auto Audit = MakeShared<FWeatherWorldAudit>(); Audit->Weather = Weather;
    Audit->Started = Weather->GetWorld()->GetTimeSeconds();
    Weather->GetWorld()->GetTimerManager().SetTimer(Audit->Timer, [Audit]() { Audit->Tick(); }, .25f, true);
}
