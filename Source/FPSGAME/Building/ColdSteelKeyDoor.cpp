#include "ColdSteelKeyDoor.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const TCHAR* UnlockSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_Unlock.S_Door_Unlock");
    const TCHAR* LockedSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_LockedJiggle.S_Door_LockedJiggle");
}

AColdSteelKeyDoor::AColdSteelKeyDoor()
{
    // 键门默认不自动关：解锁开门后保持敞开，关门仍可用 E 手动切换。
    AutoCloseSeconds = 0.f;
    static ConstructorHelpers::FObjectFinder<USoundBase> UnlockAsset(UnlockSoundPath);
    static ConstructorHelpers::FObjectFinder<USoundBase> LockedAsset(LockedSoundPath);
    if(UnlockAsset.Succeeded())UnlockSound=UnlockAsset.Object;
    if(LockedAsset.Succeeded())LockedSound=LockedAsset.Object;
}

void AColdSteelKeyDoor::MulticastKeySound_Implementation(bool bUnlock)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Sound=bUnlock?UnlockSound.Get():LockedSound.Get())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,GetActorLocation());
}

void AColdSteelKeyDoor::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelKeyDoor, bUnlocked);
}

void AColdSteelKeyDoor::OnRep_Unlocked()
{
    UE_LOG(LogTemp, Display, TEXT("ColdSteelKeyDoor %s 解锁状态同步=%d"), *GetName(), bUnlocked ? 1 : 0);
}

bool AColdSteelKeyDoor::OpenDoorFrom(const APawn* InstigatorPawn)
{
    if(HasAuthority() && !bUnlocked)
    {
        const auto* Player = Cast<AFPSGAMECharacter>(InstigatorPawn);
        // E 与撞门链路都汇到这里：没钥匙一律拒绝，锁纹丝不动（播放把手晃动声）。
        if(!Player || !Player->HasDoorKey(KeyId))
        {
            MulticastKeySound(false);
            UE_LOG(LogTemp, Display, TEXT("ColdSteelKeyDoor %s 上锁，操作者无钥匙（%s），拒绝开门"), *GetName(), *KeyId.ToString());
            return false;
        }
        bUnlocked = true;
        MulticastKeySound(true);
        UE_LOG(LogTemp, Display, TEXT("ColdSteelKeyDoor %s 已用钥匙（%s）解锁"), *GetName(), *KeyId.ToString());
    }
    return Super::OpenDoorFrom(InstigatorPawn);
}
