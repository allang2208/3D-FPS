#include "WeatherPanelValidation.h"
#include "WeatherControlWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSWeatherManager.h"
#include "Blueprint/WidgetTree.h"
#include "Components/AudioComponent.h"
#include "Components/Button.h"
#include "Components/DirectionalLightComponent.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "NiagaraComponent.h"
#include "TimerManager.h"
#include "UnrealClient.h"

// Opt-in standalone acceptance; no fixtures or timers run in ordinary play.
namespace
{
    struct FWeatherAudit
    {
        TWeakObjectPtr<AFPSGAMEPlayerController> PC;
        TWeakObjectPtr<UWeatherControlWidget> UI;
        TWeakObjectPtr<AFPSWeatherManager> Weather;
        FTimerHandle Timer;
        int32 Phase = -1;
        int32 Failures = 0;
        float MinSun = MAX_flt;
        float MaxSun = 0;
        float LastClock = 0;
        bool bClockMoved = false;
        bool bCapturedDay = false;
        bool bCapturedNight = false;
        bool bSunDirectionMoved = false;
        TMap<TWeakObjectPtr<UDirectionalLightComponent>,FRotator> InitialSunRotations;
        void Check(bool bPass, const TCHAR* Name)
        {
            Failures += bPass ? 0 : 1;
            UE_LOG(LogTemp, Display, TEXT("WeatherPanelAudit: %s %s"), bPass ? TEXT("PASS") : TEXT("FAIL"), Name);
        }
        void Click(int32 Index)
        {
            UButton* Button = Cast<UButton>(UI->WidgetTree->FindWidget(*FString::Printf(TEXT("WeatherPreset%d"), Index)));
            Check(Button != nullptr, TEXT("preset button exists"));
            if (Button) Button->OnClicked.Broadcast();
        }
        void Step()
        {
            if (!PC.IsValid() || !UI.IsValid()) return;
            UWorld* World = PC->GetWorld();
            if (Phase == -1)
            {
                int32 Count = 0;
                for (TActorIterator<AFPSWeatherManager> It(World); It; ++It) { Weather = *It; ++Count; }
                Check(Count == 1, TEXT("exactly one weather manager"));
                Check(PC->GetPawn() != nullptr, TEXT("player spawned"));
                if (!Weather.IsValid()) { PC->ConsoleCommand(TEXT("quit")); return; }
                Weather->TransitionSeconds = 1.0f;
                LastClock = Weather->NormalizedDayTime;
                PC->ToggleWeatherPanel();
                Check(UI->IsPanelOpen() && PC->bShowMouseCursor && PC->IsMoveInputIgnored() && PC->IsLookInputIgnored(), TEXT("panel owns input"));
                Click(0);
                Phase = 0;
                return;
            }
            if (Phase <= 4)
            {
                const float Expected[] = {0, 0, .35f, .68f, 1};
                Check(static_cast<int32>(Weather->CurrentState) == Phase && !Weather->bAutomaticSchedule, TEXT("manual preset persists"));
                Check(FMath::IsNearlyEqual(Weather->GetEffectiveRainIntensity(), Expected[Phase], .015f), TEXT("rain intensity reaches preset"));
                Check(Weather->RainSystem && Weather->SplashSystem && Weather->LightRainSound && Weather->RainSound && Weather->HeavyRainSound && Weather->ThunderSounds.Num() > 0, TEXT("weather assets loaded"));
                for (UNiagaraComponent* FX : TInlineComponentArray<UNiagaraComponent*>(Weather.Get()))
                {
                    bool Valid = false;
                    const float Rate = FX->GetVariableFloat(TEXT("User.SpawnRate"), Valid);
                    // Surface/roof pools legitimately stay inactive where no receiving surface exists.
                    const bool bCameraRain=FX->GetFName()==TEXT("CameraRain");
                    Check(Valid && (Phase <= 1 ? Rate < .1f : (bCameraRain ? Rate > 0 : Rate >= 0)), TEXT("Niagara receives rain rate"));
                    UE_LOG(LogTemp, Display, TEXT("WeatherPanelAudit: phase=%d %s rate=%.3f active=%d"), Phase, *FX->GetName(), Rate, FX->IsActive());
                }
                if (Phase <= 1)
                    for (UAudioComponent* Audio : TInlineComponentArray<UAudioComponent*>(Weather.Get()))
                        Check(!Audio->IsPlaying(), TEXT("dry weather has no rain or thunder audio"));
                Check(Weather->IsSkyClockConnected() || Weather->IsSceneDayNightActive(), TEXT("scene lighting connected"));
                if (FParse::Param(FCommandLine::Get(), TEXT("WeatherPanelCapture")))
                {
                    const FString Dir = FPaths::ProjectSavedDir() / TEXT("WeatherPanel");
                    IFileManager::Get().MakeDirectory(*Dir, true);
                    FScreenshotRequest::RequestScreenshot(Dir / FString::Printf(TEXT("%s-preset%d.png"), *UGameplayStatics::GetCurrentLevelName(World, true), Phase), true, false);
                }
                ++Phase;
                if (Phase <= 4)
                {
                    const TWeakObjectPtr<UWeatherControlWidget> WeakUI = UI;
                    const int32 Next = Phase;
                    FTimerHandle NextPreset;
                    World->GetTimerManager().SetTimer(NextPreset, [WeakUI, Next]()
                    {
                        if (WeakUI.IsValid())
                            if (UButton* Button = Cast<UButton>(WeakUI->WidgetTree->FindWidget(*FString::Printf(TEXT("WeatherPreset%d"), Next))))
                                Button->OnClicked.Broadcast();
                    }, .5f, false);
                }
                else
                {
                    // Leave the last preset visible until its screenshot is rendered.
                }
                return;
            }
            if (Phase == 5)
            {
                Click(5);
                Check(Weather->bAutomaticSchedule, TEXT("automatic schedule resumes"));
                UI->SetPanelOpen(false);
                Check(!PC->bShowMouseCursor && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("gameplay input restored"));
                PC->ToggleWeatherPanel();
                Check(UI->IsPanelOpen(), TEXT("panel reopens"));
                UI->SetPanelOpen(false);
                Weather->RealSecondsPerGameDay = 12.0f;
                ++Phase;
                return;
            }
            // The main map owns its sky clock in Blueprint; the weather's local test speed
            // does not accelerate that external clock. Observe its real incremental motion.
            bClockMoved |= FMath::Abs(Weather->NormalizedDayTime - LastClock) > .0001f;
            LastClock = Weather->NormalizedDayTime;
            for (TActorIterator<AActor> It(World); It; ++It)
                for (UDirectionalLightComponent* Sun : TInlineComponentArray<UDirectionalLightComponent*>(*It))
                {
                    MinSun = FMath::Min(MinSun, Sun->Intensity);
                    MaxSun = FMath::Max(MaxSun, Sun->Intensity);
                    const TWeakObjectPtr<UDirectionalLightComponent> Key(Sun);
                    if(const FRotator* Initial=InitialSunRotations.Find(Key))bSunDirectionMoved|=!Initial->Equals(Sun->GetComponentRotation(),.1f);
                    else InitialSunRotations.Add(Key,Sun->GetComponentRotation());
                }
            if (FParse::Param(FCommandLine::Get(), TEXT("WeatherPanelCapture")))
            {
                const float Hour = Weather->NormalizedDayTime * 24;
                const bool bDay = Hour > 8 && Hour < 16;
                const bool bNight = Hour > 20 || Hour < 4;
                if ((bDay && !bCapturedDay) || (bNight && !bCapturedNight))
                {
                    FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("WeatherPanel") /
                        FString::Printf(TEXT("%s-%s.png"), *UGameplayStatics::GetCurrentLevelName(World, true), bDay ? TEXT("day") : TEXT("night")), true, false);
                    bCapturedDay |= bDay;
                    bCapturedNight |= bNight;
                }
            }
            if (++Phase < 11) return;
            Check(bClockMoved, TEXT("day night clock advances"));
            Check(Weather->IsSkyClockConnected()?bSunDirectionMoved:(MaxSun > MinSun + 1.0f), TEXT("active sky controller changes scene sunlight"));
            UE_LOG(LogTemp, Display, TEXT("WeatherPanelAudit: sun_min=%.3f sun_max=%.3f"), MinSun, MaxSun);
            UE_LOG(LogTemp, Display, TEXT("WEATHER_PANEL_AUDIT_%s map=%s failures=%d"), Failures == 0 ? TEXT("PASS") : TEXT("FAIL"), *UGameplayStatics::GetCurrentLevelName(World, true), Failures);
            World->GetTimerManager().ClearTimer(Timer);
            PC->ConsoleCommand(TEXT("quit"));
        }
    };
}

void StartWeatherPanelValidation(AFPSGAMEPlayerController* Controller, UWeatherControlWidget* Panel)
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("WeatherPanelAudit"))) return;
    auto Audit = MakeShared<FWeatherAudit>();
    Audit->PC = Controller;
    Audit->UI = Panel;
    Controller->GetWorld()->GetTimerManager().SetTimer(Audit->Timer, [Audit]() { Audit->Step(); }, 3.0f, true, 8.0f);
}
