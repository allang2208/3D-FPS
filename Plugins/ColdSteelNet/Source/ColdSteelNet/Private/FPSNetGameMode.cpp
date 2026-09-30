#include "FPSNetGameMode.h"
#include "ColdSteelNetLog.h"

#include "EngineUtils.h"
#include "GameFramework/GameSession.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/PlayerState.h"

#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"

AFPSNetGameMode::AFPSNetGameMode()
{
    DefaultPawnClass = AFPSGAMECharacter::StaticClass();
    PlayerControllerClass = AFPSGAMEPlayerController::StaticClass();
    // M4 传送门换 seamless travel 的前置开关；当前硬旅行路径不受影响。
    bUseSeamlessTravel = true;
}

void AFPSNetGameMode::BeginPlay()
{
    Super::BeginPlay();

    const UWorld* World = GetWorld();
    UE_LOG(LogColdSteelNet, Warning,
        TEXT("MPTEST NetGameMode active: World=%s NetMode=%d"),
        World ? *World->GetName() : TEXT("<null>"),
        static_cast<int32>(GetNetMode()));

    if (GameSession)
    {
        // M1 冒烟规模；正式上限随 M6 会话系统定。
        GameSession->MaxPlayers = 4;
        UE_LOG(LogColdSteelNet, Log, TEXT("NetGameMode MaxPlayers=%d"), GameSession->MaxPlayers);
    }
}

AActor* AFPSNetGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
    // 重生复用原点位，避免死亡重生把出生点让给别人又收回来。
    if (const TWeakObjectPtr<APlayerStart>* Found = ClaimedStarts.Find(Player))
    {
        if (APlayerStart* Claimed = Found->Get())
        {
            UE_LOG(LogColdSteelNet, Log, TEXT("PlayerStart reuse '%s' -> %s"),
                *Claimed->GetName(), *GetNameSafe(Player));
            return Claimed;
        }
    }

    TArray<APlayerStart*> Starts;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        Starts.Add(*It);
    }

    if (Starts.Num() == 0)
    {
        UE_LOG(LogColdSteelNet, Warning, TEXT("No PlayerStart in level; falling back to engine default"));
        return Super::ChoosePlayerStart(Player);
    }

    TSet<APlayerStart*> Occupied;
    for (const TPair<TWeakObjectPtr<AController>, TWeakObjectPtr<APlayerStart>>& Pair : ClaimedStarts)
    {
        if (APlayerStart* Taken = Pair.Value.Get())
        {
            Occupied.Add(Taken);
        }
    }

    for (APlayerStart* Candidate : Starts)
    {
        if (!Occupied.Contains(Candidate))
        {
            ClaimedStarts.Add(Player, Candidate);
            UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST PlayerStart '%s' assigned to %s"),
                *Candidate->GetName(), *GetNameSafe(Player));
            return Candidate;
        }
    }

    // 满员回退：轮转错开，至少不叠在同一坐标。
    APlayerStart* Fallback = Starts[NextStartIndex % Starts.Num()];
    ++NextStartIndex;
    UE_LOG(LogColdSteelNet, Warning,
        TEXT("MPTEST PlayerStart exhausted (%d claimed), round-robin fallback '%s' -> %s"),
        ClaimedStarts.Num(), *Fallback->GetName(), *GetNameSafe(Player));
    return Fallback;
}

void AFPSNetGameMode::PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST PreLogin enter: addr=%s"), *Address);
    Super::PreLogin(Options, Address, UniqueId, ErrorMessage);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST PreLogin exit: error='%s'"), *ErrorMessage);
}

APlayerController* AFPSNetGameMode::Login(UPlayer* NewPlayer, ENetRole InRemoteRole, const FString& Portal, const FString& Options, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST Login enter"));
    APlayerController* PC = Super::Login(NewPlayer, InRemoteRole, Portal, Options, UniqueId, ErrorMessage);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST Login exit: PC=%s err='%s'"), *GetNameSafe(PC), *ErrorMessage);
    return PC;
}

void AFPSNetGameMode::RestartPlayer(AController* NewPlayer)
{
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST RestartPlayer enter: %s"), *GetNameSafe(NewPlayer));
    // 轻量测试图可能没有摆 PlayerStart：兜底在世界原点上方生成，别让联机冒烟断在缺出生点。
    bool bHasPlayerStart = false;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        bHasPlayerStart = true;
        break;
    }
    if (!bHasPlayerStart)
    {
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST No PlayerStart in level; origin+250 fallback"));
        RestartPlayerAtTransform(NewPlayer, FTransform(FVector(0.f, 0.f, 250.f)));
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST RestartPlayer exit(fallback): pawn=%s"), *GetNameSafe(NewPlayer ? NewPlayer->GetPawn() : nullptr));
        return;
    }
    Super::RestartPlayer(NewPlayer);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST RestartPlayer exit: pawn=%s"), *GetNameSafe(NewPlayer ? NewPlayer->GetPawn() : nullptr));
}

void AFPSNetGameMode::PostLogin(APlayerController* NewPlayer)
{
    Super::PostLogin(NewPlayer);

    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST PostLogin: PC=%s PlayerState=%s NumPlayers=%d NetMode=%d"),
        *GetNameSafe(NewPlayer),
        NewPlayer && NewPlayer->PlayerState ? *NewPlayer->PlayerState->GetName() : TEXT("<none>"),
        GetNumPlayers(),
        static_cast<int32>(GetNetMode()));
}

void AFPSNetGameMode::Logout(AController* Exiting)
{
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST Logout: %s (remaining=%d)"),
        *GetNameSafe(Exiting), GetNumPlayers() > 0 ? GetNumPlayers() - 1 : 0);

    ClaimedStarts.Remove(Exiting);
    Super::Logout(Exiting);
}
