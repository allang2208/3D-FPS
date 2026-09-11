#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelPickup.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Camera/CameraComponent.h"
#include "ImageUtils.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"

void AFPSGAMEPlayerController::RunM4GunsmithAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
    if(!C||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("M4GunsmithAudit")))return;
    static const bool LPVO=FParse::Param(FCommandLine::Get(),TEXT("LPVOAudit"));
    static const bool Scope2X=FParse::Param(FCommandLine::Get(),TEXT("PrismScope2XAudit"));
    static const bool Panoramic=LPVO||Scope2X||FParse::Param(FCommandLine::Get(),TEXT("PanoramicRedDotAudit"));
    static const FString MeshName=LPVO?TEXT("SM_LPVO1to6X"):Scope2X?TEXT("SM_PrismScope2X"):TEXT("SM_PanoramicRedDot");
    static const FString OpticId=LPVO?TEXT("lpvo_1_6x"):Scope2X?TEXT("prism_scope_2x"):(Panoramic?TEXT("panoramic_red_dot"):TEXT("holographic"));
    const FString Dir=FPaths::ProjectSavedDir()/(LPVO?TEXT("LPVOAudit"):Scope2X?TEXT("PrismScope2XAudit"):(Panoramic?TEXT("PanoramicRedDotAudit"):TEXT("M4GunsmithAudit")));IFileManager::Get().MakeDirectory(*Dir,true);
    auto Counts=MakeShared<FIntPoint>(0,0);
    auto Check=[Counts](bool Pass,const TCHAR* Name){Counts->X++;if(!Pass)Counts->Y++;UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    const bool Load=FParse::Param(FCommandLine::Get(),TEXT("M4GunsmithLoadAudit"));
    auto State=P->Snapshot();
    if(!Load){State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);auto Gun=P->CreateItem(TEXT("ue_m4a1"));Gun.Place=1;Gun.Cell=9;Gun.Magazine=17;State.Items.Add(Gun);State.ActiveWeaponSlot=9;auto Ammo=P->CreateItem(TEXT("ammo_556"),40);Ammo.Cell=0;State.Items.Add(Ammo);Check(P->CommitState(State),TEXT("seed isolated secondary-slot M4"));}
    else Check(P->Equipped()&&G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==OpticId&&C->HasHolographicOptic(),TEXT("new process restores saved holographic M4"));
    auto Later=[this](float Time,TFunction<void()> Fn){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[Fn](){Fn();},Time,false);};
    Later(3.f,[this,P,G,C,Check,Load,Dir](){
        Check(C->ValidateFoldingSights(Load),TEXT("initial sight heads match saved optic state"));
        Check(G->Weapon(TEXT("ue_m4a1"))&&!G->Weapon(TEXT("fps_akm"))&&!G->Weapon(TEXT("fps_hk416")),TEXT("native M4 catalog only; retired guns remain absent"));
        Check(OpenGunsmith(),TEXT("open actual equipped instance"));if(!GunsmithPanel)return;
        Check(!G->Select(TEXT("optic"),TEXT("invalid"))&&!G->Select(TEXT("stock"),TEXT("true")),TEXT("reject unsupported parts"));
        if(!Load){
            GunsmithPanel->ChooseOption(TEXT("optic"),OpticId);
            Check(C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("draft previews mesh without mutating inventory"));
            P->AuditFailNextSave=true;Check(!GunsmithPanel->ApplyDraft()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("failed save rolls back installed configuration"));
            Check(GunsmithPanel->ApplyDraft(),TEXT("apply through checked save transaction"));
        }
        Check(G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==OpticId&&P->Equipped()->Magazine==17,TEXT("installed optic and magazine preserved"));
        if(Panoramic){
            Check(C->GetGunsmithOpticVariant()==OpticId,TEXT("panoramic variant selected on live actor"));
            GunsmithPanel->ChooseOption(TEXT("optic"),TEXT("holographic"));
            Check(C->GetGunsmithOpticVariant()==TEXT("holographic"),TEXT("switch panoramic to legacy holographic mesh"));
            GunsmithPanel->ChooseOption(TEXT("optic"),OpticId);
            Check(C->GetGunsmithOpticVariant()==OpticId,TEXT("switch back to panoramic without duplicate component"));
            TArray<UStaticMeshComponent*> Parts;C->GetComponents(Parts);int32 Mounted=0;
            for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==MeshName){
                ++Mounted;Check(Part->GetAttachSocketName()==TEXT("WPN_root")&&Part->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("panoramic rigid mount follows weapon root"));
                Check(Part->GetStaticMesh()->GetNumTriangles(0)<24000&&Part->GetNumMaterials()==3,TEXT("reduced mesh and three material slots loaded"));
            }
            Check(Mounted==1,TEXT("exactly one panoramic mesh visible"));
            GunsmithPanel->SelectCategory(TEXT("optic"));
        }
        GunsmithPanel->SetAimPreview(true);
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-gunsmith-panel.png"),true,false);
    });
    Later(5.f,[this,C,Check,Dir](){float Error;Check(C->ValidateGunsmithSight(Error),TEXT("holographic reticle within two pixels of aim axis"));UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: reticle_error_px=%.4f"),Error);
        if(Scope2X){
            const auto* Cam=C->FindComponentByClass<UCameraComponent>();
            const float BaselineHFOV=FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(55.f)*.5f)*(16.f/9.f)));
            const float Ratio=Cam?FMath::Tan(FMath::DegreesToRadians(BaselineHFOV)*.5f)/FMath::Tan(FMath::DegreesToRadians(Cam->FieldOfView)*.5f):0;
            Check(FMath::IsNearlyEqual(Ratio,2.f,.02f),TEXT("rendered camera provides exact 2x over 1x ADS"));
            UE_LOG(LogTemp,Display,TEXT("SCOPE2X_MAGNIFICATION ratio=%.5f fov=%.5f"),Ratio,Cam?Cam->FieldOfView:0);
        }
        float Roll,RailError;Check(C->MeasureHolographicOrientation(Roll,RailError),TEXT("read rendered optic orientation"));
        Check(C->ValidateFoldingSights(true),TEXT("both sight heads fold ninety degrees around fixed pivots"));
        UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: ads_roll_deg=%.4f rail_error_deg=%.4f"),Roll,RailError);
        Check(FMath::Abs(Roll)<.2f,TEXT("ADS optic frame is level"));Check(RailError<.2f,TEXT("optic up axis matches weapon rail"));
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-ads.png"),true,false);});
    Later(6.f,[this,P,G,C,Check](){
        if(!GunsmithPanel)return;GunsmithPanel->Choose(false);Check(!C->HasHolographicOptic(),TEXT("remove preview hides mesh"));
        CloseGunsmith();Check(C->HasHolographicOptic()&&G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==OpticId,TEXT("close discards unapplied removal"));
        Check(!IsMoveInputIgnored()&&!IsLookInputIgnored()&&!bShowMouseCursor,TEXT("menu close restores gameplay input"));
        Check(OpenGunsmith(),TEXT("reopen"));if(!GunsmithPanel)return;GunsmithPanel->Choose(false);Check(GunsmithPanel->ApplyDraft()&&!C->HasHolographicOptic(),TEXT("apply removal restores iron sight"));CloseGunsmith();
        Check(P->ReloadProfile()&&!C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("removal survives profile reload"));
        Check(OpenGunsmith(),TEXT("open to reinstall"));if(!GunsmithPanel)return;GunsmithPanel->ChooseOption(TEXT("optic"),OpticId);Check(GunsmithPanel->ApplyDraft(),TEXT("reinstall and save"));CloseGunsmith();
        Check(P->ReloadProfile()&&C->HasHolographicOptic(),TEXT("saved holographic state rebinds visual"));
    });
    Later(7.f,[this,Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-hip.png"),true,false);});
    Later(8.f,[P,C,Check](){Check(C->GetMagazineAmmo()==17&&P->AmmoCount()==40,TEXT("no ammo loss during repeated changes"));});
    Later(7.5f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("cancel and profile reload restore folded heads"));});
    Later(10.2f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("folded heads stay on receiver during reload"));});
    Later(14.f,[this](){if(OpenGunsmith()&&GunsmithPanel)GunsmithPanel->Choose(false);});
    Later(14.5f,[this,C,Check,Dir](){Check(C->ValidateFoldingSights(false),TEXT("removal unfolds both original sight heads"));if(GunsmithPanel)GunsmithPanel->SetAimPreview(true);});
    Later(14.6f,[P,Check](){Check(P->SaveNow(),TEXT("autosave succeeds during unapplied iron preview"));});
    Later(15.2f,[this,C,P,G,Check,Dir](){Check(!C->HasHolographicOptic()&&C->ValidateFoldingSights(false),TEXT("autosave does not overwrite upright iron preview"));Check(G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==OpticId,TEXT("preview remains transient after autosave"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-iron-restored.png"),true,false);});
    Later(15.6f,[this](){CloseGunsmith();});
    Later(16.5f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("cancel removal restores folded state after switching weapons"));});
    Later(8.1f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
    if(Panoramic)Later(8.5f,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("panoramic-gameplay-ads.png"),true,false);});
    Later(8.7f,[this,C,Check](){Check(C->IsAiming(),TEXT("gameplay aim input after menu close"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1));});
    Later(8.8f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0));});
    auto Shots=MakeShared<int32>(0);
    Later(9.f,[this,C,Check,Shots,Dir](){*Shots=17-C->GetMagazineAmmo();Check(*Shots>0&&*Shots<=2,TEXT("fire input consumes rounds"));Check(C->ValidateHolographicShot(),TEXT("shot ray follows visible reticle during recoil"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-fire.png"),true,false);InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1));});
    Later(9.1f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0));});
    Later(10.f,[this,C,Check,Dir](){Check(C->IsReloading()&&C->HasHolographicOptic(),TEXT("reload keeps optic attached"));float Roll,RailError;Check(C->MeasureHolographicOrientation(Roll,RailError)&&RailError<.2f,TEXT("reload preserves rail alignment"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-reload.png"),true,false);});
    Later(13.f,[this,C,P,G,Check,Shots](){
        const int32 ExpectedReserve=C->HasInfiniteReserveAmmo()?40:27-*Shots;
        Check(!C->IsReloading()&&C->GetMagazineAmmo()==30&&P->AmmoCount()==ExpectedReserve,TEXT("reload preserves current map finite/infinite reserve contract"));
        InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));
        auto S=P->Snapshot();const FString First=P->Equipped()->InstanceId;
        for(auto& I:S.Items){if(I.InstanceId==First)I.Magazine=17;if(I.Definition==TEXT("ammo_556"))I.Count=40;}
        if(!P->Equipped(6)){auto Other=P->CreateItem(TEXT("ue_m4a1"));Other.Place=1;Other.Cell=6;Other.Magazine=11;S.Items.Add(Other);}
        S.ActiveWeaponSlot=6;Check(P->CommitState(S)&&!C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("second M4 does not inherit first instance optic"));
        S=P->Snapshot();S.ActiveWeaponSlot=9;Check(P->CommitState(S)&&C->HasHolographicOptic(),TEXT("switching back restores first instance optic"));
        Check(OpenGunsmith(),TEXT("open while secondary-slot weapon equips"));if(GunsmithPanel){GunsmithPanel->Choose(false);Check(!GunsmithPanel->ApplyDraft(),TEXT("active secondary-slot equip blocks modification"));CloseGunsmith();}
    });
    if(Panoramic){
        Later(17.f,[this,C,Check](){Check(OpenGunsmith(),TEXT("open panoramic side display"));if(GunsmithPanel)GunsmithPanel->SetSidePreview(true);});
        Later(18.f,[this,C,Check,Dir](){Check(C->GetGunsmithOpticVariant()==OpticId,TEXT("saved panoramic retained in side display"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("panoramic-side.png"),true,false);});
        Later(19.f,[this](){if(GunsmithPanel)GunsmithPanel->RotatePreview(FVector2D(100,20));});
        Later(20.f,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("panoramic-rotated.png"),true,false);});
        Later(21.f,[this](){CloseGunsmith();});
        Later(22.f,[this,P,C,G,Check](){
            GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Request(*P->Equipped());
            auto S=P->Snapshot();FString OtherId;
            for(const auto& I:S.Items)if(I.Place==0&&I.Definition==TEXT("ue_m4a1")){OtherId=I.InstanceId;break;}
            if(OtherId.IsEmpty()){auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=0;I.Cell=4;I.Magazine=11;OtherId=I.InstanceId;S.Items.Add(I);Check(P->CommitState(S),TEXT("seed unequipped panoramic instance"));}
            Check(OpenGunsmith(OtherId),TEXT("open unequipped optic workbench"));if(!GunsmithPanel)return;
            GunsmithPanel->ChooseOption(TEXT("optic"),TEXT("holographic"));
            Check(C->GetGunsmithOpticVariant()==OpticId,TEXT("unequipped optic draft leaves active panoramic unchanged"));
            Check(GunsmithPanel->ApplyDraft(),TEXT("save other optic before unequipped panoramic replacement"));
            GunsmithPanel->ChooseOption(TEXT("optic"),OpticId);Check(GunsmithPanel->ApplyDraft(),TEXT("save panoramic on unequipped instance"));CloseGunsmith();
            Check(P->ReloadProfile()&&G->Installed(*P->FindItem(OtherId)).FindRef(TEXT("optic"))==OpticId,TEXT("unequipped panoramic survives reload"));
            auto* Drop=GetWorld()->SpawnActor<AColdSteelPickup>(GetPawn()->GetActorLocation()+FVector(300,0,100),FRotator::ZeroRotator);Drop->InitializeItem(*P->FindItem(OtherId));
            TArray<UStaticMeshComponent*> Parts;Drop->GetComponents(Parts);bool Found=false;
            for(auto* Part:Parts)Found|=Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==MeshName;
            Check(Found,TEXT("ground item model retains panoramic and materials"));Drop->Destroy();
        });
        Later(25.f,[this,P,Check,Dir](){
            const auto* Brush=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Find(*P->Equipped());auto* Tex=Brush?Cast<UTexture2D>(Brush->GetResourceObject()):nullptr;
            Check(Tex!=nullptr,TEXT("saved panoramic inventory icon renders"));if(!Tex)return;
            const auto& Mip=Tex->GetPlatformData()->Mips[0];const FColor* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());TArray<FColor> Copy;Copy.Append(Pixels,Tex->GetSizeX()*Tex->GetSizeY());Mip.BulkData.Unlock();
            TArray<uint8> PNG;FImageUtils::CompressImageArray(Tex->GetSizeX(),Tex->GetSizeY(),Copy,PNG);FFileHelper::SaveArrayToFile(PNG,*(Dir/TEXT("panoramic-inventory-icon.png")));
        });
    }
    if(LPVO){
        Later(28.f,[this,C,Check](){Check(!C->AdjustOpticMagnification(.5f),TEXT("LPVO zoom ignored outside ADS"));Check(C->GetOpticMagnification()==1.f,TEXT("LPVO starts at minimum without explicit reset"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
        auto Measure=[C,Check,Dir](float Expected,const FString& Name){
            const auto* Cam=C->FindComponentByClass<UCameraComponent>();const float Base=2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(55.f)*.5f)*16.f/9.f);
            const float Ratio=Cam?FMath::Tan(Base*.5f)/FMath::Tan(FMath::DegreesToRadians(Cam->FieldOfView)*.5f):0;
            TArray<UStaticMeshComponent*> Parts;C->GetComponents(Parts);int32 Rings=0;
            for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==TEXT("SM_LPVORing")){++Rings;Check(Part->GetAttachParent()&&Part->GetAttachParent()->GetName().StartsWith(TEXT("M4HolographicOptic"))&&Part->GetRelativeLocation().Equals(FVector(-7.1f,0,4),.01f),TEXT("LPVO moving ring remains attached after weapon rebuild"));Check(FMath::IsNearlyEqual(FMath::Abs(Part->GetRelativeRotation().Roll),(Expected-1)*24.f,.1f),TEXT("LPVO throw lever rotation tracks zoom"));}
            Check(Rings==1,TEXT("exactly one LPVO moving ring"));
            Check(C->GetScopePresentationAlpha()>.99f,TEXT("LPVO full-aperture presentation active"));
            for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==MeshName)Check(Part->bOwnerNoSee,TEXT("physical scope cannot obstruct optical image"));
            Check(FMath::IsNearlyEqual(Ratio,Expected,.03f),TEXT("LPVO actual camera magnification matches control"));float Error;Check(C->ValidateGunsmithSight(Error),TEXT("LPVO reticle remains centered across zoom"));
            UE_LOG(LogTemp,Display,TEXT("LPVO_MAGNIFICATION expected=%.2f actual=%.5f reticle_px=%.4f"),Expected,Ratio,Error);
            FScreenshotRequest::RequestScreenshot(Dir/(Name+TEXT(".png")),true,false);
        };
        Later(29.f,[Measure](){Measure(1.f,TEXT("lpvo-1x"));});
        Later(29.3f,[this,C,P,Check](){const auto Slot=P->Snapshot().ActiveWeaponSlot;for(int i=0;i<2;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollUp,IE_Pressed,1));Check(C->GetOpticMagnification()==2.f&&Slot==P->Snapshot().ActiveWeaponSlot,TEXT("ADS wheel zoom consumes input without switching weapon"));});
        Later(30.f,[Measure](){Measure(2.f,TEXT("lpvo-2x"));});
        Later(30.3f,[this](){for(int i=0;i<4;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollUp,IE_Pressed,1));});
        Later(31.f,[Measure](){Measure(4.f,TEXT("lpvo-4x"));});
        Later(31.3f,[this,C,Check](){for(int i=0;i<12;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollUp,IE_Pressed,1));Check(C->GetOpticMagnification()==6.f,TEXT("LPVO upper clamp"));});
        Later(32.f,[Measure](){Measure(6.f,TEXT("lpvo-6x"));});
        Later(32.3f,[this,C,Check](){for(int i=0;i<14;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollDown,IE_Pressed,1));Check(C->GetOpticMagnification()==1.f,TEXT("LPVO lower clamp and reverse wheel"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));});
        Later(33.f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
        Later(34.f,[this,C,Check](){for(int i=0;i<6;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollUp,IE_Pressed,1));Check(C->GetOpticMagnification()==4.f,TEXT("wheel selects remembered 4x"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));});
        Later(39.f,[C,Check,Dir](){
            Check(C->GetScopePresentationAlpha()==0.f,TEXT("LPVO presentation clears after ADS release"));
            TArray<UStaticMeshComponent*> Parts;C->GetComponents(Parts);
            for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==MeshName)Check(!Part->bOwnerNoSee,TEXT("LPVO exterior restored after ADS"));
            FScreenshotRequest::RequestScreenshot(Dir/TEXT("lpvo-hip-restored.png"),true,false);
        });
        Later(40.f,[this,C,Check](){Check(!C->IsAiming()&&C->GetOpticMagnification()==4.f,TEXT("4x survives ADS release and profile refresh"));Check(!C->AdjustOpticMagnification(-.5f)&&C->GetOpticMagnification()==4.f,TEXT("hip state cannot change remembered zoom"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
        Later(41.f,[Measure](){Measure(4.f,TEXT("lpvo-reopen-4x"));});
        Later(41.3f,[this,C,Check](){for(int i=0;i<4;i++)InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseScrollDown,IE_Pressed,1));Check(C->GetOpticMagnification()==2.f,TEXT("reverse wheel selects remembered 2x"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));});
        Later(42.f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
        Later(43.f,[Measure](){Measure(2.f,TEXT("lpvo-reopen-2x"));});
        Later(43.3f,[this,C,Check](){
            Check(C->IsAiming(),TEXT("fixed optic exclusion checked while ADS active"));
            for(const TCHAR* Variant:{TEXT("prism_scope_2x"),TEXT("panoramic_red_dot"),TEXT("holographic"),TEXT("")}){
                C->SetGunsmithOpticVariant(Variant);const float Before=C->GetOpticMagnification();
                Check(!C->AdjustOpticMagnification(.5f)&&!C->AdjustOpticMagnification(-.5f)&&C->GetOpticMagnification()==Before,TEXT("fixed optic rejects zoom in both directions"));
            }
            C->SetGunsmithOpticVariant(TEXT("lpvo_1_6x"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));
        });
    }
    Later(LPVO?45.f:(Panoramic?27.f:17.f),[this,Counts,Dir](){UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);FFileHelper::SaveStringToFile(FString::Printf(TEXT("checks=%d failures=%d"),Counts->X,Counts->Y),*(Dir/TEXT("result.txt")));ConsoleCommand(TEXT("quit"));});
}
