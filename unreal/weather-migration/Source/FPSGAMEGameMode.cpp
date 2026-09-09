#include "FPSGAMEGameMode.h"
#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "FPSWeatherManager.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

AFPSGAMEGameMode::AFPSGAMEGameMode()
{
    DefaultPawnClass = AFPSGAMECharacter::StaticClass();
    PlayerControllerClass = AFPSGAMEPlayerController::StaticClass();
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
