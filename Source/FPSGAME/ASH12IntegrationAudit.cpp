#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Weapons/ASH12WeaponAssets.h"

// Still capture for the ASH-12 viewmodel: hip frame, then iron-sight ADS at
// several eye reliefs, so the shipped framing can be judged from real frames
// instead of a reconstruction.
void AFPSGAMECharacter::RunASH12IntegrationAudit()
{
    auto* P=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    auto* PC=Cast<APlayerController>(Controller);
    if(!P||!PC||!P->ProfileSlot().Contains(TEXT("ASH12SightAudit"))||GetWorld()->GetTimeSeconds()<5)return;
    static int Stage=0;static double At=0;static int32 BeatIndex=0;
    static const float EyeReliefs[]={12.f,18.f,24.f};
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("ASH12Run="),Run);Run=FPaths::MakeValidFileName(Run);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("ASH12SightAudit")/Run;
    const double Now=GetWorld()->GetTimeSeconds();
    auto Capture=[&](const TCHAR* Name)
    {
        const FString File=Out/Name;
        UE_LOG(LogTemp,Display,TEXT("ASH12_SIGHT_CAPTURE mesh=%s aim=%s alpha=%.6f eye=%.2f output=%s"),
            *GetPathNameSafe(AKMViewmodel?AKMViewmodel->GetSkeletalMeshAsset():nullptr),
            *GetPathNameSafe(AimAnimation),WeaponADSFactor,ADSRearEyeDistance,*File);
        FScreenshotRequest::RequestScreenshot(File,false,false);
    };
    auto Aim=[&](bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,Down?IE_Pressed:IE_Released,Down?1:0));};
    if(Stage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto Rifle=P->CreateItem(TEXT("ue_ash12"));Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=20;S.Items.Add(Rifle);
        auto Ammo=P->CreateItem(TEXT("ammo_127"),120);if(!Ammo.Data.IsEmpty())S.Items.Add(Ammo);
        if(!P->CommitState(S)){UE_LOG(LogTemp,Error,TEXT("ASH12_SIGHT_CAPTURE could not equip the fixture"));PC->ConsoleCommand(TEXT("quit"));return;}
        ADSRearEyeDistance=EyeReliefs[0];bSightCalibrated=false;
        Stage=1;At=Now;
    }
    else if(Stage==1&&!IsWeaponBusy()&&Now-At>1.5){Capture(TEXT("ASH12-hip.png"));Stage=2;At=Now;}
    else if(Stage==2&&Now-At>0.5){Aim(true);Stage=3;At=Now;}
    else if(Stage>=3&&Stage<=5&&Now-At>2.0)
    {
        const int32 Index=Stage-3;
        Capture(*FString::Printf(TEXT("ASH12-ADS-eye%02d.png"),int32(EyeReliefs[Index])));
        if(Index+1<UE_ARRAY_COUNT(EyeReliefs))
        {
            ADSRearEyeDistance=EyeReliefs[Index+1];bSightCalibrated=false;
            Stage+=1;At=Now;
        }
        else
        {
            // Same aim, shared holographic sight, so an optic complaint can be
            // told apart from an iron-sight one.
            SetGunsmithOpticVariant(TEXT("holographic"));
            Stage=6;At=Now;
        }
    }
    else if(Stage==6&&Now-At>2.0){Capture(TEXT("ASH12-ADS-optic.png"));SetGunsmithOpticVariant(TEXT("false"));Aim(false);Stage=7;At=Now;}
    else if(Stage==7&&Now-At>1.0)
    {
        // Reproduce the states a player actually aims in: walking while aimed,
        // then a burst. A settled still cannot tell those apart from the build.
        Aim(true);Stage=8;At=Now;
    }
    else if(Stage==8&&Now-At>1.5)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Pressed,1.0f));
        Stage=9;At=Now;
    }
    else if(Stage==9&&Now-At>1.2){Capture(TEXT("ASH12-ADS-walk.png"));Stage=10;At=Now;}
    else if(Stage==10&&Now-At>0.3)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.0f));
        Stage=11;At=Now;
    }
    else if(Stage==11&&Now-At>0.45){Capture(TEXT("ASH12-ADS-burst.png"));Stage=12;At=Now;}
    else if(Stage==12&&Now-At>0.3)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.0f));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Released,0.0f));
        Aim(false);Stage=13;At=Now;
    }
    else if(Stage==13&&Now-At>1.0){bGunsmithInspection=true;Stage=14;At=Now;}
    else if(Stage==14&&Now-At>1.5){Capture(TEXT("ASH12-closeup.png"));bGunsmithInspection=false;Stage=15;At=Now;}
    else if(Stage==15&&Now-At>0.6)
    {
        // Empty the magazine so the reload that follows is the empty one, then
        // drive it with the same key a player presses. Captures land on the
        // frames the runtime fires its mechanical cues on (21/60, 54/60, 80/60,
        // 130/60 of the 2.7 s clip), plus the pull-out beat.
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto Rifle=P->CreateItem(TEXT("ue_ash12"));Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=0;S.Items.Add(Rifle);
        auto Ammo=P->CreateItem(TEXT("ammo_127"),120);if(!Ammo.Data.IsEmpty())S.Items.Add(Ammo);
        if(!P->CommitState(S))UE_LOG(LogTemp,Error,TEXT("ASH12_RELOAD_CAPTURE could not empty the rifle"));
        Stage=16;At=Now;
    }
    else if(Stage==16&&Now-At>1.0)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1.0f));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0.0f));
        UE_LOG(LogTemp,Display,TEXT("ASH12_RELOAD_CAPTURE key=R source_time=%.4f"),ReloadSourceTime(WeaponStateElapsed));
        Stage=17;At=Now;BeatIndex=0;
    }
    else if(Stage==17)
    {
        static const float Beats[]={0.35f,0.70f,0.90f,1.33f,2.17f};
        const double Since=Now-At;
        if(BeatIndex<int32(UE_ARRAY_COUNT(Beats))&&Since>=Beats[BeatIndex])
        {
            UE_LOG(LogTemp,Display,TEXT("ASH12_RELOAD_CAPTURE beat=%.2f source_time=%.4f"),
                Beats[BeatIndex],ReloadSourceTime(WeaponStateElapsed));
            Capture(*FString::Printf(TEXT("ASH12-reload-t%03d.png"),int32(Beats[BeatIndex]*100)));
            ++BeatIndex;
        }
        else if(BeatIndex>=int32(UE_ARRAY_COUNT(Beats))&&Since>3.6)Stage=20;
    }
    else if(Stage==20){PC->ConsoleCommand(TEXT("quit"));}
}
