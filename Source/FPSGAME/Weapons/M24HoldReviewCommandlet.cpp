#include "M24HoldReviewCommandlet.h"
#include "M24SurfaceReview.h"
#if WITH_EDITOR
#include "M24WeaponAssets.h"
#include "M24Attachments.h"
#include "SVDWeaponAssets.h"
#include "RifleHipFraming.h"
#include "../UI/ColdSteelPreviewScene.h"
#include "../UI/GunsmithPreviewLighting.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "AssetCompilingManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"
#endif

int32 UM24HoldReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Output;
    if (!FParse::Value(*Params,TEXT("Output="),Output)) return 1;
    FString SurfaceManifest;
    if (FParse::Value(*Params,TEXT("SurfaceManifest="),SurfaceManifest))
        return RunM24SurfaceReview(SurfaceManifest,Output);
    float SoftboxScale=.15f,Exposure=-.25f;
    FParse::Value(*Params,TEXT("SoftboxScale="),SoftboxScale);
    FParse::Value(*Params,TEXT("Exposure="),Exposure);
    IFileManager::Get().MakeDirectory(*Output,true);
    FString Failure;
    auto Studio=FColdSteelPreviewScene::TryCreate(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(2.5f).SetSkyBrightness(.8f),Failure);
    if (!Studio) return 2;
    UWorld* World=Studio->GetWorld(); World->SetShouldTick(false);
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    // A local transient pawn permits the existing corrective driver to run exactly as in-game.
    APawn* Owner=World->SpawnActor<APawn>();
    APlayerController* Controller=World->SpawnActor<APlayerController>();
    Controller->SetAsLocalPlayerController();
    Controller->Possess(Owner);
    auto* Rig=NewObject<USkeletalMeshComponent>(Owner); Owner->AddInstanceComponent(Rig); Owner->SetRootComponent(Rig);
    Rig->SetForcedLOD(1); Rig->SetCastShadow(false); Studio->AddComponent(Rig,FTransform::Identity);
    auto* Correctives=NewObject<UFPSArmJointCorrectiveComponent>(Owner);
    Owner->AddInstanceComponent(Correctives); Correctives->RegisterComponent();
    TStrongObjectPtr<USceneCaptureComponent2D> Capture(NewObject<USceneCaptureComponent2D>(GetTransientPackage()));
    TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>(GetTransientPackage()));
    Target->RenderTargetFormat=RTF_RGBA8_SRGB;Target->ClearColor=FLinearColor(.045f,.055f,.07f,1);
    Target->InitAutoFormat(1280,720);Target->UpdateResourceImmediate(true);
    Capture->TextureTarget=Target.Get();Capture->CaptureSource=SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->bAlwaysPersistRenderingState=true;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);Capture->ShowFlags.SetTemporalAA(true);
    Capture->ShowFlags.SetAntiAliasing(true);Capture->ShowFlags.SetLighting(true);Capture->ShowFlags.SetMaterials(true);
    Capture->FOVAngle=FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(37.5f))*16.f/9.f));
    Capture->bOverride_CustomNearClippingPlane=true;Capture->CustomNearClippingPlane=1.f;
    auto& PP=Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=Exposure;PP.bOverride_FilmGrainIntensity=true;PP.FilmGrainIntensity=0;
    Studio->AddComponent(Capture.Get(),FTransform::Identity);
    auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage());Fill->SetIntensity(.25f);
    Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Fill->SetCastShadows(false);
    Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    GunsmithPreviewLighting::Create(*Studio,*Capture);
    TArray<TSharedPtr<FJsonValue>> Results;
    for (bool bM24:{false,true})
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,bM24?M24WeaponAssets::MeshPath:SVDWeaponAssets::MeshPath);
        auto* Idle=LoadObject<UAnimSequence>(nullptr,*(bM24?M24WeaponAssets::AnimationPath(TEXT("idle")):SVDWeaponAssets::AnimationPath(TEXT("idle"))));
        if (!Mesh||!Idle) return 3;
        FRifleHipFraming Framing;Framing.Initialize(bM24?M24WeaponAssets::Definition:SVDWeaponAssets::Definition,Idle,FVector(0,7,-7),FRotator(0,90,0),FVector::OneVector,false);
        if (!Framing.IsReady()) return 4;
        Rig->SetSkeletalMeshAsset(Mesh);Rig->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        Rig->SetWorldTransform(FTransform(Framing.Rotation(FQuat::Identity),Framing.Location(FVector::ZeroVector)));
        Rig->PlayAnimation(Idle,true);Rig->SetPlayRate(0);Rig->SetPosition(0,false);Rig->TickAnimation(0,false);Rig->RefreshBoneTransforms();
        Capture->ClearShowOnlyComponents();Capture->ShowOnlyComponent(Rig);
        TArray<UStaticMeshComponent*> Parts;
        if (bM24) for (const auto* Key:{M24Attachments::Scope,M24Attachments::Suppressor,M24Attachments::CheekRest})
        {
            auto* Part=M24Attachments::Configure(Owner,Rig,nullptr,Key,true);
            if (!Part) return 5;
            Parts.Add(Part);Capture->ShowOnlyComponent(Part);
        }
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
        Studio->UpdateCaptureContents();
        FBox Assembly=Rig->Bounds.GetBox();
        for(const auto* Part:Parts)Assembly+=Part->Bounds.GetBox();
        GunsmithPreviewLighting::Update(*Capture,Assembly,false,SoftboxScale);
        struct FSample {const TCHAR* Role;float Time;};
        TArray<FSample> Samples={{TEXT("idle"),0.f}};
        if(bM24)Samples.Append({{TEXT("idle"),1.f},{TEXT("aim"),0.f},{TEXT("fire"),1.f},{TEXT("cycle"),1.f},{TEXT("reload"),1.f},{TEXT("reload_empty"),65.f/30.f},{TEXT("equip"),.8f},{TEXT("inspect"),1.5f},{TEXT("quick_melee"),.9f}});
        for(const auto& Sample:Samples)
        {
            auto* Clip=LoadObject<UAnimSequence>(nullptr,*(bM24?M24WeaponAssets::AnimationPath(Sample.Role):SVDWeaponAssets::AnimationPath(Sample.Role)));
            if (!Clip) return 6;
            Rig->PlayAnimation(Clip,true);Rig->SetPlayRate(0);
            for(int32 Frame=0;Frame<12;++Frame)
            {
                ++GFrameCounter;
                World->Tick(LEVELTICK_All,1.f/60.f);
                Rig->SetPosition(Sample.Time,false);Rig->TickAnimation(0,false);Rig->RefreshBoneTransforms();Rig->UpdateComponentToWorld();
                Correctives->TickComponent(.3f,LEVELTICK_All,nullptr);
                World->SendAllEndOfFrameUpdates();Capture->CaptureScene();FlushRenderingCommands();
            }
            TArray<FColor> Pixels;
            if (!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)) return 7;
            for(auto& Pixel:Pixels)Pixel.A=255;
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(1280,720,Pixels,PNG);
            const FString Name=FString::Printf(TEXT("%s_%s_%03d"),bM24?TEXT("M24"):TEXT("SVD"),Sample.Role,FMath::RoundToInt(Sample.Time*30));
            if (!FFileHelper::SaveArrayToFile(PNG,*(Output/(Name+TEXT(".png")))))return 8;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("view"),Name);Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());
            Row->SetStringField(TEXT("clip"),Clip->GetPathName());Row->SetBoolField(TEXT("framing_ready"),Framing.IsReady());
            Row->SetStringField(TEXT("hip_cm"),Framing.Location(FVector::ZeroVector).ToString());
            Row->SetNumberField(TEXT("corrective_count"),Mesh->GetMorphTargets().Num());
            Row->SetBoolField(TEXT("local_corrective_driver"),Owner->IsLocallyControlled());
            Row->SetStringField(TEXT("camera"),TEXT("calibrated hip; aim entry reviews the aim clip in this same camera"));
            Row->SetNumberField(TEXT("elbow_left_weight"),Rig->GetMorphTarget(TEXT("JC_ElbowFlex75_L")));
            float MaxDelta=0;
            for(const UMorphTarget* Morph:Mesh->GetMorphTargets())for(const auto& LOD:Morph->GetMorphLODModels())for(const auto& Vertex:LOD.Vertices)MaxDelta=FMath::Max(MaxDelta,Vertex.PositionDelta.Size());
            Row->SetNumberField(TEXT("max_morph_delta_cm"),MaxDelta);
            Results.Add(MakeShared<FJsonValueObject>(Row));
        }
        for(auto* Part:Parts)Part->DestroyComponent();
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("views"),Results);Report->SetBoolField(TEXT("complete"),true);
    Report->SetNumberField(TEXT("softbox_scale"),SoftboxScale);Report->SetNumberField(TEXT("exposure"),Exposure);
    Report->SetBoolField(TEXT("gameplay_test"),false);FString JSON;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&JSON));
    FFileHelper::SaveStringToFile(JSON,*(Output/TEXT("review.json")));
    UE_LOG(LogTemp,Display,TEXT("M24_HOLD_REVIEW_COMPLETE views=%d"),Results.Num());
    return 0;
#else
    return 1;
#endif
}
