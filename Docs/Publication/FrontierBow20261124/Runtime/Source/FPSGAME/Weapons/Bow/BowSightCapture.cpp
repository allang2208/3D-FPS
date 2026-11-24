// Explicit, isolated screenshot fixture. No normal-play registration or tick.
#include "BowWeaponComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Containers/Ticker.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformTime.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

#if WITH_EDITOR
namespace
{
FAutoConsoleCommandWithWorld BowSightCapture(
    TEXT("fps.Bow.CaptureSight"), TEXT("Capture current bow in a BowSightCaptureAudit profile; exits the isolated game."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
    {
        FString ProfileName;
        FParse::Value(FCommandLine::Get(), TEXT("ColdSteelProfile="), ProfileName);
        if ((!World || !World->IsGameWorld()) && GEngine)
            for (const auto& Context:GEngine->GetWorldContexts())
                if (Context.World() && Context.World()->IsGameWorld()) { World=Context.World(); break; }
        if (!World || !World->IsGameWorld() || !ProfileName.StartsWith(TEXT("BowSightCaptureAudit"))) return;
        UE_LOG(LogTemp,Display,TEXT("BOW_SIGHT_CAPTURE_START world=%s profile=%s"),*World->GetName(),*ProfileName);
        struct FRun { int32 Phase=0; double Started=FPlatformTime::Seconds(); float Next=0; FString Out, Record; };
        auto Run=MakeShared<FRun>();
        Run->Out=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("BowRingSight20260927")/ProfileName);
        IFileManager::Get().MakeDirectory(*Run->Out,true);
        const TWeakObjectPtr<UWorld> WeakWorld(World);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run,WeakWorld](float)
        {
            UWorld* W=WeakWorld.Get();
            if (!W) return false;
            if (FPlatformTime::Seconds()-Run->Started>150.)
            { UE_LOG(LogTemp,Error,TEXT("BOW_SIGHT_CAPTURE timeout")); FPlatformMisc::RequestExitWithStatus(false,1); return false; }
            auto* PC=W->GetFirstPlayerController();
            auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
            auto* Profile=W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
            if (!Character || !Profile || !Profile->IsAudit() || W->GetTimeSeconds()<3.f) return true;
            auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>();
            if (!Bow) return true;
            const float Now=W->GetTimeSeconds();
            const auto Input=[PC](FKey Key,EInputEvent Event=IE_Pressed)
            { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key,Event,Event==IE_Released?0.f:1.f)); };
            const auto Capture=[&](const TCHAR* Name)
            {
                const auto* Cam=Character->FindComponentByClass<UCameraComponent>();
                const FString Line=FString::Printf(TEXT("%s stage=%d draw=%.4f aim=%.4f sight=%s fov=%.2f\n"),Name,
                    static_cast<int32>(Bow->GetStage()),Bow->DrawFraction(),Bow->AimAlpha(),
                    *Bow->PartMeshPath(TEXT("sight")),Cam?Cam->FieldOfView:0.f);
                Run->Record+=Line;
                UE_LOG(LogTemp,Display,TEXT("BOW_SIGHT_CAPTURE %s"),*Line);
                FScreenshotRequest::RequestScreenshot(Run->Out/(FString(Name)+TEXT(".png")),true,false);
            };
            switch(Run->Phase)
            {
            case 0:
            {
                auto State=Profile->Snapshot(); State.Items.Reset(); State.Hotbar.Init(TEXT(""),4); State.HotbarDefinitions.Init(TEXT(""),4);
                auto Item=Profile->CreateItem(TEXT("bow_dark")); Item.Place=1; Item.Cell=9;
                State.Items.Add(Item); State.ActiveWeaponSlot=9; State.AmmoPouch.Add(TEXT("arrow_wood"),30);
                State.Stamina=Profile->MaxStamina();
                if (!Profile->CommitState(State))
                { UE_LOG(LogTemp,Error,TEXT("BOW_SIGHT_CAPTURE fixture rejected")); FPlatformMisc::RequestExitWithStatus(false,1); return false; }
                PC->SetControlRotation(FRotator::ZeroRotator);
                Run->Next=Now+7.f; Run->Phase=1; break;
            }
            case 1:
                if (Now<Run->Next || !Bow->IsEquipped() || Bow->IsBusy()) break;
                Capture(TEXT("01_hip_ready")); Run->Next=Now+.5f; Run->Phase=2; break;
            case 2:
                if (Now<Run->Next) break;
                Input(EKeys::RightMouseButton); Run->Next=Now+1.f; Run->Phase=3; break;
            case 3:
                if (Now<Run->Next || Bow->AimAlpha()<.99f) break;
                Capture(TEXT("02_ads_ready")); Run->Next=Now+.5f; Run->Phase=4; break;
            case 4:
                if (Now<Run->Next) break;
                Input(EKeys::LeftMouseButton); Run->Next=Now+1.9f; Run->Phase=5; break;
            case 5:
                if (Now<Run->Next || Bow->GetStage()!=EBowStage::Holding) break;
                Capture(TEXT("03_ads_full_draw")); Run->Next=Now+.7f; Run->Phase=6; break;
            case 6:
                if (Now<Run->Next) break;
                Input(EKeys::R); Input(EKeys::R,IE_Released); Input(EKeys::LeftMouseButton,IE_Released);
                Input(EKeys::RightMouseButton,IE_Released);
                FFileHelper::SaveStringToFile(Run->Record,*(Run->Out/TEXT("capture.txt")));
                Run->Next=Now+1.f; Run->Phase=7; break;
            default:
                if (Now<Run->Next) break;
                UE_LOG(LogTemp,Display,TEXT("BOW_SIGHT_CAPTURE_COMPLETE %s"),*Run->Out);
                FPlatformMisc::RequestExitWithStatus(false,0); return false;
            }
            return true;
        }));
    }));
}
#endif
