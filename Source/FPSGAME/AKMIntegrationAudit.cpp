#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/FPSBallisticsComponent.h"
#include "Weapons/AKMSovietCalibration.h"
#include "UI/ColdSteelEnhancementAuditTarget.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "AudioMixerBlueprintLibrary.h"

void AFPSGAMECharacter::RunAKMIntegrationAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* PC=Cast<APlayerController>(Controller);
    if(!P||!G||!PC||!P->ProfileSlot().Contains(TEXT("AKMIntegrationAudit"))||GetWorld()->GetTimeSeconds()<5)return;
    static int Stage=0,Failures=0,Frame=0,BeforeAmmo=0,BeforeShots=0;static double At=0,LastFrame=-1;static FString AKMId;
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("AKMRun="),Run);Run=FPaths::MakeValidFileName(Run);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("AKMIntegrationAudit")/Run;
    const double Now=GetWorld()->GetTimeSeconds();
    auto Check=[&](bool OK,const TCHAR* Label){if(!OK)++Failures;UE_LOG(LogTemp,Display,TEXT("AKM_INTEGRATION: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Label);};
    auto Key=[&](FKey K,bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Down?IE_Pressed:IE_Released,Down?1:0));};
    if(Stage>0&&Stage<19&&!FParse::Param(FCommandLine::Get(),TEXT("AKMReadback"))&&Now-LastFrame>=.05){LastFrame=Now;UE_LOG(LogTemp,Display,TEXT("AKM_FRAME stage=%d index=%d elapsed=%.6f"),Stage,Frame,Now);FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("frame_%04d.png"),Frame++),false,false);}
    if(Stage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        if(FParse::Param(FCommandLine::Get(),TEXT("AKMExistingProfile")))
        {
            const auto* Item=P->Items().FindByPredicate([](const auto& I){return I.Definition==TEXT("ue_akm")&&I.Place!=4;});
            Check(Item!=nullptr,TEXT("existing profile contains AKM"));
            if(Item){AKMId=Item->InstanceId;if(Item->Place==0)Check(P->DefaultAction(AKMId),TEXT("equip existing backpack AKM through normal action"));
                else if(P->Equipped()!=Item)Check(P->MoveItem(AKMId,1,Item->Cell),TEXT("activate existing equipped AKM"));}
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this,15.f);UE_LOG(LogTemp,Display,TEXT("AKM_AUDIO_START"));Stage=18;At=Now;return;
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("AKMReadback"))){Check(P->Equipped()&&P->Equipped()->Definition==TEXT("ue_akm")&&P->Equipped()->Magazine==17,TEXT("new process restores AKM instance and 17 rounds"));Stage=19;return;}
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto M=P->CreateItem(TEXT("ue_m4a1"));M.Place=1;M.Cell=6;M.Magazine=11;S.Items.Add(M);
        auto A=P->CreateItem(TEXT("ue_akm"));A.Place=1;A.Cell=9;A.Magazine=17;AKMId=A.InstanceId;S.Items.Add(A);S.ActiveWeaponSlot=9;
        auto Ammo=P->CreateItem(TEXT("ammo_762"),90);Ammo.Cell=0;S.Items.Add(Ammo);Ammo=P->CreateItem(TEXT("ammo_556"),70);Ammo.Cell=1;S.Items.Add(Ammo);
        Check(P->CommitState(S),TEXT("equip native AKM alongside M4"));Check(!HasInfiniteReserveAmmo(),TEXT("finite reserve fixture"));
        UAudioMixerBlueprintLibrary::StartRecordingOutput(this,40.f);UE_LOG(LogTemp,Display,TEXT("AKM_AUDIO_START"));Stage=1;At=Now;return;
    }
    if(Stage==18&&Now-At>5)
    {
        Check(bInventoryWeaponReady&&AKMViewmodel->IsVisible(),TEXT("existing profile equipped mesh visible"));
        Check(AKMViewmodel->IsMaterialSectionShown(0,0)&&AKMViewmodel->IsMaterialSectionShown(4,0),TEXT("AKM receiver and sights visible after modified M4"));
        UE_LOG(LogTemp,Display,TEXT("AKM_EXISTING mesh=%s transform=%s camera=%s"),*GetNameSafe(AKMViewmodel->GetSkeletalMeshAsset()),*AKMViewmodel->GetRelativeTransform().ToString(),*FirstPersonCamera->GetComponentTransform().ToString());
        Check(P->CycleWeapon(),TEXT("return to existing modified M4"));Stage=16;At=Now;return;
    }
    if(Stage==16&&Now-At>2&&!IsWeaponBusy()){
        Check(bUsingM4Infima&&bDrumVisual&&!MuzzleVariant.IsEmpty(),TEXT("modified M4 attachments restored"));
        Check(P->CycleWeapon(),TEXT("switch from modified M4 to AKM again"));Stage=17;At=Now;return;
    }
    if(Stage==17&&Now-At>4&&!IsWeaponBusy()){
        Check(!bUsingM4Infima&&AKMViewmodel->IsMaterialSectionShown(0,0)&&AKMViewmodel->IsMaterialSectionShown(4,0),TEXT("AKM geometry remains visible after repeated switch"));Stage=19;return;
    }
    if(Stage==1&&!IsWeaponBusy())
    {
        Check(bInventoryWeaponReady&&!bUsingM4Infima&&AKMViewmodel->GetSkeletalMeshAsset()->GetName()==TEXT("SK_AKM_MannyNative"),TEXT("AKM with shared M4 hands actually loaded"));
        UE_LOG(LogTemp,Display,TEXT("AKM_ACTIVE mesh=%s"),*AKMViewmodel->GetSkeletalMeshAsset()->GetPathName());
        Check(IdleAnimation&&AimAnimation&&FireAnimation&&ReloadAnimation&&ReloadEmptyAnimation&&EquipAnimation,TEXT("all required native AKM actions loaded"));
        Check(WeaponFX->IsReady()&&AKMViewmodel->DoesSocketExist(TEXT("WPN_SOCKET_Eject")),TEXT("muzzle and ejection effects ready"));
        Check(P->AmmoDefinition()==TEXT("ammo_762")&&ReserveAmmo==90&&MagazineCapacity==30,TEXT("7.62 reserve and 30 round capacity"));
        BeforeShots=ShotsFired;BeforeAmmo=MagazineAmmo;Key(EKeys::LeftMouseButton,true);Stage=2;At=Now;
    }
    else if(Stage==2&&Now-At>.55){Key(EKeys::LeftMouseButton,false);Check(ShotsFired-BeforeShots>=3&&MagazineAmmo==BeforeAmmo-(ShotsFired-BeforeShots),TEXT("held trigger consumes one round per shot"));Key(EKeys::RightMouseButton,true);Stage=3;At=Now;}
    else if(Stage==3&&Now-At>.55)
    {
        if(FParse::Param(FCommandLine::Get(),TEXT("AKMSightAudit")))
        {
            static int Sample=0,ImpactBefore=0;static double ShotAt=0;
            static TWeakObjectPtr<AColdSteelEnhancementAuditTarget> Target;
            static FVector Eye,Direction;
            constexpr float Ranges[]={500.f,2500.f,10000.f};
            if(Sample<3)
            {
                if(!Target.IsValid())
                {
                    if(Now-At<1.2)return;
                    const FVector Front=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(AKMSoviet::Front);
                    const FVector Rear=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(AKMSoviet::Rear);
                    Eye=FirstPersonCamera->GetComponentLocation();Direction=(Front-Eye).GetSafeNormal();
                    FVector2D FrontPixel,RearPixel;PC->ProjectWorldLocationToScreen(Front,FrontPixel);PC->ProjectWorldLocationToScreen(Rear,RearPixel);
                    int32 W,H;PC->GetViewportSize(W,H);
                    Check(FVector2D::Distance(FrontPixel,FVector2D(W*.5,H*.5))<2.f,TEXT("measured front sight projects to screen center"));
                    Check(FVector2D::Distance(FrontPixel,RearPixel)<2.f,TEXT("measured front sight and rear notch align"));
                    Check(FVector::Dist(ComputeShotDirection(),Direction)<.000001f,TEXT("ADS shot direction follows the new mesh front sight"));
                    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                    Target=GetWorld()->SpawnActor<AColdSteelEnhancementAuditTarget>(Eye+Direction*Ranges[Sample],FRotator::ZeroRotator,Spawn);
                    Check(Target.IsValid(),TEXT("spawn isolated ballistic target"));
                    ImpactBefore=Ballistics->ImpactCount;FireShot();ShotAt=Now;
                    UE_LOG(LogTemp,Display,TEXT("AKM_SIGHT_SAMPLE range_cm=%.0f front_px=%s rear_px=%s hip=%s"),Ranges[Sample],*FrontPixel.ToString(),*RearPixel.ToString(),*HipViewmodelLocation.ToString());
                    return;
                }
                if(Now-ShotAt<Ranges[Sample]/FMath::Max(ProjectileSpeedCM,1.f)+.3f)return;
                const FVector Impact=Ballistics->LastImpactPoint;
                const float Error=(Impact-Eye-Direction*FVector::DotProduct(Impact-Eye,Direction)).Size();
                Check(Target->Received>0&&Ballistics->ImpactCount>ImpactBefore,TEXT("real fired projectile hit the isolated target"));
                Check(Error<.2f,TEXT("actual impact within 2 mm of visible sight ray"));
                UE_LOG(LogTemp,Display,TEXT("AKM_SIGHT_IMPACT range_cm=%.0f error_cm=%.6f damage=%.3f"),Ranges[Sample],Error,Target->Received);
                Target->Destroy();Target.Reset();++Sample;At=Now;return;
            }
        }
        Check(bSightCalibrated&&WeaponADSFactor>.98f,TEXT("AKM calibrated ADS reaches target"));Key(EKeys::RightMouseButton,false);BeforeAmmo=MagazineAmmo;Key(EKeys::R,true);Key(EKeys::R,false);Stage=4;At=Now;
    }
    else if(Stage==4){const double Start=WeaponActionStartedAt;Key(EKeys::R,true);Key(EKeys::R,false);Check(WeaponActionStartedAt==Start,TEXT("repeated R does not restart reload"));Stage=5;}
    else if(Stage==5&&!IsWeaponBusy())
    {
        Check(MagazineAmmo==30&&ReserveAmmo==90-(30-BeforeAmmo),TEXT("normal reload settles 7.62 ammo exactly"));
        auto S=P->Snapshot();for(auto& I:S.Items)if(I.InstanceId==AKMId)I.Magazine=0;Check(P->CommitState(S),TEXT("prepare empty AKM"));BeforeAmmo=ReserveAmmo;
        Key(EKeys::R,true);Key(EKeys::R,false);Stage=6;
    }
    else if(Stage==6&&!IsWeaponBusy())
    {
        Check(MagazineAmmo==30&&ReserveAmmo==BeforeAmmo-30,TEXT("empty reload settles ammo once"));
        Check(P->CycleWeapon(),TEXT("switch to M4"));Stage=7;
    }
    else if(Stage==7&&!IsWeaponBusy())
    {
        Check(bUsingM4Infima&&MagazineAmmo==11&&P->AmmoDefinition()==TEXT("ammo_556")&&ReserveAmmo==70,TEXT("M4 mesh and untouched 5.56 ammo restored"));
        Check(P->CycleWeapon(),TEXT("switch back to AKM"));Stage=8;
    }
    else if(Stage==8&&!IsWeaponBusy())
    {
        Check(!bUsingM4Infima&&MagazineAmmo==30&&ADSRearEyeDistance==18.f,TEXT("AKM identity and framing restored"));
        Check(G->Begin(AKMId)&&G->Weapon(G->Definition())->Name==TEXT("AKM"),TEXT("AKM workshop uses native definition"));G->Close();
        Check(P->TransferWarehouse(AKMId,4),TEXT("store AKM in warehouse"));Check(P->TransferWarehouse(AKMId,0),TEXT("retrieve AKM from warehouse"));Check(P->MoveItem(AKMId,1,9),TEXT("reequip retrieved AKM"));
        auto S=P->Snapshot();S.ActiveWeaponSlot=9;for(auto& I:S.Items)if(I.InstanceId==AKMId)I.Magazine=17;Check(P->CommitState(S)&&P->SaveNow(),TEXT("save AKM instance with 17 rounds"));Stage=9;
    }
    else if(Stage==9&&!IsWeaponBusy()){Check(P->ReloadProfile()&&P->Equipped()->Definition==TEXT("ue_akm")&&MagazineAmmo==17,TEXT("reload saved AKM profile"));Stage=19;}
    else if(Stage==19&&!IsWeaponBusy())
    {
        if(!FParse::Param(FCommandLine::Get(),TEXT("AKMReadback")))UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("AKMAudio"),Out+TEXT("/"));
        UE_LOG(LogTemp,Display,TEXT("AKM_INTEGRATION: COMPLETE failures=%d"),Failures);Stage=20;PC->ConsoleCommand(TEXT("quit"));
    }
}
