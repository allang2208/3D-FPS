#include "FPSGAMEGameMode.h"
#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "FPSWeatherManager.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "SceneSpawnValidation.h"
#include "GameFramework/PlayerStart.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Engine.h"
#include "TimerManager.h"

AFPSGAMEGameMode::AFPSGAMEGameMode()
{
    DefaultPawnClass = AFPSGAMECharacter::StaticClass();
    PlayerControllerClass = AFPSGAMEPlayerController::StaticClass();
}

void AFPSGAMEGameMode::RestartPlayer(AController* NewPlayer)
{
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    if (Map != TEXT("DayNight_Lighting") && Map != TEXT("L_Normandy_FPS_Test") && Map != TEXT("L_MilitaryTrench_FPS_Test"))
    {
        Super::RestartPlayer(NewPlayer);
        return;
    }
    if (!IsValid(NewPlayer) || NewPlayer->GetPawn()) return;
    if (Map == TEXT("L_MilitaryTrench_FPS_Test"))
    {
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateUObject(this,
            &AFPSGAMEGameMode::SpawnAfterStreaming, TWeakObjectPtr<AController>(NewPlayer)), .5f, false);
        return;
    }
    SpawnAfterStreaming(NewPlayer);
}

void AFPSGAMEGameMode::SpawnAfterStreaming(TWeakObjectPtr<AController> Player)
{
    AController* NewPlayer = Player.Get();
    if (!NewPlayer || NewPlayer->GetPawn()) return;
    GetWorld()->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        FVector Safe;
        if (!USceneSpawnValidation::FindSafeSpawn(this, It->GetActorLocation(), Safe)) continue;
        // Evaluate after runtime collision is created, not just in the editor.
        RestartPlayerAtTransform(NewPlayer, FTransform(It->GetActorRotation(), Safe));
        if (NewPlayer->GetPawn())
        {
            UE_LOG(LogTemp, Display, TEXT("SceneSpawn: Runtime spawn %s at %s"), *Map, *Safe.ToString());
            return;
        }
    }
    // Never let GameMode's no-start fallback place a character at world origin.
    UE_LOG(LogTemp, Error, TEXT("SceneSpawn: Spawn blocked in %s; no safe start. No pawn spawned."), *Map);
    if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 20.f, FColor::Red, TEXT("No safe spawn found. Return to editor and check PlayerStart/collision."));
}

void AFPSGAMEGameMode::BeginPlay()
{
    Super::BeginPlay();

    // Keep the isolated UI acceptance route independent from world/weather work.
    if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUIAudit")))
    {
        return;
    }

    for (TActorIterator<AFPSWeatherManager> It(GetWorld()); It; ++It)
    {
        return;
    }

    GetWorld()->SpawnActor<AFPSWeatherManager>();
}
