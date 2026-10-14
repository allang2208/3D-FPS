#include "ColdSteelNetConnectSubsystem.h"
#include "ColdSteelNetLog.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/Parse.h"
#include "TimerManager.h"

void UColdSteelNetConnectSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FParse::Value(FCommandLine::Get(), TEXT("MPConnect="), Target);
    float ParsedDelay = 0.f;
    if (FParse::Value(FCommandLine::Get(), TEXT("MPConnectDelay="), ParsedDelay) && ParsedDelay > 0.f)
    {
        Delay = ParsedDelay;
    }
    if (Target.IsEmpty())
    {
        return;
    }
    ArmedAt = FPlatformTime::Seconds();
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST connect armed: target=%s delay=%.0fs"), *Target, Delay);
    // GameInstance 级定时器：不依赖具体世界/GameMode，任何图直开后都会在延迟后连线。
    GetGameInstance()->GetTimerManager().SetTimer(TimerHandle, this, &UColdSteelNetConnectSubsystem::TryConnect, 5.f, true);
}

void UColdSteelNetConnectSubsystem::TryConnect()
{
    if (bConnectIssued)
    {
        GetGameInstance()->GetTimerManager().ClearTimer(TimerHandle);
        return;
    }
    if (FPlatformTime::Seconds() - ArmedAt < Delay)
    {
        return;
    }
    UWorld* World = GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr;
    APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
    if (!World || !PC || World->IsNetMode(NM_DedicatedServer))
    {
        return;
    }
    bConnectIssued = true;
    GetGameInstance()->GetTimerManager().ClearTimer(TimerHandle);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST connect issuing: open %s"), *Target);
    UKismetSystemLibrary::ExecuteConsoleCommand(World, FString::Printf(TEXT("open %s"), *Target), PC);
}
