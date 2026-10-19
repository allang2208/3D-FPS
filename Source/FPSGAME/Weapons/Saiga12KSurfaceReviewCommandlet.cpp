#include "Saiga12KSurfaceReviewCommandlet.h"

#if WITH_EDITOR
#include "Saiga12KAttachments.h"
#include "WeaponPresentationMaterials.h"
#include "../UI/ColdSteelPreviewScene.h"
#include "../UI/GunsmithPreviewLighting.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "UObject/StrongObjectPtr.h"
#endif

int32 USaiga12KSurfaceReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString MeshPath, AttachmentRoot, Output;
    if (!FParse::Value(*Params,TEXT("Mesh="),MeshPath) || !FParse::Value(*Params,TEXT("Output="),Output)) return 1;
    FParse::Value(*Params,TEXT("AttachmentRoot="),AttachmentRoot);
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*MeshPath);
    auto* Idle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle"));
    if (!Asset || !Idle) return 2;
    FString Failure;
    auto Studio=FColdSteelPreviewScene::TryCreate(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(2.5f).SetSkyBrightness(.28f),Failure);
    if (!Studio) { UE_LOG(LogTemp,Error,TEXT("SaigaSurfaceReview: %s"),*Failure); return 3; }
    Studio->GetWorld()->SetShouldTick(false);
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    TStrongObjectPtr<USkeletalMeshComponent> Rig(NewObject<USkeletalMeshComponent>(GetTransientPackage()));
    Rig->SetSkeletalMeshAsset(Asset); Rig->SetForcedLOD(1); Rig->SetCastShadow(false);
    Studio->AddComponent(Rig.Get(),FTransform::Identity);
    Rig->SetAnimationMode(EAnimationMode::AnimationSingleNode); Rig->PlayAnimation(Idle,true); Rig->SetPlayRate(0.f);
    Rig->SetPosition(0.f,false); Rig->TickAnimation(0.f,false); Rig->RefreshBoneTransforms(); Rig->UpdateComponentToWorld();
    const auto* Render=Asset->GetResourceForRendering();
    if (!Render || Render->LODRenderData.IsEmpty()) return 4;
    int32 GunTriangles=0;
    for (int32 S=0;S<Render->LODRenderData[0].RenderSections.Num();++S)
    {
        const auto& Section=Render->LODRenderData[0].RenderSections[S];
        const bool Arm=WeaponPresentationMaterials::IsArmSection(Asset->GetMaterials()[Section.MaterialIndex]);
        Rig->ShowMaterialSection(Section.MaterialIndex,S,!Arm,0);
        if (!Arm) GunTriangles+=Section.NumTriangles;
    }
    const FTransform Root=Rig->GetSocketTransform(TEXT("WPN_root"));
    TStrongObjectPtr<USceneCaptureComponent2D> Capture(NewObject<USceneCaptureComponent2D>(GetTransientPackage()));
    TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>(GetTransientPackage()));
    Target->RenderTargetFormat=RTF_RGBA8_SRGB; Target->ClearColor=FLinearColor(.025f,.028f,.032f,1.f);
    Target->InitAutoFormat(1600,1000); Target->UpdateResourceImmediate(true);
    Capture->TextureTarget=Target.Get(); Capture->CaptureSource=SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false; Capture->bCaptureOnMovement=false;
    Capture->bAlwaysPersistRenderingState=true;
    Capture->ShowFlags.SetAtmosphere(false); Capture->ShowFlags.SetFog(false); Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false); Capture->ShowFlags.SetBloom(false); Capture->ShowFlags.SetTemporalAA(true);
    Capture->ShowFlags.SetAntiAliasing(true); Capture->ShowFlags.SetLighting(true); Capture->ShowFlags.SetMaterials(true);
    auto& PP=Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true; PP.AutoExposureMethod=AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true; PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true; PP.AutoExposureBias=0;
    PP.bOverride_FilmGrainIntensity=true; PP.FilmGrainIntensity=0;
    Studio->AddComponent(Capture.Get(),FTransform::Identity); Capture->ShowOnlyComponent(Rig.Get());
    TArray<TStrongObjectPtr<UStaticMeshComponent>> Parts;
    if (!AttachmentRoot.IsEmpty())
    {
        for (const auto& Key:{FString(TEXT("OpticSeat_eoth_holographic")),FString(TEXT("eoth_holographic"))})
        {
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*(AttachmentRoot/TEXT("SM_Saiga12K_")+Key));
            if (!Mesh) return 5;
            TStrongObjectPtr<UStaticMeshComponent> Part(NewObject<UStaticMeshComponent>(GetTransientPackage()));
            Part->SetStaticMesh(Mesh); Part->SetForcedLodModel(1); Part->SetCastShadow(false);
            const FTransform Local=Key.StartsWith(TEXT("OpticSeat"))?Saiga12KAttachments::RailMount():Saiga12KAttachments::OpticMount(TEXT("eoth_holographic"));
            Studio->AddComponent(Part.Get(),Local*Root); Capture->ShowOnlyComponent(Part.Get()); Parts.Add(MoveTemp(Part));
        }
    }
    auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage()); Fill->SetIntensity(.65f);
    Fill->SetLightColor(FLinearColor(.82f,.91f,1.f)); Fill->SetCastShadows(false);
    Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    GunsmithPreviewLighting::Create(*Studio,*Capture);
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    Studio->UpdateCaptureContents();
    struct FView {const TCHAR* Name; FVector Center; FVector Offset; float Width;};
    const FView Views[]={
        {TEXT("Hero"),FVector(0,14,0),FVector(125,20,26),104.f},
        {TEXT("Receiver"),FVector(0,4,3),FVector(-100,-24,25),38.f},
        {TEXT("Foreend"),FVector(0,30,4),FVector(100,18,25),33.f},
        {TEXT("Opposite"),FVector(0,14,0),FVector(-125,-20,25),104.f}};
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);
    for (const auto& View:Views)
    {
        const FVector Center=Root.TransformPosition(View.Center*.01);
        const FVector Position=Root.TransformPosition((View.Center+View.Offset)*.01);
        const FQuat Rotation=FRotationMatrix::MakeFromXZ(Center-Position,Root.GetRotation().GetUpVector()).ToQuat();
        Capture->SetWorldTransform(FTransform(Rotation,Position)); Capture->ProjectionType=ECameraProjectionMode::Orthographic;
        Capture->OrthoWidth=View.Width;
        const FVector ViewCenter=Capture->GetComponentTransform().InverseTransformPosition(Center);
        GunsmithPreviewLighting::Update(*Capture,FBox(ViewCenter-FVector(45,45,20),ViewCenter+FVector(45,45,20)),true,.55f);
        for (int32 Frame=0;Frame<16;++Frame)
        {
            ++GFrameCounter;
            Studio->GetWorld()->Tick(LEVELTICK_All,1.f/60.f); Rig->SetPosition(0.f,false);
            Rig->TickAnimation(0.f,false); Rig->RefreshBoneTransforms();
            Studio->GetWorld()->SendAllEndOfFrameUpdates(); Capture->CaptureScene(); FlushRenderingCommands();
        }
        TArray<FColor> Pixels;
        if (!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)) return 6;
        for (auto& Pixel:Pixels) Pixel.A=255;
        TArray64<uint8> PNG; FImageUtils::PNGCompressImageArray(1600,1000,Pixels,PNG);
        if (!FFileHelper::SaveArrayToFile(PNG,*(Output+TEXT("_")+View.Name+TEXT(".png")))) return 7;
        if (FString(View.Name)==TEXT("Hero"))
        {
            Capture->CaptureSource=SCS_BaseColor;
            Capture->CaptureScene(); FlushRenderingCommands();
            if (!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)) return 8;
            for (auto& Pixel:Pixels) Pixel.A=255;
            PNG.Reset(); FImageUtils::PNGCompressImageArray(1600,1000,Pixels,PNG);
            if (!FFileHelper::SaveArrayToFile(PNG,*(Output+TEXT("_BaseColor.png")))) return 9;
            Capture->CaptureSource=SCS_FinalColorLDR;
        }
    }
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"mesh\":\"%s\",\"render_gun_triangles\":%d,\"actual_skeletal_renderer\":true,\"idle_frame\":0,\"player_profile_created\":false,\"complete\":true}"),*MeshPath,GunTriangles),*(Output+TEXT(".json")));
    UE_LOG(LogTemp,Display,TEXT("SaigaSurfaceReview: COMPLETE mesh=%s rendered_triangles=%d"),*MeshPath,GunTriangles);
    return 0;
#else
    return 1;
#endif
}
