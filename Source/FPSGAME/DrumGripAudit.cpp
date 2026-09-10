#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Animation/AnimSequence.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"

void AFPSGAMECharacter::RunDrumGripAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* PC=Cast<APlayerController>(Controller);
    if(!P||!PC||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("DrumGripAudit")))return;
    auto Check=[this](bool OK,const TCHAR* Name){if(!OK)++DrumGripAuditFailures;UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    FString CaptureRun;
    FParse::Value(FCommandLine::Get(), TEXT("DrumGripCaptureRun="), CaptureRun);
    CaptureRun=FPaths::MakeValidFileName(CaptureRun);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("DrumGripAudit")/CaptureRun;
    if(GetWorld()->GetTimeSeconds()<5)return;
    if(DrumGripAuditStage==0)
    {
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(TEXT("ue_m4a1"));W.Place=1;W.Cell=9;W.Magazine=17;S.Items.Add(W);S.ActiveWeaponSlot=9;
        auto Ammo=P->CreateItem(TEXT("ammo_556"));Ammo.Place=0;Ammo.Cell=0;Ammo.Count=Ammo.StackMax;S.Items.Add(Ammo);
        Check(P->CommitState(S),TEXT("isolated M4 profile"));
        Check(DrumReloadAnimation&&DrumReloadAnimation->GetPathName().Contains(TEXT("/M4DrumDrop/"))&&DrumReloadEmptyAnimation,TEXT("drop reload default clips loaded"));
        Check(DrumSupportAnimations.Num()==5,TEXT("drum support clips loaded"));
        for(const auto& Pair:DrumSupportAnimations)Check(FMath::IsNearlyEqual(Pair.Key->GetPlayLength(),Pair.Value->GetPlayLength(),.0001f),TEXT("support clip timing preserved"));
        UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: ACTIVE %s"),DrumReloadAnimation?*DrumReloadAnimation->GetPathName():TEXT("missing"));
        IFileManager::Get().MakeDirectory(*Out,true);DrumGripAuditStage=10;return;
    }
    if(IsReloading())
    {
        const float RightDepth=FirstPersonCamera->GetComponentTransform().InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("hand_r"))).X;
        DrumGripAuditRightDepthMin=FMath::Min(DrumGripAuditRightDepthMin,RightDepth);
        DrumGripAuditRightDepthMax=FMath::Max(DrumGripAuditRightDepthMax,RightDepth);
        if(DrumGripAuditCapture==0)Check(true,bPendingEmptyReload?TEXT("empty reload input accepted"):TEXT("normal reload input accepted"));
        if(WeaponStateElapsed-DrumGripAuditLastCapture>=1.0f/30.0f)
        {
            DrumGripAuditLastCapture=WeaponStateElapsed;
            UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: FRAME clip=%s index=%d elapsed=%.6f"),bPendingEmptyReload?TEXT("empty"):TEXT("normal"),DrumGripAuditCapture,WeaponStateElapsed);
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("%s_%03d.png"),bPendingEmptyReload?TEXT("empty"):TEXT("normal"),DrumGripAuditCapture++),true,false);
            Check(ValidateDrumAttachment(),TEXT("animated drum attachment"));
        }
        return;
    }
    if(IsWeaponBusy())return;
    if(DrumGripAuditStage==10)
    {
        Check(G->Begin(P->Equipped()->InstanceId)&&G->Select(TEXT("magazine"),TEXT("large_drum"))&&G->Apply(),TEXT("install large drum through profile"));G->Close();
        DrumGripAuditStage=1;return;
    }
    if(DrumGripAuditStage==1||DrumGripAuditStage==3)
    {
        const bool Empty=DrumGripAuditStage==3;
        auto S=P->Snapshot();for(auto& I:S.Items){if(I.Place==1&&I.Cell==S.ActiveWeaponSlot)I.Magazine=Empty?0:17;if(I.Place==0&&I.Definition==TEXT("ammo_556"))I.Count=I.StackMax;}
        P->CommitState(S);DrumGripAuditReserve=P->AmmoCount();DrumGripAuditLastCapture=-1;DrumGripAuditCapture=0;
        DrumGripAuditRightDepthMin=MAX_flt;DrumGripAuditRightDepthMax=-MAX_flt;
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1));PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0));
        ++DrumGripAuditStage;return;
    }
    if(DrumGripAuditStage==2||DrumGripAuditStage==4)
    {
        Check(MagazineAmmo==MagazineCapacity&&MagazineCapacity==50,TEXT("fills 50 round drum"));
        const int32 Expected=HasInfiniteReserveAmmo()?DrumGripAuditReserve:DrumGripAuditReserve-(DrumGripAuditStage==2?33:50);
        Check(P->AmmoCount()==Expected,TEXT("ammo accounting preserved"));
        Check(ValidateDrumAttachment(),TEXT("attachment stable after reload"));
        Check(DrumDropCount==(DrumGripAuditStage==2?1:2),TEXT("one physical old drum per reload"));
        Check(LastDroppedDrum.IsValid()&&LastDroppedDrum->GetActorLocation().Z<LastDrumDropStart.Z-10.0f,TEXT("released drum falls independently"));
        Check(LastDroppedDrum.IsValid()&&FVector::DotProduct(LastDroppedDrum->GetActorLocation()-LastDrumDropStart,FirstPersonCamera->GetRightVector())<-25.0f,TEXT("old drum thrown sideways"));
        UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: right grip depth range=%.4f cm"),DrumGripAuditRightDepthMax-DrumGripAuditRightDepthMin);
        // Allow the authored small sway; reject the former 14 cm action shift.
        Check(DrumGripAuditRightDepthMax-DrumGripAuditRightDepthMin<2.0f,TEXT("no large fore-aft grip excursion"));
        ++DrumGripAuditStage;
        if(DrumGripAuditStage==5){UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: COMPLETE failures=%d"),DrumGripAuditFailures);PC->ConsoleCommand(TEXT("quit"));}
    }
}
