#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/M4DrumReloadTiming.h"
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
#include "AudioMixerBlueprintLibrary.h"

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
    FString MagazineAuditId;
    FParse::Value(FCommandLine::Get(), TEXT("MagazineAudit="), MagazineAuditId);
    if(MagazineAuditId.IsEmpty())MagazineAuditId=TEXT("large_drum");
    const bool bDrumAudit=MagazineAuditId==TEXT("large_drum");
    const FString Out=FPaths::ProjectSavedDir()/TEXT("DrumGripAudit")/CaptureRun;
    if(GetWorld()->GetTimeSeconds()<5)return;
    if(DrumGripAuditStage==0)
    {
        FString AuditWeapon;
        FParse::Value(FCommandLine::Get(), TEXT("AuditWeapon="), AuditWeapon);
        if(AuditWeapon!=TEXT("ue_akm")&&AuditWeapon!=TEXT("ue_qbz191"))AuditWeapon=TEXT("ue_m4a1");
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(AuditWeapon);W.Place=1;W.Cell=9;W.Magazine=17;S.Items.Add(W);S.ActiveWeaponSlot=9;
        auto Ammo=P->CreateItem(TEXT("ammo_556"));Ammo.Place=0;Ammo.Cell=0;Ammo.Count=Ammo.StackMax;S.Items.Add(Ammo);
        Check(P->CommitState(S),TEXT("isolated M4 profile"));
        if(bDrumAudit){
        Check(DrumReloadAnimation&&DrumReloadAnimation->GetPathName().Contains(TEXT("/M4DrumDrop/Contact/"))&&DrumReloadEmptyAnimation&&DrumReloadEmptyAnimation->GetPathName().Contains(TEXT("/M4DrumDrop/Contact/")),TEXT("contact-corrected reload default clips loaded"));
        Check(DrumReloadAnimation&&DrumReloadEmptyAnimation&&FMath::IsNearlyEqual(DrumReloadAnimation->GetPlayLength(),2.1f,.001f)&&FMath::IsNearlyEqual(DrumReloadEmptyAnimation->GetPlayLength(),148.f/60.f,.001f),TEXT("revised animation lengths match event clock"));}
        if(FParse::Param(FCommandLine::Get(),TEXT("DrumCaptureAudio")))
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this,20.0f);
        if(bDrumAudit){
        Check(DrumSupportAnimations.Num()==5,TEXT("drum support clips loaded"));
        for(const auto& Pair:DrumSupportAnimations)Check(FMath::IsNearlyEqual(Pair.Key->GetPlayLength(),Pair.Value->GetPlayLength(),.0001f),TEXT("support clip timing preserved"));
        }
        UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: ACTIVE %s"),DrumReloadAnimation?*DrumReloadAnimation->GetPathName():TEXT("missing"));
        IFileManager::Get().MakeDirectory(*Out,true);DrumGripAuditStage=10;return;
    }
    if(IsReloading())
    {
        DrumGripAuditReloadDuration=WeaponStateDuration;
        const float RightDepth=FirstPersonCamera->GetComponentTransform().InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("hand_r"))).X;
        DrumGripAuditRightDepthMin=FMath::Min(DrumGripAuditRightDepthMin,RightDepth);
        DrumGripAuditRightDepthMax=FMath::Max(DrumGripAuditRightDepthMax,RightDepth);
        // Compare the two configurations with identical feedback and camera state.
        // A bare framing position excludes bob, recoil and near-wall attenuation.
        const FVector DrumLocation=AKMViewmodel->GetRelativeLocation();
        bDrumInstalled=false;
        UpdateViewmodel(0.0f);
        const float ExpectedDepth=AKMViewmodel->GetRelativeLocation().X;
        bDrumInstalled=true;
        AKMViewmodel->SetRelativeLocation(DrumLocation);
        DrumGripAuditFramingMaxError=FMath::Max(DrumGripAuditFramingMaxError,FMath::Abs(AKMViewmodel->GetRelativeLocation().X-ExpectedDepth));
        if(DrumGripAuditCapture==0)Check(true,bPendingEmptyReload?TEXT("empty reload input accepted"):TEXT("normal reload input accepted"));
        if(WeaponStateElapsed-DrumGripAuditLastCapture>=1.0f/30.0f)
        {
            DrumGripAuditLastCapture=WeaponStateElapsed;
            UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: FRAME clip=%s index=%d elapsed=%.6f"),bPendingEmptyReload?TEXT("empty"):TEXT("normal"),DrumGripAuditCapture,WeaponStateElapsed);
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("%s_%03d.png"),bPendingEmptyReload?TEXT("empty"):TEXT("normal"),DrumGripAuditCapture++),true,false);
            if(bDrumAudit)Check(ValidateDrumAttachment(),TEXT("animated drum attachment"));
        }
        return;
    }
    if(IsWeaponBusy())return;
    if(DrumGripAuditStage==5)
    {
        if(bDrumAudit)
        {
            if(FParse::Param(FCommandLine::Get(),TEXT("DrumCaptureAudio")))
                UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("DrumAudio"),Out+TEXT("/"));
            UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: COMPLETE failures=%d"),DrumGripAuditFailures);
            PC->ConsoleCommand(TEXT("quit"));return;
        }
        // Magazine audit close-out: yaw the viewmodel 90 deg so the side of the
        // seated magazine faces the camera, let the screenshot land, restore, quit.
        static bool bTurned=false;static double TurnedAt=0;static double ShotAt=0;static FRotator Keep;
        if(!bTurned){Keep=AKMViewmodel->GetRelativeRotation();AKMViewmodel->SetRelativeRotation(FRotator(0,90,0));bTurned=true;TurnedAt=FPlatformTime::Seconds();return;}
        if(ShotAt==0.0)
        {
            if(FPlatformTime::Seconds()-TurnedAt<0.8)return;
            if(LargeDrum)UE_LOG(LogTemp,Display,TEXT("MAG_SIDE: vis=%d loc=%s scale=%s origin=%s extent=%s socket=%s cam=%s"),
                LargeDrum->IsVisible()?1:0,*LargeDrum->GetComponentLocation().ToString(),*LargeDrum->GetComponentScale().ToString(),
                *LargeDrum->Bounds.Origin.ToString(),*LargeDrum->Bounds.BoxExtent.ToString(),
                *AKMViewmodel->GetSocketTransform(TEXT("WPN_SOCKET_Magazine")).ToString(),
                *FirstPersonCamera->GetComponentLocation().ToString());
            FScreenshotRequest::RequestScreenshot(Out/TEXT("side.png"),true,false);
            UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: MAG_SIDE_CAPTURED"));
            ShotAt=FPlatformTime::Seconds();return;
        }
        if(FPlatformTime::Seconds()-ShotAt<0.8)return;
        AKMViewmodel->SetRelativeRotation(Keep);
        if(FParse::Param(FCommandLine::Get(),TEXT("DrumCaptureAudio")))
            UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("DrumAudio"),Out+TEXT("/"));
        UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: COMPLETE failures=%d"),DrumGripAuditFailures);
        PC->ConsoleCommand(TEXT("quit"));return;
    }
    if(DrumGripAuditStage==10)
    {
        Check(G->Begin(P->Equipped()->InstanceId)&&G->Select(TEXT("magazine"),MagazineAuditId)&&G->Apply(),bDrumAudit?TEXT("install large drum through profile"):TEXT("install audited magazine through profile"));G->Close();
        DrumGripAuditStage=1;return;
    }
    if(DrumGripAuditStage==1||DrumGripAuditStage==3)
    {
        const bool Empty=DrumGripAuditStage==3;
        auto S=P->Snapshot();for(auto& I:S.Items){if(I.Place==1&&I.Cell==S.ActiveWeaponSlot)I.Magazine=Empty?0:17;if(I.Place==0&&I.Definition==TEXT("ammo_556"))I.Count=I.StackMax;}
        P->CommitState(S);DrumGripAuditReserve=P->AmmoCount();DrumGripAuditLastCapture=-1;DrumGripAuditCapture=0;
        DrumGripAuditRightDepthMin=MAX_flt;DrumGripAuditRightDepthMax=-MAX_flt;
        DrumGripAuditFramingMaxError=0;
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
        Check(DrumGripAuditFramingMaxError<.02f,TEXT("same depth framing as ordinary magazine"));
        const bool Empty=DrumGripAuditStage==4;
        const float Start=Empty?43.0f:50.0f,End=Empty?80.0f:95.0f,Length=Empty?162.0f:126.0f;
        const float Duration=DrumGripAuditReloadDuration;
        const float Baseline=Duration/M4DrumReloadTiming::DurationScale(Empty);
        const float PreviousInsert=Baseline*(M4DrumReloadTiming::PreviousRuntimeFraction(End/Length)-M4DrumReloadTiming::PreviousRuntimeFraction(Start/Length));
        const auto RuntimeAt=[Duration,Empty](float Frame){float Low=0,High=1;for(int I=0;I<24;++I){const float Mid=(Low+High)*.5f;if(M4DrumReloadTiming::SourceSeconds(Mid,Empty)*60<Frame)Low=Mid;else High=Mid;}return (Low+High)*.5f*Duration;};
        const float CurrentInsert=RuntimeAt(End)-RuntimeAt(Start);
        Check(Duration>1.0f&&CurrentInsert>.1f,TEXT("nonzero captured reload timing"));
        UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: timing empty=%d duration=%.6f insert_before=%.6f insert_now=%.6f speed_ratio=%.6f framing_error=%.6f"),Empty,Duration,PreviousInsert,CurrentInsert,PreviousInsert/FMath::Max(CurrentInsert,.001f),DrumGripAuditFramingMaxError);
        Check(FMath::Abs(PreviousInsert/1.5f-CurrentInsert)<.002f,TEXT("insertion playback exactly 1.5x"));
        if(Empty)
        {
            const float FollowThrough=RuntimeAt(116)-RuntimeAt(80);
            const float Retrieval=RuntimeAt(34)-RuntimeAt(24);
            UE_LOG(LogTemp,Display,TEXT("DRUM_GRIP: flow seat_to_strike=%.6f retrieval=%.6f"),FollowThrough,Retrieval);
            Check(FollowThrough>.40f&&FollowThrough<.50f,TEXT("empty seat to strike has no long hold"));
            Check(Retrieval>1.0f,TEXT("time moved to retrieving replacement drum"));
        }
        // The stage-5 branch above owns the close-out capture and the quit.
        ++DrumGripAuditStage;
    }
}
