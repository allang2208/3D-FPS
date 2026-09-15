#include "FPSGAMECharacter.h"
#include "UI/ColdSteelWeaponIcons.h"
#include "UI/ColdSteelPickup.h"
#include "Components/PoseableMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
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

void AFPSGAMECharacter::RunQBZ191IntegrationAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* PC=Cast<APlayerController>(Controller);
    if(!P||!G||!PC||!P->ProfileSlot().Contains(TEXT("QBZ191IntegrationAudit"))||GetWorld()->GetTimeSeconds()<5)return;
    static int Stage=0,Failures=0,Frame=0,BeforeAmmo=0,BeforeShots=0;static double At=0,LastFrame=-1;static FString AKMId;static bool OpticTested=false,DropTested=false;static TWeakObjectPtr<AColdSteelEnhancementAuditTarget> Target;static FVector TestEye,TestDirection;
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("QBZ191Run="),Run);Run=FPaths::MakeValidFileName(Run);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("QBZ191IntegrationAudit")/Run;
    const double Now=GetWorld()->GetTimeSeconds();
    // A user-requested still uses a separate mode and isolated profile. It does
    // not enter the firing, reload, persistence or attachment audit sequence.
    if(FParse::Param(FCommandLine::Get(),TEXT("QBZ191SightCapture")))
    {
        auto CaptureKey=[&](bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,Down?IE_Pressed:IE_Released,Down?1:0));};
        if(Stage==0)
        {
            IFileManager::Get().MakeDirectory(*Out,true);
            auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
            auto Rifle=P->CreateItem(TEXT("ue_qbz191"));Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=30;S.Items.Add(Rifle);S.ActiveWeaponSlot=9;
            if(!P->CommitState(S)){UE_LOG(LogTemp,Error,TEXT("QBZ191_SIGHT_CAPTURE could not equip screenshot fixture"));PC->ConsoleCommand(TEXT("quit"));return;}
            Stage=1;At=Now;
        }
        else if(Stage==1&&!IsWeaponBusy()&&Now-At>1.){CaptureKey(true);Stage=2;At=Now;}
        else if(Stage==2&&Now-At>2.)
        {
            const FString File=Out/TEXT("QBZ191-ADS-Irons.png");
            UE_LOG(LogTemp,Display,TEXT("QBZ191_SIGHT_CAPTURE mesh=%s aim=%s alpha=%.6f output=%s"),*GetPathNameSafe(AKMViewmodel->GetSkeletalMeshAsset()),*GetPathNameSafe(AimAnimation),WeaponADSFactor,*File);
            FScreenshotRequest::RequestScreenshot(File,false,false);Stage=3;At=Now;
        }
        else if(Stage==3&&Now-At>1.){CaptureKey(false);PC->ConsoleCommand(TEXT("quit"));Stage=20;}
        return;
    }
    auto Check=[&](bool OK,const TCHAR* Label){if(!OK)++Failures;UE_LOG(LogTemp,Display,TEXT("QBZ191_INTEGRATION: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Label);};
    auto Key=[&](FKey K,bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Down?IE_Pressed:IE_Released,Down?1:0));};
    if(Stage>0&&Stage<19&&!FParse::Param(FCommandLine::Get(),TEXT("QBZ191Readback"))&&Now-LastFrame>=.05){LastFrame=Now;UE_LOG(LogTemp,Display,TEXT("QBZ191_FRAME stage=%d index=%d elapsed=%.6f"),Stage,Frame,Now);FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("frame_%04d.png"),Frame++),false,false);}
    if(Stage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        if(FParse::Param(FCommandLine::Get(),TEXT("QBZ191ExistingProfile")))
        {
            const auto* Item=P->Items().FindByPredicate([](const auto& I){return I.Definition==TEXT("ue_qbz191")&&I.Place!=4;});
            Check(Item!=nullptr,TEXT("existing profile contains AKM"));
            if(Item){AKMId=Item->InstanceId;if(Item->Place==0)Check(P->DefaultAction(AKMId),TEXT("equip existing backpack AKM through normal action"));
                else if(P->Equipped()!=Item)Check(P->MoveItem(AKMId,1,Item->Cell),TEXT("activate existing equipped AKM"));}
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this,15.f);UE_LOG(LogTemp,Display,TEXT("AKM_AUDIO_START"));Stage=18;At=Now;return;
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("QBZ191Readback"))){Check(P->Equipped()&&P->Equipped()->Definition==TEXT("ue_qbz191")&&P->Equipped()->Magazine==17,TEXT("new process restores AKM instance and 17 rounds"));Stage=19;return;}
        Check(P->Items().ContainsByPredicate([](const auto& I){return I.Definition==TEXT("ue_qbz191")&&I.Place==4;}),TEXT("new profile receives QBZ in warehouse"));
        const int Count=P->Items().Num();Check(P->GrantStartingArmory()&&P->Items().Num()==Count,TEXT("warehouse grant cannot duplicate"));
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto M=P->CreateItem(TEXT("ue_m4a1"));M.Place=1;M.Cell=6;M.Magazine=11;S.Items.Add(M);
        auto A=P->CreateItem(TEXT("ue_qbz191"));A.Place=1;A.Cell=9;A.Magazine=17;AKMId=A.InstanceId;S.Items.Add(A);S.ActiveWeaponSlot=9;
        auto Ammo=P->CreateItem(TEXT("ammo_58"),90);Ammo.Cell=0;S.Items.Add(Ammo);Ammo=P->CreateItem(TEXT("ammo_556"),70);Ammo.Cell=1;S.Items.Add(Ammo);
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
        Check(bUseQBZ191&&AKMViewmodel->IsMaterialSectionShown(0,0)&&AKMViewmodel->IsMaterialSectionShown(4,0),TEXT("AKM geometry remains visible after repeated switch"));Stage=19;return;
    }
    if(Stage==1&&!IsWeaponBusy())
    {
        Check(bInventoryWeaponReady&&bUseQBZ191&&AKMViewmodel->GetSkeletalMeshAsset()->GetName()==TEXT("SK_QBZ191_Manny"),TEXT("QBZ191 with shared Manny hands actually loaded"));
        UE_LOG(LogTemp,Display,TEXT("AKM_ACTIVE mesh=%s"),*AKMViewmodel->GetSkeletalMeshAsset()->GetPathName());
        Check(IdleAnimation&&AimAnimation&&FireAnimation&&ReloadAnimation&&ReloadEmptyAnimation&&EquipAnimation,TEXT("all required native AKM actions loaded"));
        Check(WeaponFX->IsReady()&&AKMViewmodel->DoesSocketExist(TEXT("WPN_SOCKET_Eject")),TEXT("muzzle and ejection effects ready"));
        Check(P->AmmoDefinition()==TEXT("ammo_58")&&ReserveAmmo==90&&MagazineCapacity==30,TEXT("5.8 reserve and 30 round capacity"));
        auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();Icons->Request(*P->Equipped());
        Check(FMath::IsNearlyEqual(ReloadDuration,ReloadAnimation->GetPlayLength(),.001f)&&FMath::IsNearlyEqual(EmptyReloadDuration,ReloadEmptyAnimation->GetPlayLength(),.001f),TEXT("base reload durations match whole clips"));
        BeforeShots=ShotsFired;BeforeAmmo=MagazineAmmo;Key(EKeys::LeftMouseButton,true);Stage=2;At=Now;
    }
    else if(Stage==2&&Now-At>.55){Key(EKeys::LeftMouseButton,false);Check(ShotsFired-BeforeShots>=3&&MagazineAmmo==BeforeAmmo-(ShotsFired-BeforeShots),TEXT("held trigger consumes one round per shot"));Key(EKeys::RightMouseButton,true);Stage=3;At=Now;}
    else if(Stage==3&&Now-At>1.5)
    {
        UE_LOG(LogTemp,Display,TEXT("QBZ191_ADS component=%s aim=%.6f kick=%s"),*AKMViewmodel->GetRelativeTransform().ToString(),WeaponADSFactor,*GunKickPosition.ToString());
        const FVector Front=AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"));
        const FVector Rear=AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"));
        FVector2D FP,RP;PC->ProjectWorldLocationToScreen(Front,FP);PC->ProjectWorldLocationToScreen(Rear,RP);
        int W,H;PC->GetViewportSize(W,H);Check(FVector2D::Distance(FP,FVector2D(W*.5,H*.5))<2&&FVector2D::Distance(FP,RP)<2,TEXT("front and rear sight align at screen center"));
        UE_LOG(LogTemp,Display,TEXT("QBZ191_SIGHT front=%s rear=%s"),*FP.ToString(),*RP.ToString());
        TestEye=FirstPersonCamera->GetComponentLocation();TestDirection=ComputeShotDirection();
        FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Target=GetWorld()->SpawnActor<AColdSteelEnhancementAuditTarget>(TestEye+TestDirection*1500.f,FRotator::ZeroRotator,Spawn);FireShot();
        Check(bSightCalibrated&&WeaponADSFactor>.98f,TEXT("AKM calibrated ADS reaches target"));Key(EKeys::RightMouseButton,false);BeforeAmmo=MagazineAmmo;Key(EKeys::R,true);Key(EKeys::R,false);Stage=4;At=Now;
    }
    else if(Stage==4){const int Locked=ShotsFired;FireShot();Check(ShotsFired==Locked,TEXT("reload blocks firing"));const double Start=WeaponActionStartedAt;Key(EKeys::R,true);Key(EKeys::R,false);Check(WeaponActionStartedAt==Start,TEXT("repeated R does not restart reload"));Stage=5;}
    else if(Stage==5&&!IsWeaponBusy())
    {
        Check(Target.IsValid()&&Target->Received>0,TEXT("QBZ fired projectile damages target"));
        const FVector ImpactDelta=Ballistics->LastImpactPoint-TestEye;Check((ImpactDelta-TestDirection*FVector::DotProduct(ImpactDelta,TestDirection)).Size()<.2f,TEXT("projectile impact follows sight ray within 2 mm"));if(Target.IsValid())Target->Destroy();
        Check(MagazineAmmo==30&&ReserveAmmo==90-(30-BeforeAmmo),TEXT("normal reload settles 5.8 ammo exactly"));
        const int ReadyShots=ShotsFired;FireShot();Check(ShotsFired==ReadyShots+1,TEXT("fire immediately when reload ends"));
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
        Check(bUseQBZ191&&MagazineAmmo==30&&ADSRearEyeDistance==12.f,TEXT("AKM identity and framing restored"));
        Check(G->Begin(AKMId)&&G->Weapon(G->Definition())->Name==TEXT("QBZ-191"),TEXT("AKM workshop uses native definition"));G->Close();
        if(!DropTested){Check(P->Drop(AKMId),TEXT("drop QBZ instance through inventory"));Stage=24;At=Now;return;}
        if(!OpticTested){
            auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();const auto* Brush=Icons->Find(*P->Equipped());auto* T=Brush?Cast<UTexture2D>(Brush->GetResourceObject()):nullptr;
            Check(T!=nullptr,TEXT("live model inventory icon ready"));if(T){const auto& M=T->GetPlatformData()->Mips[0];TArray<FColor> Copy;Copy.Append(static_cast<const FColor*>(M.BulkData.LockReadOnly()),T->GetSizeX()*T->GetSizeY());M.BulkData.Unlock();TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(T->GetSizeX(),T->GetSizeY(),Copy,PNG);FFileHelper::SaveArrayToFile(PNG,*(Out/TEXT("inventory-icon.png")));}
            Check(G->Begin(AKMId)&&G->Select(TEXT("optic"),TEXT("panoramic_red_dot"))&&G->Apply(),TEXT("apply fitted panoramic optic through gunsmith"));G->Close();OpticTested=true;Stage=21;At=Now;return;
        }
        Check(P->TransferWarehouse(AKMId,4),TEXT("store AKM in warehouse"));Check(P->TransferWarehouse(AKMId,0),TEXT("retrieve AKM from warehouse"));Check(P->MoveItem(AKMId,1,9),TEXT("reequip retrieved AKM"));
        auto S=P->Snapshot();S.ActiveWeaponSlot=9;for(auto& I:S.Items)if(I.InstanceId==AKMId)I.Magazine=17;Check(P->CommitState(S)&&P->SaveNow(),TEXT("save AKM instance with 17 rounds"));Stage=9;
    }
    else if(Stage==24&&Now-At>1.5){bool Found=false;for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(It->ItemId==AKMId){Found=It->Weapon&&It->Weapon->GetSkinnedAsset()&&It->Weapon->GetSkinnedAsset()->GetName()==TEXT("SK_QBZ191_Manny");PC->SetControlRotation((It->GetActorLocation()-FirstPersonCamera->GetComponentLocation()).Rotation());}Check(Found,TEXT("world pickup renders the QBZ model"));Stage=25;At=Now;}
    else if(Stage==25&&Now-At>.3){Check(P->Pickup(AKMId),TEXT("focused pickup returns QBZ to backpack"));Check(P->MoveItem(AKMId,1,9),TEXT("reequip picked up original instance"));PC->SetControlRotation(FRotator::ZeroRotator);DropTested=true;Stage=8;At=Now;}
    else if(Stage==21&&Now-At>1&&!IsWeaponBusy()){Check(bHolographicOptic,TEXT("QBZ optic visible"));Key(EKeys::RightMouseButton,true);Stage=22;At=Now;}
    else if(Stage==22&&Now-At>1){FScreenshotRequest::RequestScreenshot(Out/TEXT("optic-ads.png"),false,false);Stage=23;At=Now;}
    else if(Stage==23&&Now-At>.3){Key(EKeys::RightMouseButton,false);Check(G->Begin(AKMId)&&G->Select(TEXT("optic"),TEXT("false"))&&G->Apply(),TEXT("restore factory sights"));G->Close();Stage=8;At=Now;}
    else if(Stage==9&&!IsWeaponBusy()){Check(P->ReloadProfile()&&P->Equipped()->Definition==TEXT("ue_qbz191")&&MagazineAmmo==17,TEXT("reload saved AKM profile"));Stage=19;}
    else if(Stage==19&&!IsWeaponBusy())
    {
        if(!FParse::Param(FCommandLine::Get(),TEXT("QBZ191Readback")))UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("AKMAudio"),Out+TEXT("/"));
        UE_LOG(LogTemp,Display,TEXT("QBZ191_INTEGRATION: COMPLETE failures=%d"),Failures);Stage=20;PC->ConsoleCommand(TEXT("quit"));
    }
}
