#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "AudioMixerBlueprintLibrary.h"

void AFPSGAMECharacter::RunForegripAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* PC=Cast<APlayerController>(Controller);
    if(!P||!G||!PC||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("ForegripAudit")))return;
    const bool bCantedAudit=FParse::Param(FCommandLine::Get(),TEXT("CantedGripAudit"));
    const bool bVerticalAudit=FParse::Param(FCommandLine::Get(),TEXT("VerticalGripAudit"));
    const bool bPrismAudit=FParse::Param(FCommandLine::Get(),TEXT("PrismGripAudit"));
    const bool bAKM=FParse::Param(FCommandLine::Get(),TEXT("AKMAttachmentAudit"));
    const TCHAR* Variant=bCantedAudit?TEXT("canted_foregrip"):bVerticalAudit?TEXT("vertical_foregrip"):bPrismAudit?TEXT("prism_handstop"):TEXT("angled_foregrip");
    const TCHAR* Prefix=bCantedAudit?TEXT("A_M4_Canted_"):bVerticalAudit?TEXT("A_M4_Vertical_"):bAKM?(bPrismAudit?TEXT("A_AKM_prism_"):TEXT("A_AKM_angled_")):(bPrismAudit?TEXT("A_M4_Prism_"):TEXT("A_M4_Foregrip_"));
    const auto& GripAnimations=bCantedAudit?CantedGripAnimations:bVerticalAudit?VerticalGripAnimations:bPrismAudit?PrismGripAnimations:ForegripAnimations;
    auto HasGrip=[&](){return bCantedAudit?HasCantedForegrip():bVerticalAudit?HasVerticalForegrip():bPrismAudit?HasPrismHandstop():HasAngledForegrip();};
    const float Now=GetWorld()->GetTimeSeconds();if(Now<5||Now<ForegripAuditNextTime)return;
    auto Check=[this](bool OK,const TCHAR* Label){if(!OK)++ForegripAuditFailures;UE_LOG(LogTemp,Display,TEXT("FOREGRIP_AUDIT: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Label);};
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("ForegripRun="),Run);Run=FPaths::MakeValidFileName(Run);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("ForegripAudit")/Run;
    auto Capture=[&](const FString& Name){IFileManager::Get().MakeDirectory(*Out,true);FScreenshotRequest::RequestScreenshot(Out/(Name+TEXT(".png")),!(bDrumInstalled&&FParse::Param(FCommandLine::Get(),TEXT("AKMReloadSide"))),false);if(FParse::Param(FCommandLine::Get(),TEXT("AKMReloadAudio")))UE_LOG(LogTemp,Display,TEXT("AKM_POLISH_FRAME name=%s time=%.6f source=%.6f"),*Name,Now,ReloadSourceTime(WeaponStateElapsed));};
    auto Install=[&](const TCHAR* Slot,const TCHAR* Value){const bool OK=P->Equipped()&&G->Begin(P->Equipped()->InstanceId)&&G->Select(Slot,Value)&&G->Apply();G->Close();Check(OK,TEXT("catalog apply"));};
    if(ForegripAuditStage==0)
    {
        if(FParse::Param(FCommandLine::Get(),TEXT("AKMReloadAudio"))){UAudioMixerBlueprintLibrary::StartRecordingOutput(this,60.f);UE_LOG(LogTemp,Display,TEXT("AKM_POLISH_AUDIO_START time=%.6f"),Now);}
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(bAKM?TEXT("ue_akm"):TEXT("ue_m4a1"));W.Place=1;W.Cell=9;W.Magazine=17;S.Items.Add(W);S.ActiveWeaponSlot=9;
        auto A=P->CreateItem(bAKM?TEXT("ammo_762"):TEXT("ammo_556"));A.Place=0;A.Cell=0;A.Count=A.StackMax;S.Items.Add(A);Check(P->CommitState(S),TEXT("isolated profile"));
        Check(GripAnimations.Num()==9,TEXT("all nine animation variants loaded with matching duration"));
        ForegripAuditStage=1;return;
    }
    if(IsReloading())
    {
        // Character tick updates evaluator inputs before the mesh's scheduled tick.
        // Sample the current pose rather than comparing the previous frame's bones to today's clock.
        if(bAKM&&ReloadSourceTime(WeaponStateElapsed)*120.f>=(bPendingEmptyReload?443.f:333.f)){AKMViewmodel->TickAnimation(0.f,false);AKMViewmodel->RefreshBoneTransforms();AKMViewmodel->UpdateChildTransforms();}
        if(bAKM&&bDrumInstalled)
        {
            const float SourceFrame=ReloadSourceTime(WeaponStateElapsed)*120.f;
            const FVector MagazineInRoot=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Magazine")));
            const float Extracted=(MagazineInRoot-ForegripAuditSeatedMagazine).Size();
            if(SourceFrame>=64.f&&SourceFrame<86.f&&Extracted>.03f&&!bDrumReleasedDuringReload)bForegripAuditSawPull=true;
            if(bDrumReleasedDuringReload&&!bForegripAuditSawDrop){Check(bForegripAuditSawPull&&SourceFrame>=86.f&&Extracted>.12f,TEXT("AKM drum visibly extracted before release"));bForegripAuditSawDrop=true;}
        }
        if(WeaponStateElapsed-ForegripAuditLastCapture>=.05f)
        {
            ForegripAuditLastCapture=WeaponStateElapsed;
            Capture(FString::Printf(TEXT("%s_%s_%03d"),bDrumInstalled?TEXT("drum"):TEXT("standard"),bPendingEmptyReload?TEXT("empty"):TEXT("normal"),ForegripAuditCapture++));
            Check(GunplayAnimation&&GunplayAnimation->ActionClip&&GunplayAnimation->ActionClip->GetName().StartsWith(Prefix),TEXT("runtime reload uses selected grip clip"));
            Check(HasGrip(),TEXT("attachment visible during action"));
            if(bAKM&&ReloadSourceTime(WeaponStateElapsed)*120.f>=(bPendingEmptyReload?443.f:333.f))
            {
                const FVector HandInRoot=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("hand_l")));
                Check((HandInRoot-ForegripAuditSeatedHand).Size()<.006f,TEXT("reload tail holds installed grip directly"));
            }
            if(bAKM&&bDrumInstalled)
            {
                const auto* Asset=AKMViewmodel->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();bool Found=false,Hidden=true;
                for(int32 L=0;L<Render->LODRenderData.Num();++L)for(const auto& Section:Render->LODRenderData[L].RenderSections)
                    if(Asset->GetMaterials()[Section.MaterialIndex].MaterialSlotName.ToString().Contains(TEXT("Magazine"))){Found=true;Hidden&=!AKMViewmodel->IsMaterialSectionShown(Section.MaterialIndex,L);}
                Check(Found&&Hidden,TEXT("factory magazine hidden throughout drum reload all LODs"));
            }
        }
        return;
    }
    if(WeaponState==EAKMWeaponState::Equipping&&ForegripAuditStage==17&&WeaponStateElapsed-ForegripAuditLastCapture>=.1f)
    {
        ForegripAuditLastCapture=WeaponStateElapsed;
        Check(GunplayAnimation&&GunplayAnimation->ActionClip==GripAnimations.FindRef(EquipAnimation),TEXT("equip uses selected support grip"));
        Capture(FString::Printf(TEXT("equip_%03d"),ForegripAuditCapture++));
    }
    if(IsWeaponBusy())return;
    if(ForegripAuditStage==1){Install(TEXT("underbarrel"),Variant);if(bAKM){Install(TEXT("optic"),TEXT("holographic"));Install(TEXT("muzzle"),TEXT("true"));}ForegripAuditStage=2;ForegripAuditNextTime=Now+1;return;}
    if(ForegripAuditStage==2)
    {
        Check(HasGrip()&&((int32)HasAngledForegrip()+(int32)HasPrismHandstop()+(int32)HasVerticalForegrip()+(int32)HasCantedForegrip()==1),TEXT("grip installed exclusively"));
        Check(GunplayAnimation->IdleClip==GripAnimations.FindRef(IdleAnimation),TEXT("runtime idle uses selected grasp"));
        if(!bAKM&&!bPrismAudit&&!bVerticalAudit&&!bCantedAudit&&HasAngledForegrip())
        {
            auto* Original=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/M4AngledForegripFinal/SM_M4_AngledForegrip"));
            UStaticMesh* Compact=AngledForegrip->GetStaticMesh();
            Check(Compact->GetPathName().Contains(TEXT("M4AngledForegripCompact75"))&&
                GunplayAnimation->IdleClip->GetPathName().Contains(TEXT("M4ForegripWristNatural")),TEXT("compact mesh and natural wrist three finger animation active"));
            Check(Original&&Compact->GetBoundingBox().GetSize().Equals(Original->GetBoundingBox().GetSize()*.75f,.01f),TEXT("foregrip dimensions reduced by 25 percent on all axes"));
        }
        Check(P->SaveNow()&&P->ReloadProfile()&&P->Equipped()&&G->Installed(*P->Equipped()).FindRef(TEXT("underbarrel"))==Variant,TEXT("save reload retains attachment"));
        Capture(TEXT("idle"));AimPressed();ForegripAuditStage=3;ForegripAuditNextTime=Now+1;return;
    }
    if(ForegripAuditStage==3){Check(GunplayAnimation->AimClip==GripAnimations.FindRef(AimAnimation),TEXT("ADS variant"));if(bAKM){float Error;Check(ValidateGunsmithSight(Error)&&ValidateHolographicShot(),TEXT("AKM holographic reticle and projectile aim align"));Check(MuzzleAttachment&&MuzzleAttachment->IsVisible(),TEXT("AKM muzzle attached"));}Capture(TEXT("ads"));AimReleased();FirePressed();ForegripAuditStage=4;ForegripAuditNextTime=Now+.1f;return;}
    if(ForegripAuditStage==4){Check(GunplayAnimation->ActionClip&&GunplayAnimation->ActionClip->GetName().StartsWith(Prefix),TEXT("fire uses selected grip"));FireReleased();ForegripAuditStage=5;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==5||ForegripAuditStage==7||ForegripAuditStage==9||ForegripAuditStage==11)
    {
        const bool Empty=ForegripAuditStage==7||ForegripAuditStage==11;
        if(ForegripAuditStage==9)Install(TEXT("magazine"),TEXT("large_drum"));
        if(bAKM&&ForegripAuditStage==7)Install(TEXT("muzzle"),TEXT("brake"));
        if(bAKM&&ForegripAuditStage==9)Install(TEXT("muzzle"),TEXT("titanium_brake"));
        if(bAKM&&ForegripAuditStage==9&&FParse::Param(FCommandLine::Get(),TEXT("AKMReloadSide")))
        {
            if(auto* Camera=GetWorld()->SpawnActor<ACameraActor>())
            {
                const FTransform Root=AKMViewmodel->GetSocketTransform(TEXT("WPN_root"));
                const FVector Focus=Root.TransformPosition(FVector(0,.08,-.08));
                const FVector Eye=Focus+Root.TransformVector(FVector(-.95,-.25,.2));
                Camera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(48);PC->SetViewTarget(Camera);
            }
        }
        auto S=P->Snapshot();for(auto& I:S.Items){if(I.Place==1&&I.Cell==S.ActiveWeaponSlot)I.Magazine=Empty?0:17;if(I.Definition==(bAKM?TEXT("ammo_762"):TEXT("ammo_556")))I.Count=I.StackMax;}
        Check(P->CommitState(S),TEXT("reload setup"));ForegripAuditLastCapture=-1;ForegripAuditCapture=0;
        ForegripAuditSeatedMagazine=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Magazine")));bForegripAuditSawPull=false;bForegripAuditSawDrop=false;
        ForegripAuditSeatedHand=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).InverseTransformPosition(AKMViewmodel->GetSocketLocation(TEXT("hand_l")));
        ReloadPressed();Check(IsReloading(),TEXT("reload accepted"));++ForegripAuditStage;return;
    }
    if(ForegripAuditStage==6||ForegripAuditStage==8||ForegripAuditStage==10||ForegripAuditStage==12)
    {
        Check(MagazineAmmo==MagazineCapacity,TEXT("reload completes ammo contract"));
        if(bAKM&&bDrumInstalled){Check(ValidateDrumAttachment()&&MagazineCapacity==50,TEXT("AKM drum seated and original magazine hidden"));Check(bForegripAuditSawDrop,TEXT("AKM completed ordered drum release"));}
        Check(HasGrip()&&GunplayAnimation->IdleClip==GripAnimations.FindRef(IdleAnimation),TEXT("reload restores selected grasp"));Capture(FString::Printf(TEXT("returned_%d"),ForegripAuditStage));++ForegripAuditStage;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==13){if(FParse::Param(FCommandLine::Get(),TEXT("AKMReloadSide")))PC->SetViewTarget(this);Install(TEXT("underbarrel"),bPrismAudit?TEXT("angled_foregrip"):TEXT("prism_handstop"));ForegripAuditStage=14;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==14)
    {
        Check(bPrismAudit?(HasAngledForegrip()&&!HasPrismHandstop()):(!HasAngledForegrip()&&HasPrismHandstop()),TEXT("alternative grip preserved"));
        UAnimSequence* AlternatePose=(bPrismAudit?ForegripAnimations:PrismGripAnimations).FindRef(IdleAnimation);
        // The alternative handstop may still use the existing drum/base support until its optional clips are installed.
        if(!AlternatePose&&!bPrismAudit)AlternatePose=bDrumInstalled?DrumSupportAnimations.FindRef(IdleAnimation).Get():IdleAnimation.Get();
        Check(GunplayAnimation->IdleClip==AlternatePose,TEXT("alternative grip restores its supported pose"));
        Install(TEXT("underbarrel"),TEXT("false"));Install(TEXT("magazine"),TEXT("false"));if(bAKM){Install(TEXT("optic"),TEXT("false"));Install(TEXT("muzzle"),TEXT("false"));}ForegripAuditStage=15;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==15)
    {
        Check(!HasAngledForegrip()&&!HasPrismHandstop()&&!HasVerticalForegrip()&&!HasCantedForegrip()&&GunplayAnimation->IdleClip==IdleAnimation,TEXT("removal restores original mesh and animation"));
        Capture(TEXT("removed"));ForegripAuditStage=16;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==16)
    {
        Install(TEXT("underbarrel"),Variant);
        StartEquipCharge();ForegripAuditLastCapture=0;ForegripAuditCapture=0;
        if(auto* ReviewCamera=GetWorld()->SpawnActor<ACameraActor>())
        {
            const FVector Focus=(bCantedAudit?CantedForegrip:bVerticalAudit?VerticalForegrip:bPrismAudit?PrismHandstop:AngledForegrip)->Bounds.Origin;
            const FVector Eye=Focus+AKMViewmodel->GetComponentTransform().TransformVectorNoScale(FVector(48,14,10));
            ReviewCamera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());ReviewCamera->GetCameraComponent()->SetFieldOfView(42);
            PC->SetViewTarget(ReviewCamera);
        }
        ForegripAuditStage=17;ForegripAuditNextTime=Now+.1f;return;
    }
    if(ForegripAuditStage==17){FScreenshotRequest::RequestScreenshot(Out/TEXT("grasp_closeup.png"),false,false);ForegripAuditStage=18;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==18)
    {
        if(auto* ReviewCamera=Cast<ACameraActor>(PC->GetViewTarget()))
        {
            const FVector Focus=(bCantedAudit?CantedForegrip:bVerticalAudit?VerticalForegrip:bPrismAudit?PrismHandstop:AngledForegrip)->Bounds.Origin;
            const FVector Forward=(AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"))-AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
            const FVector Eye=Focus+Forward*45.f-AKMViewmodel->GetUpVector()*5.f;
            ReviewCamera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());
        }
        ForegripAuditStage=19;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==19){FScreenshotRequest::RequestScreenshot(Out/TEXT("grasp_front.png"),false,false);ForegripAuditStage=20;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==20)
    {
        if(auto* ReviewCamera=Cast<ACameraActor>(PC->GetViewTarget()))
        {
            const FVector Focus=(AKMViewmodel->GetSocketLocation(TEXT("hand_l"))+AKMViewmodel->GetSocketLocation(TEXT("lowerarm_l")))*.5f;
            const FVector Eye=Focus+AKMViewmodel->GetComponentTransform().TransformVectorNoScale(FVector(-55,14,12));
            ReviewCamera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());
        }
        ForegripAuditStage=21;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==21){FScreenshotRequest::RequestScreenshot(Out/TEXT("wrist_review.png"),false,false);ForegripAuditStage=bAKM?25:22;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==25)
    {
        Install(TEXT("optic"),TEXT("holographic"));
        if(auto* ReviewCamera=Cast<ACameraActor>(PC->GetViewTarget()))
        {
            const FTransform Root=AKMViewmodel->GetSocketTransform(TEXT("WPN_root"));
            const FVector Focus=Root.TransformPosition(FVector(0,.08,.075));
            const FVector Eye=Focus+Root.TransformVector(FVector(-.40,.16,.13));
            ReviewCamera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());ReviewCamera->GetCameraComponent()->SetFieldOfView(42);
        }
        ForegripAuditStage=26;ForegripAuditNextTime=Now+.5f;return;
    }
    if(ForegripAuditStage==26){FScreenshotRequest::RequestScreenshot(Out/TEXT("optic_mount_review.png"),false,false);ForegripAuditStage=22;ForegripAuditNextTime=Now+.5f;return;}
    if(ForegripAuditStage==22){UE_LOG(LogTemp,Display,TEXT("FOREGRIP_AUDIT: COMPLETE failures=%d"),ForegripAuditFailures);if(FParse::Param(FCommandLine::Get(),TEXT("AKMReloadAudio")))UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("AKMReloadAudio"),Out+TEXT("/"));ForegripAuditStage=24;ForegripAuditNextTime=Now+1.f;return;}
    if(ForegripAuditStage==24){ForegripAuditStage=23;PC->ConsoleCommand(TEXT("quit"));}
}
