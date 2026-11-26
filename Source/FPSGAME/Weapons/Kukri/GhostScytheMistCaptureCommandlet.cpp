#include "GhostScytheMistCaptureCommandlet.h"
#include "GhostScytheMist.h"
#include "KukriRhythm.h"
#include "KukriOffhandDraw.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "../ModularSwordVisual.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/TextureCube.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "FXSystem.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSystem.h"
#include "GameFramework/Actor.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"

int32 UGhostScytheMistCaptureCommandlet::Main(const FString& Params)
{
    FString Out=FPaths::ProjectSavedDir()/TEXT("GhostScytheMistDiagnosis");
    FParse::Value(*Params,TEXT("Out="),Out);IFileManager::Get().MakeDirectory(*Out,true);
    auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("GhostMistInspection"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    // Commandlet worlds omit the FX system even with a rendering RHI. Use the same dispatch as a live preview scene.
    World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    World->InitializeActorsForPlay(FURL());FlushRenderingCommands();
    if(!FNiagaraGpuComputeDispatchInterface::Get(World))return 6;
    AActor* Owner=World->SpawnActor<AActor>();
    auto* Blade=NewObject<UStaticMeshComponent>(Owner);Owner->SetRootComponent(Blade);Owner->AddInstanceComponent(Blade);
    Blade->SetMobility(EComponentMobility::Movable);Blade->SetOnlyOwnerSee(true);Blade->RegisterComponent();
    FColdSteelItem Item;Item.Definition=TEXT("ue_tactical_hatchet");Item.InstanceId=TEXT("ghost-mist-inspection");
    Item.Data=TEXT("{\"gunsmith_parts\":{\"blade_1\":\"hatchet_ghost_scythe\"}}");
    if(!ColdSteelModularSword::Apply(Blade,Item))return 2;
    auto* Fx=Cast<UInstancedStaticMeshComponent>(GhostScytheMist::Find(Blade));if(!Fx)return 3;
    auto* Light=NewObject<UDirectionalLightComponent>(Owner);Owner->AddInstanceComponent(Light);Light->SetIntensity(4.f);
    Light->SetWorldRotation(FRotator(-42,25,0));Light->RegisterComponent();
    auto* Sky=NewObject<USkyLightComponent>(Owner);Owner->AddInstanceComponent(Sky);
    Sky->SourceType=SLS_SpecifiedCubemap;
    Sky->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap")));
    Sky->SetIntensity(1.2f);Sky->SetMobility(EComponentMobility::Movable);Sky->RegisterComponent();
    USkyLightComponent::UpdateSkyCaptureContents(World);FlushRenderingCommands();
    constexpr int W=960,H=540;
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->RenderTargetFormat=RTF_RGBA8;RT->ClearColor=FLinearColor(.014f,.016f,.018f,1);
    RT->InitAutoFormat(W,H);RT->UpdateResourceImmediate(true);
    auto* Camera=NewObject<UGhostScytheOwnerCapture>(Owner);Owner->AddInstanceComponent(Camera);Camera->RegisterComponent();
    Camera->TextureTarget=RT;Camera->CaptureSource=SCS_FinalColorLDR;Camera->FOVAngle=62;
    Camera->SetWorldLocationAndRotation(FVector(9,-48,20),FRotator(0,90,0));
    Camera->bCaptureEveryFrame=Camera->bCaptureOnMovement=false;
    Camera->ShowFlags.SetTemporalAA(false);Camera->ShowFlags.SetAntiAliasing(false);Camera->ShowFlags.SetMotionBlur(false);
    Camera->ShowFlags.SetAtmosphere(false);Camera->ShowFlags.SetFog(false);Camera->ShowFlags.SetBloom(false);
    Camera->PostProcessSettings.bOverride_AutoExposureMethod=true;Camera->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Camera->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Camera->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Camera->PostProcessSettings.AmbientCubemap=LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"));
    Camera->PostProcessSettings.bOverride_AmbientCubemapIntensity=true;Camera->PostProcessSettings.AmbientCubemapIntensity=.85f;
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto* RigOwner=World->SpawnActor<AActor>();auto* Arms=NewObject<USkeletalMeshComponent>(RigOwner);
    RigOwner->SetRootComponent(Arms);RigOwner->AddInstanceComponent(Arms);Arms->SetVisibility(false);
    Arms->SetSkeletalMeshAsset(LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh));
    Arms->SetWorldRotation(FRotator(0,90,0));Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCastShadow(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    auto Capture=[&](const FString& Name)
    {
        World->SendAllEndOfFrameUpdates();
        for(int32 I=0;I<3;++I){Camera->CaptureScene();FlushRenderingCommands();}
        TArray<FColor> Pixels;RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);
        if(Pixels.Num()==W*H)
        {
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(W,H,Pixels,PNG);
            FFileHelper::SaveArrayToFile(PNG,*(Out/(Name+TEXT(".png"))));
        }
        return Pixels;
    };
    int32 Detected=0;FString Report;
    for(int32 View=0;View<4;++View)
    {
        const bool Left=(View%2)!=0;
        if(View<2)Blade->SetWorldScale3D(FVector(1,Left?-1:1,1));
        else
        {
            auto* Idle=LoadObject<UAnimSequence>(nullptr,Left?TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle.A_Kukri_DualIdle"):
                TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_Idle.A_Kukri_Idle"));
            if(!Idle||!Arms->GetSkeletalMeshAsset())return 5;
            Arms->SetVisibility(true);
            Arms->PlayAnimation(Idle,true);Arms->SetPlayRate(0.f);Arms->SetPosition(.1f,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
            Blade->SetWorldTransform(Left?KukriOffhandDraw::Grip()*Arms->GetSocketTransform(TEXT("hand_l")):
                FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f))*Arms->GetSocketTransform(TEXT("WPN_root")));
            Camera->SetWorldLocationAndRotation(FVector::ZeroVector,FRotator::ZeroRotator);Camera->FOVAngle=90;
        }
        GhostScytheMist::MatchVisibility(Blade);
        for(int32 Frame=0;Frame<75;++Frame){++GFrameCounter;World->Tick(LEVELTICK_All,1.f/60);World->SendAllEndOfFrameUpdates();}
        const int32 Count=Fx->GetInstanceCount();
        FString Side=View<2?TEXT("side-"):TEXT("idle-");Side+=Left?TEXT("offhand"):TEXT("main");
        auto On=Capture(Side+TEXT("-on"));Fx->SetVisibility(false);auto Off=Capture(Side+TEXT("-off"));Fx->SetVisibility(true);
        int32 RedPixels=0,Strong=0,MaxRed=0;
        for(int32 I=0;I<FMath::Min(On.Num(),Off.Num());++I)
        {
            const int R=int(On[I].R)-Off[I].R,G=int(On[I].G)-Off[I].G;
            if(R>G+3&&R>=4)++RedPixels;
            if(R>G+10&&R>=14)++Strong;
            MaxRed=FMath::Max(MaxRed,R);
        }
        Report+=FString::Printf(TEXT("%s wisps=%d red_pixels=%d strong=%d max_red=%d\n"),*Side,Count,RedPixels,Strong,MaxRed);
        if(Count>0&&Strong>30)++Detected;
    }
    FFileHelper::SaveStringToFile(Report,*(Out/TEXT("result.txt")));UE_LOG(LogTemp,Display,TEXT("GHOST_MIST_CAPTURE %s"),*Report);
    GhostScytheMist::Clear(Blade);World->DestroyWorld(false);return Detected==4?0:4;
}
