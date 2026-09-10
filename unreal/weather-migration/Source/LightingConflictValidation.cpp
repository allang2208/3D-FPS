#include "LightingConflictValidation.h"
#include "FPSWeatherManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/GameViewportClient.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "TimerManager.h"

void StartLightingConflictValidation(AFPSWeatherManager* Weather)
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("LightingAudit"))) return;
    const TWeakObjectPtr<AFPSWeatherManager> WeakWeather(Weather);
    FTimerHandle Snapshot;
    Weather->GetWorld()->GetTimerManager().SetTimer(Snapshot, [WeakWeather]()
    {
        if (!WeakWeather.IsValid()) return;
        UWorld* World = WeakWeather->GetWorld();
        int32 ActiveDirectional = 0, ActiveSky = 0, TopPriority = MIN_int32, TopCount = 0;
        TSet<int32> AtmosphereIndices;
        bool bAtmosphereConflict = false;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            for (ULightComponentBase* Light : TInlineComponentArray<ULightComponentBase*>(*It))
            {
                auto* Directional = Cast<UDirectionalLightComponent>(Light);
                auto* Sky = Cast<USkyLightComponent>(Light);
                if (!Directional && !Sky) continue;
                const bool Active = Light->IsRegistered() && Light->IsVisible() && Light->bAffectsWorld && !It->IsHidden() && Light->Intensity > 0;
                UE_LOG(LogTemp, Display, TEXT("LightingAudit: light=%s active=%d intensity=%.4f priority=%d atmosphere=%d index=%d"),
                    *Light->GetPathName(), Active, Light->Intensity, Directional ? Directional->ForwardShadingPriority : -1,
                    Directional ? Directional->bAtmosphereSunLight : false, Directional ? Directional->AtmosphereSunLightIndex : -1);
                if (Active && Sky) ++ActiveSky;
                if (Active && Directional)
                {
                    ++ActiveDirectional;
                    if (Directional->bAtmosphereSunLight)
                    {
                        bAtmosphereConflict |= AtmosphereIndices.Contains(Directional->AtmosphereSunLightIndex);
                        AtmosphereIndices.Add(Directional->AtmosphereSunLightIndex);
                    }
                    if (Directional->ForwardShadingPriority > TopPriority) { TopPriority = Directional->ForwardShadingPriority; TopCount = 1; }
                    else if (Directional->ForwardShadingPriority == TopPriority) ++TopCount;
                }
            }
        }
        for (ULevel* Level : World->GetLevels())
            UE_LOG(LogTemp, Display, TEXT("LightingAudit: level=%s"), *Level->GetPathName());
        const int32 ExpectedDirectional = UGameplayStatics::GetCurrentLevelName(World, true) == TEXT("L_M4RigValidation") ? 2 : 1;
        UE_LOG(LogTemp, Display, TEXT("LIGHTING_AUDIT_%s map=%s directional=%d skylights=%d top_count=%d clock=%d scene=%d atmosphere_conflict=%d"),
            ActiveDirectional == ExpectedDirectional && ActiveSky == 1 && TopCount == 1 && !bAtmosphereConflict ? TEXT("PASS") : TEXT("FAIL"),
            *UGameplayStatics::GetCurrentLevelName(World, true), ActiveDirectional, ActiveSky, TopCount,
            WeakWeather->IsSkyClockConnected(), WeakWeather->IsSceneDayNightActive(), bAtmosphereConflict);
        FString Label(TEXT("snapshot"));
        FParse::Value(FCommandLine::Get(), TEXT("LightingLabel="), Label);
        const FString Dir = FPaths::ProjectSavedDir() / TEXT("LightingAudit");
        IFileManager::Get().MakeDirectory(*Dir, true);
        FScreenshotRequest::RequestScreenshot(Dir / (UGameplayStatics::GetCurrentLevelName(World, true) + TEXT("-") + Label + TEXT(".png")), true, false);
        FTimerHandle Quit;
        World->GetTimerManager().SetTimer(Quit, []() { FPlatformMisc::RequestExit(false); }, 3.0f, false);
    }, 10.0f, false);
}
