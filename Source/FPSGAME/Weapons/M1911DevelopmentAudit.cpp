#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "M1911WeaponAssets.h"
#include "GunsmithSystem.h"
#include "FPSGunplayAnimInstance.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWeaponIcons.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/M4GunsmithWidget.h"
#include "../WeatherViewEffectsComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/GameInstance.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Camera/CameraComponent.h"
#include "ImageUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "UObject/UObjectIterator.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
UM4GunsmithWidget* FindM1911AuditPanel(APlayerController* PC)
{
    for(TObjectIterator<UM4GunsmithWidget> It;It;++It)
        if(It->GetOwningPlayer()==PC&&It->IsInViewport())return *It;
    return nullptr;
}
}


// Explicit -M1911Audit only. Every write is guarded by a distinct audit save
// slot; the second process (-M1911AuditLoad) reads the first process's result.
void AFPSGAMECharacter::RunM1911DevelopmentAudit()
{
    static bool Started=false;
    if(Started||GetWorld()->GetTimeSeconds()<6.f||!GetController())return;
    Started=true;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* PC=Cast<AFPSGAMEPlayerController>(GetController());
    if(!P||!G||!PC||!P->IsAudit()||!P->ProfileSlot().StartsWith(TEXT("ColdSteel_M1911Audit_")))
    {UE_LOG(LogTemp,Error,TEXT("M1911_AUDIT: isolated named profile required"));FPlatformMisc::RequestExitWithStatus(false,2);return;}
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("M1911Audit")/P->ProfileSlot();
    IFileManager::Get().MakeDirectory(*Dir,true);
    struct FRun {int32 Checks=0,Failures=0,Shots=0,Reserve=0;FString Rows;};
    auto R=MakeShared<FRun>();
    auto Check=[R](bool Pass,const FString& Name){++R->Checks;if(!Pass)++R->Failures;
        R->Rows+=FString::Printf(TEXT("%s\t%s\n"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);
        UE_LOG(LogTemp,Display,TEXT("M1911_AUDIT: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);};
    const bool Load=FParse::Param(FCommandLine::Get(),TEXT("M1911AuditLoad"));
    auto Finish=[R,Dir,Load](){
        const FString Result=FString::Printf(TEXT("checks=%d failures=%d\n"),R->Checks,R->Failures)+R->Rows;
        FFileHelper::SaveStringToFile(Result,*(Dir/(Load?TEXT("load-result.txt"):TEXT("result.txt"))));
        UE_LOG(LogTemp,Display,TEXT("M1911_AUDIT: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);
        FPlatformMisc::RequestExitWithStatus(false,R->Failures?1:0);};
    auto Later=[this](float Seconds,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},Seconds,false);};
    if(Load)
    {
        Check(P->Equipped()&&P->Equipped()->Definition==TEXT("ue_m1911"),TEXT("new process restores pistol instance"));
        if(P->Equipped()){
            const auto Parts=G->Installed(*P->Equipped());
            Check(Parts.FindRef(TEXT("optic"))==TEXT("panoramic_red_dot")&&Parts.FindRef(TEXT("muzzle"))==TEXT("true")
                &&Parts.FindRef(TEXT("tactical"))==TEXT("laser")&&Parts.FindRef(TEXT("trigger"))==TEXT("m1911_lightweight_fast"),TEXT("new process restores string and boolean parts"));
            Check(bUseM1911&&bHolographicOptic&&IsMuzzleSuppressed()&&MagazineAmmo==7,TEXT("saved parts and ammo reach runtime"));
        }
        Finish();return;
    }
    auto State=P->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    for(auto& A:State.Attributes)A.Value=0;
    auto Gun=P->CreateItem(TEXT("ue_m1911"));Gun.Place=1;Gun.Cell=9;Gun.Magazine=3;State.Items.Add(Gun);State.ActiveWeaponSlot=9;
    auto Ammo=P->CreateItem(TEXT("ammo_45acp"),70);Ammo.Cell=0;State.Items.Add(Ammo);
    if(!P->CommitState(State)){Check(false,TEXT("seed valid isolated pistol and ammo"));Finish();return;}
    Check(bUseM1911&&AKMViewmodel->GetSkeletalMeshAsset()&&AKMViewmodel->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/RearFinish20260913/")),TEXT("current refined receiver is runtime mesh"));
    if(FParse::Param(FCommandLine::Get(),TEXT("M1911MeasureBounds")))
    {
        // Offline audit measurement only, never a per-frame gameplay skin readback.
        auto* Probe=NewObject<USkeletalMeshComponent>(this);
        Probe->SetSkeletalMeshAsset(AKMViewmodel->GetSkeletalMeshAsset());
        Probe->SetVisibility(false);Probe->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Probe->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Probe->RegisterComponent();
        const auto& LOD=Probe->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        auto* Weights=Probe->GetSkinWeightBuffer(0);FBox Envelope(ForceInit);int32 Samples=0;
        for(const TCHAR* Name:{TEXT("idle"),TEXT("aim"),TEXT("idle_empty"),TEXT("aim_empty"),TEXT("fire"),TEXT("aim_fire"),TEXT("fire_last"),TEXT("aim_fire_last"),TEXT("reload"),TEXT("reload_empty"),TEXT("equip_charge"),TEXT("equip_charge_empty")})
        {
            auto* Clip=LoadObject<UAnimSequence>(nullptr,*M1911WeaponAssets::AnimationPath(Name));if(!Clip||!Weights)continue;
            Probe->PlayAnimation(Clip,false);
            const int32 Steps=FMath::Max(1,FMath::CeilToInt(Clip->GetPlayLength()*60));
            for(int32 Step=0;Step<=Steps;++Step){
                Probe->SetPosition(Clip->GetPlayLength()*Step/Steps,false);Probe->TickAnimation(0,false);Probe->RefreshBoneTransforms();
                TArray<FMatrix44f> Matrices;Probe->GetCurrentRefToLocalMatrices(Matrices,0);
                for(const auto& Section:LOD.RenderSections)for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
                    Envelope+=FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Probe,V,LOD,*Weights,Matrices));
                ++Samples;
            }
        }
        const auto Ref=Probe->GetSkeletalMeshAsset()->GetBounds();
        const FVector Required=(Envelope.GetCenter()-Ref.Origin).GetAbs()+Envelope.GetExtent();
        const float BoxScale=FMath::Max3(float(Required.X/Ref.BoxExtent.X),float(Required.Y/Ref.BoxExtent.Y),float(Required.Z/Ref.BoxExtent.Z));
        const float SphereScale=float(((Envelope.GetCenter()-Ref.Origin).Size()+Envelope.GetExtent().Size())/Ref.SphereRadius);
        const float Scale=FMath::CeilToFloat(FMath::Max3(1.f,BoxScale,SphereScale)*1.1f*100.f)/100.f;
        const FString Measurement=FString::Printf(TEXT("samples=%d scale=%.2f\nreference=%s\nenvelope=%s\n"),Samples,Scale,*Ref.ToString(),*Envelope.ToString());
        FFileHelper::SaveStringToFile(Measurement,*(Dir/TEXT("measured-bounds.txt")));UE_LOG(LogTemp,Display,TEXT("M1911_BOUNDS_MEASURE %s"),*Measurement);
        auto Installed=Ref;Installed.BoxExtent*=M1911WeaponAssets::ViewmodelBoundsScale;Installed.SphereRadius*=M1911WeaponAssets::ViewmodelBoundsScale;
        Check(Installed.GetBox().IsInside(Envelope)&&SphereScale<=M1911WeaponAssets::ViewmodelBoundsScale,TEXT("installed viewmodel bounds enclose all sampled actions"));
        Probe->DestroyComponent();
    }
    for(const TCHAR* Name:{TEXT("idle"),TEXT("aim"),TEXT("idle_empty"),TEXT("aim_empty"),TEXT("fire"),TEXT("aim_fire"),TEXT("fire_last"),TEXT("aim_fire_last"),TEXT("reload"),TEXT("reload_empty"),TEXT("equip_charge"),TEXT("equip_charge_empty")})
    {
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*M1911WeaponAssets::AnimationPath(Name));
        Check(Clip&&Clip->GetPlayLength()>0&&Clip->GetSkeleton(),FString(TEXT("load action "))+Name);
    }
    Check(FMath::IsNearlyEqual(ReloadDuration,1.75f,.001f)&&FMath::IsNearlyEqual(EmptyReloadDuration,2.25f,.001f),TEXT("stats read current 1.75/2.25 second clips"));
    Check(G->Calculate(TEXT("ue_m1911"),{{TEXT("trigger"),TEXT("m1911_lightweight_fast")}}).Interval==G->Weapon(TEXT("ue_m1911"))->Base.Interval*.75,TEXT("fast trigger multiplies interval by .75"));
    Check(!G->Option(TEXT("ue_m1911"),TEXT("magazine"),TEXT("large_drum"))&&!G->Option(TEXT("ue_m1911"),TEXT("stock"),TEXT("compact")),TEXT("rifle drum and stock remain unsupported"));
    for(const TCHAR* Bone:{TEXT("WPN_root"),TEXT("WPN_Slide"),TEXT("WPN_Barrel"),TEXT("WPN_RearSight"),TEXT("WPN_FrontSight"),TEXT("WPN_SOCKET_Muzzle")})
        Check(AKMViewmodel->DoesSocketExist(Bone),FString(TEXT("mechanical frame "))+Bone);
    Later(1,[this,Check,R](){
        StartEquipCharge();AimPressed();Check(WeaponState==EAKMWeaponState::Idle&&IsAiming()&&!ActiveActionAnimation,TEXT("ADS immediately interrupts pistol equip"));
        AimReleased();StartEquipCharge();R->Shots=ShotsFired;FirePressed();
        Check(WeaponState==EAKMWeaponState::Idle&&ShotsFired==R->Shots+1,TEXT("fire immediately interrupts pistol equip"));
    });
    Later(1.6f,[this,P,Check,R](){
        Check(ShotsFired==R->Shots+1,TEXT("held trigger remains semiautomatic"));FireReleased();
        MagazineAmmo=4;P->SaveNow();R->Reserve=ReserveAmmo;ReloadPressed();
        Check(IsReloading()&&FMath::IsNearlyEqual(WeaponStateDuration,ReloadAnimation->GetPlayLength(),.001f)
            &&FMath::IsNearlyEqual(ActionDuration,WeaponStateDuration,.001f),TEXT("normal reload state and action share clip duration"));
        AimPressed();FirePressed();Check(IsReloading()&&!IsAiming(),TEXT("reload cannot be interrupted by pistol equip exception"));FireReleased();AimReleased();
    });
    Later(2.1f,[this,Check](){Check(IsReloading()&&GunplayAnimation&&FMath::Abs(GunplayAnimation->ActionTime-ReloadSourceTime(WeaponStateElapsed))<.08f,TEXT("normal pose samples business reload clock"));});
    Later(3.6f,[this,P,Check,R](){
        Check(!IsReloading()&&MagazineAmmo==7&&!ActiveActionAnimation,TEXT("normal reload completes without ready tail"));
        Check(HasInfiniteReserveAmmo()||ReserveAmmo==R->Reserve-3,TEXT("normal reload consumes exactly missing ammunition"));
        MagazineAmmo=1;P->SaveNow();FirePressed();FireReleased();
        Check(MagazineAmmo==0&&ActiveActionAnimation==PistolFireLastAnimation,TEXT("last round uses locked-slide fire action"));
    });
    Later(4.2f,[this,Check,R](){
        Check(GunplayAnimation&&GunplayAnimation->IdleClip==PistolIdleEmptyAnimation,TEXT("empty idle uses locked-slide pose"));
        R->Reserve=ReserveAmmo;ReloadPressed();
        Check(IsReloading()&&FMath::IsNearlyEqual(WeaponStateDuration,ReloadEmptyAnimation->GetPlayLength(),.001f),TEXT("empty reload uses actual empty clip length"));
        Check(MechanicalCueTimes.Num()==4&&MechanicalCueTimes.Last()<ReloadEmptyAnimation->GetPlayLength(),TEXT("slide release and magazine cues lie inside source clip"));
    });
    Later(4.8f,[this,Check,Dir](){
        Check(IsReloading()&&GunplayAnimation&&FMath::Abs(GunplayAnimation->ActionTime-ReloadSourceTime(WeaponStateElapsed))<.08f,TEXT("empty pose samples business reload clock"));
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("empty-reload.png"),false,false);
    });
    Later(6.7f,[this,Check,R](){
        Check(!IsReloading()&&MagazineAmmo==7&&!ActiveActionAnimation,TEXT("empty reload completes without ready tail"));
        Check(HasInfiniteReserveAmmo()||ReserveAmmo==R->Reserve-7,TEXT("empty reload consumes one magazine exactly"));
    });
    Later(7,[this,P,G,PC,Check](){
        Check(PC->OpenGunsmith(),TEXT("open real gunsmith panel"));auto* Panel=FindM1911AuditPanel(PC);if(!Panel)return;
        Check(G->Weapon(TEXT("ue_m1911"))->Allowed.Contains(Panel->SelectedCategory),TEXT("default category is supported by pistol"));
        for(const TCHAR* Part:{TEXT("holographic"),TEXT("panoramic_red_dot")}){
            Panel->ChooseOption(TEXT("optic"),Part);ApplyColdSteelProfile(P);
            Check(HolographicOptic&&HolographicOptic->IsVisible()&&HolographicOptic->GetAttachSocketName()==TEXT("WPN_Slide"),FString(TEXT("optic fitted to slide "))+Part);
            if(HolographicOptic){
                UStaticMesh* Mesh=HolographicOptic->GetStaticMesh();
                Check(Mesh&&HolographicOptic->GetMaterial(0)==Mesh->GetMaterial(0),TEXT("optic swap clears prior material overrides"));
                if(Mesh)HolographicOptic->SetMaterial(0,UMaterialInstanceDynamic::Create(Mesh->GetMaterial(0),this));
            }
        }
        Panel->ChooseOption(TEXT("optic"),TEXT("false"));ApplyColdSteelProfile(P);
        Check(!HolographicOptic||!HolographicOptic->IsVisible(),TEXT("factory optic remains hidden after profile refresh"));
        for(const TCHAR* Part:{TEXT("true"),TEXT("brake"),TEXT("false")}){
            Panel->ChooseOption(TEXT("muzzle"),Part);ApplyColdSteelProfile(P);
            if(FString(Part)==TEXT("false"))Check(!MuzzleAttachment&&!IsMuzzleSuppressed(),TEXT("factory destroys muzzle and restores unsuppressed state"));
            else {
                Check(MuzzleAttachment&&MuzzleAttachment->IsVisible()&&MuzzleAttachment->GetAttachSocketName()==TEXT("WPN_Barrel"),FString(TEXT("muzzle follows barrel "))+Part);
                const FVector Axis=(AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"))-AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
                Check(FVector::DotProduct(Axis,GetEffectiveMuzzleForward())>.99f&&FVector::DotProduct(GetEffectiveMuzzleLocation()-AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle")),Axis)>2.f,TEXT("muzzle exit extends forward from bore"));
            }
        }
        for(const TCHAR* Part:{TEXT("laser"),TEXT("flashlight"),TEXT("false")}){
            Panel->ChooseOption(TEXT("tactical"),Part);ApplyColdSteelProfile(P);UStaticMeshComponent* Body=nullptr;
            for(auto* C:TInlineComponentArray<UStaticMeshComponent*>(this))if(C->GetName().StartsWith(TEXT("TacticalDeviceBody")))Body=C;
            Check(Body&&(Body->IsVisible()==(FString(Part)!=TEXT("false"))),FString(TEXT("tactical visibility after profile refresh "))+Part);
            if(Body&&FString(Part)!=TEXT("false"))Check(Body->DoesSocketExist(TEXT("Emitter"))&&Body->DoesSocketExist(TEXT("AimGuide")),TEXT("tactical emitter and aim guide exist"));
        }
        Panel->ChooseOption(TEXT("optic"),TEXT("panoramic_red_dot"));Panel->ChooseOption(TEXT("muzzle"),TEXT("true"));
        Panel->ChooseOption(TEXT("tactical"),TEXT("laser"));Panel->ChooseOption(TEXT("trigger"),TEXT("m1911_lightweight_fast"));
        Check(G->Installed(*P->Equipped()).IsEmpty(),TEXT("preview does not mutate installed parts"));
        P->AuditFailNextSave=true;Check(!Panel->ApplyDraft()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("failed save rolls back parts"));
        Check(Panel->ApplyDraft()&&MagazineAmmo==7,TEXT("apply saves configured pistol without ammo change"));
        Check(FMath::IsNearlyEqual(FireInterval,.135f,.0001f),TEXT("fast trigger reaches runtime interval"));
        auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();Icons->Request(*P->Equipped());
        MagazineAmmo=0;UpdateActionPose(0);Check(GunplayAnimation&&GunplayAnimation->IdleClip==IdleAnimation,TEXT("empty inventory previews closed slide without ammo refill"));MagazineAmmo=7;
        Panel->SetSidePreview(true);
    });
    auto Capture=[PC,Check,Dir](const FString& Name){
        auto* Panel=FindM1911AuditPanel(PC);if(!Panel){Check(false,TEXT("panel available for capture"));return;}
        FScreenshotRequest::RequestScreenshot(Dir/(Name+TEXT("-panel.png")),true,false);
        TArray<FColor> Pixels;
        if(Panel->PreviewTarget&&Panel->PreviewTarget->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)){
            TArray64<uint8> Png;FImageUtils::PNGCompressImageArray(Panel->PreviewTarget->SizeX,Panel->PreviewTarget->SizeY,TArrayView64<const FColor>(Pixels),Png);FFileHelper::SaveArrayToFile(Png,*(Dir/(Name+TEXT("-studio.png"))));
            Check(Pixels.ContainsByPredicate([](const FColor& C){return C.R>30||C.G>30||C.B>30;}),Name+TEXT(" rendered pixels present"));
        }else Check(false,Name+TEXT(" render target readback"));
        bool Body=false;for(const auto& Pair:Panel->StudioCopies)if(auto* C=Cast<USkeletalMeshComponent>(Pair.Value))Body|=C->IsVisible()&&C->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/M1911/"));
        Check(Body,Name+TEXT(" studio retains receiver component"));
    };
    Later(10,[Capture](){Capture(TEXT("suppressed-side"));});
    Later(11,[PC](){if(FindM1911AuditPanel(PC))FindM1911AuditPanel(PC)->SetAimPreview(true);});
    Later(13,[this,Capture,Check](){Capture(TEXT("suppressed-ads"));float Error=0;Check(ValidateGunsmithSight(Error),FString::Printf(TEXT("red dot aim error %.3f px"),Error));});
    Later(14,[this,P,G,PC,Check](){
        if(!FindM1911AuditPanel(PC))return;FindM1911AuditPanel(PC)->SetSidePreview(true);FindM1911AuditPanel(PC)->ChooseOption(TEXT("muzzle"),TEXT("brake"));
        Check(!IsMuzzleSuppressed(),TEXT("brake uses normal shot sound and effects"));
        FindM1911AuditPanel(PC)->UndoDraft();Check(IsMuzzleSuppressed(),TEXT("undo restores saved suppressor"));
        PC->CloseGunsmith();Check(P->ReloadProfile()&&G->Installed(*P->Equipped()).FindRef(TEXT("muzzle"))==TEXT("true"),TEXT("saved configuration reloads"));
        auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();Check(Icons->Find(*P->Equipped())!=nullptr,TEXT("configured inventory icon rendered"));
        auto* Pickup=GetWorld()->SpawnActor<AColdSteelPickup>();Pickup->InitializeItem(*P->Equipped());
        Check(Pickup->Weapon&&Pickup->Weapon->GetSkinnedAsset(),TEXT("dropped pistol builds posed weapon"));Pickup->Destroy();
        for(const TCHAR* Folder:{TEXT("RainVisibility"),TEXT("NaturalV2")}){
            auto* Weather=LoadObject<UWeatherPresentationAssets>(nullptr,*FString::Printf(TEXT("/Game/Weather/%s/DA_WeatherPresentation"),Folder));
            Check(Weather!=nullptr,FString(TEXT("weather catalog "))+Folder);if(!Weather)continue;
            bool Rear=false,Tactical=false;
            for(const auto& Pair:Weather->WetMaterials){Rear|=Pair.Key.Contains(TEXT("M1911"))&&Pair.Key.Contains(TEXT("Rear"))&&Pair.Value;Tactical|=Pair.Key.Contains(TEXT("M1911"))&&Pair.Key.Contains(TEXT("laser"))&&Pair.Value;}
            Check(Rear&&Tactical,TEXT("pistol rear and tactical wet-material mappings resolve"));
        }
    });
    Later(16,[this,Dir,Check](){
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("final-idle.png"),false,false);
        Check(AKMViewmodel->IsVisible()&&!bGunsmithInspection&&AKMViewmodel->Bounds.GetBox().IsInside(AKMViewmodel->GetSocketLocation(TEXT("WPN_root"))),TEXT("closed workbench restores live receiver inside culling bounds"));
        UE_LOG(LogTemp,Display,TEXT("M1911_LIVE_BOUNDS visible=%d hidden=%d inspection=%d bounds=%s root=%s pose=%s"),
            AKMViewmodel->IsVisible(),AKMViewmodel->bHiddenInGame,bGunsmithInspection,*AKMViewmodel->Bounds.ToString(),
            *AKMViewmodel->GetSocketLocation(TEXT("WPN_root")).ToString(),*AKMViewmodel->GetComponentTransform().ToString());
    });
    Later(18,Finish);
}
