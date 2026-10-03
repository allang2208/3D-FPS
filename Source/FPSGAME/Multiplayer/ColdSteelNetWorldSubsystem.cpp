#include "ColdSteelNetWorldSubsystem.h"
#include "ColdSteelPlayerState.h"
#include "Engine/World.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Misc/Crc.h"

namespace
{
    // 客人档案槽名：按玩家名做文件名安全化 + CRC 后缀（与原 NetGameMode 口径一致，
    // 存量 ColdSteelMP_*.sav 客人档可直接载回）。
    FString BuildGuestSlotName(const APlayerController* PC)
    {
        FString Key;
        if (const APlayerState* State = PC ? PC->PlayerState : nullptr)
        {
            Key = State->GetPlayerName();
        }
        if (Key.IsEmpty())
        {
            Key = TEXT("Guest");
        }
        FString Safe;
        for (const TCHAR C : Key)
        {
            if (FChar::IsAlnum(C))
            {
                Safe.AppendChar(C);
            }
        }
        if (Safe.IsEmpty())
        {
            Safe = TEXT("Guest");
        }
        return FString::Printf(TEXT("ColdSteelMP_%s_%08x"), *Safe, FCrc::StrCrc32(*Key));
    }
}

bool UColdSteelNetWorldSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    const UWorld* World = Cast<UWorld>(Outer);
    return World && World->IsGameWorld();
}

void UColdSteelNetWorldSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    PostLoginHandle = FGameModeEvents::OnGameModePostLoginEvent().AddUObject(this, &UColdSteelNetWorldSubsystem::OnPostLogin);
    LogoutHandle = FGameModeEvents::OnGameModeLogoutEvent().AddUObject(this, &UColdSteelNetWorldSubsystem::OnLogout);
}

void UColdSteelNetWorldSubsystem::Deinitialize()
{
    FGameModeEvents::OnGameModePostLoginEvent().Remove(PostLoginHandle);
    FGameModeEvents::OnGameModeLogoutEvent().Remove(LogoutHandle);
    Super::Deinitialize();
}

void UColdSteelNetWorldSubsystem::OnPostLogin(AGameModeBase* GameMode, APlayerController* NewPlayer)
{
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Standalone || !NewPlayer) return;
    // FGameModeEvents 是进程级广播：PIE 同进程多实例下，客户端子系统也会收到
    // 服务器 GameMode 的登录事件——必须过滤只处理本世界的登录。
    if (!GameMode || GameMode->GetWorld() != World) return;
    // 本机玩家（监听服主机）不挂影子档案——它的权威档案就是 GameInstance 单例。
    if (NewPlayer->IsLocalController()) return;
    if (AColdSteelPlayerState* PS = NewPlayer->GetPlayerState<AColdSteelPlayerState>())
    {
        PS->InitializeGuest(BuildGuestSlotName(NewPlayer));
        UE_LOG(LogTemp, Warning, TEXT("MPTEST guest initialized via world subsystem: %s"), *GetNameSafe(PS));
    }
}

void UColdSteelNetWorldSubsystem::OnLogout(AGameModeBase* GameMode, AController* Exiting)
{
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Standalone || !Exiting) return;
    if (GameMode && GameMode->GetWorld() != World) return;
    if (AColdSteelPlayerState* PS = Exiting->GetPlayerState<AColdSteelPlayerState>())
    {
        // 玩家离开时把影子档案立即落盘（正常节流靠 bServerDirty，这里抢在销毁前）。
        PS->SaveShadowToHostDisk();
    }
}
