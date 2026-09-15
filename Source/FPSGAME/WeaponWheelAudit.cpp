#include "FPSGAMEPlayerController.h"
#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

// Explicit opt-in in an isolated profile. Uses the actual virtual InputKey path.
void RunWeaponWheelAudit(AFPSGAMEPlayerController* Owner)
{
    auto* Profile=Owner->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||!Profile->IsAudit()||!Profile->ProfileSlot().Contains(TEXT("WeaponWheelAudit")))return;
    auto Failures=MakeShared<int32>(0);
    auto Check=[Failures](bool Pass,const TCHAR* Label)
    {
        if(!Pass)++*Failures;
        UE_LOG(LogTemp,Display,TEXT("WEAPON_WHEEL: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Label);
    };
    auto State=Profile->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    auto AKM=Profile->CreateItem(TEXT("ue_akm"));AKM.Place=1;AKM.Cell=6;AKM.Magazine=12;State.Items.Add(AKM);
    auto M4=Profile->CreateItem(TEXT("ue_m4a1"));M4.Place=1;M4.Cell=9;M4.Magazine=17;State.Items.Add(M4);State.ActiveWeaponSlot=6;
    Check(Profile->CommitState(State),TEXT("isolated AKM and M4 equipped"));
    APlayerController* PC=Owner;
    auto Input=[PC](FKey Key,EInputEvent Event=IE_Pressed){PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key,Event,Event==IE_Released?0.f:1.f));};
    auto Verify=[Profile,PC,Check](int32 Slot,int32 Ammo,const TCHAR* Label)
    {
        auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());
        Check(Profile->Snapshot().ActiveWeaponSlot==Slot&&Pawn&&Pawn->HasInventoryWeapon()&&Pawn->GetMagazineAmmo()==Ammo,Label);
    };
    const FString Out=FPaths::ProjectSavedDir()/TEXT("WeaponWheel20260910");IFileManager::Get().MakeDirectory(*Out,true);
    for(int32 Step=0;Step<11;++Step)
    {
        FTimerHandle Timer;
        Owner->GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(Owner,[=]()
        {
            switch(Step)
            {
            case 0: Input(EKeys::MouseScrollUp);Verify(9,17,TEXT("wheel up switches to M4"));break;
            case 1: FScreenshotRequest::RequestScreenshot(Out/TEXT("wheel-up-M4.png"),true,false);break;
            case 2: Input(EKeys::MouseScrollDown);Verify(6,12,TEXT("wheel down switches to AKM"));break;
            case 3: FScreenshotRequest::RequestScreenshot(Out/TEXT("wheel-down-AKM.png"),true,false);break;
            case 4:
                Input(EKeys::MouseScrollDown);Verify(9,17,TEXT("same direction toggles back"));
                Input(EKeys::MouseScrollDown,IE_Repeat);Input(EKeys::MouseScrollDown,IE_Released);
                Verify(9,17,TEXT("repeat and release do not double toggle"));break;
            case 5: Input(EKeys::MouseScrollUp);Verify(6,12,TEXT("both magazines retained"));Input(EKeys::Tab);break;
            case 6:
                Input(EKeys::MouseScrollUp);Verify(6,12,TEXT("inventory wheel up does not switch weapon"));
                Input(EKeys::MouseScrollDown);Verify(6,12,TEXT("inventory wheel down does not switch weapon"));
                Input(EKeys::Tab,IE_Released);Input(EKeys::Tab);break;
            case 7: Input(EKeys::G);Verify(9,17,TEXT("G shortcut preserved after closing inventory"));break;
            case 8:
            {
                auto Single=Profile->Snapshot();Single.Items.RemoveAll([](const auto& I){return I.Place==1&&I.Cell==6;});
                Check(Profile->CommitState(Single),TEXT("empty other slot fixture"));
                Input(EKeys::MouseScrollUp);Verify(9,17,TEXT("wheel up keeps weapon when other slot empty"));
                Input(EKeys::MouseScrollDown);Verify(9,17,TEXT("wheel down keeps weapon when other slot empty"));break;
            }
            case 10:
                UE_LOG(LogTemp,Display,TEXT("WEAPON_WHEEL: COMPLETE failures=%d"),*Failures);
                FPlatformMisc::RequestExitWithStatus(false,*Failures?1:0);break;
            }
        }),.1f+Step*1.f,false);
    }
}
