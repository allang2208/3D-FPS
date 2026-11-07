#include "M24SurfaceReview.h"
#if WITH_EDITOR
#include "../UI/ColdSteelPreviewScene.h"
#include "../UI/GunsmithPreviewLighting.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "ContentStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "RenderingThread.h"
#include "Serialization/JsonSerializer.h"
#include "ShaderCompiler.h"
#include "UObject/StrongObjectPtr.h"
#endif

int32 RunM24SurfaceReview(const FString& ManifestPath, const FString& Output)
{
#if WITH_EDITOR
    FString Text, Failure;
    TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text,*ManifestPath) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Manifest)) return 10;
    const TArray<TSharedPtr<FJsonValue>>* Groups=nullptr;
    if (!Manifest->TryGetArrayField(TEXT("groups"),Groups)) return 11;
    bool bFlatNormalProbe=false;
    Manifest->TryGetBoolField(TEXT("flat_normal_probe"),bFlatNormalProbe);
    bool bAfterOnly=false;
    Manifest->TryGetBoolField(TEXT("after_only"),bAfterOnly);
    IFileManager::Get().MakeDirectory(*Output,true);
    auto Studio=FColdSteelPreviewScene::TryCreate(FPreviewScene::ConstructionValues().SetEditor(false)
        .SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true)
        .SetLightBrightness(6.f).SetSkyBrightness(1.5f),Failure);
    if (!Studio) return 12;
    UWorld* World=Studio->GetWorld(); World->SetShouldTick(false);
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    Studio->DirectionalLight->SetWorldRotation(FRotator(-40,-55,0));
    auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage());
    Fill->SetIntensity(3.f);Fill->SetCastShadows(false);Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));
    Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>(GetTransientPackage()));
    Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor::Black;
    Target->InitAutoFormat(1600,800);Target->UpdateResourceImmediate(true);
    TStrongObjectPtr<USceneCaptureComponent2D> Capture(NewObject<USceneCaptureComponent2D>(GetTransientPackage()));
    Capture->TextureTarget=Target.Get();Capture->CaptureSource=SCS_FinalToneCurveHDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->bAlwaysPersistRenderingState=true;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetBloom(false);Capture->ShowFlags.SetMotionBlur(false);
    Capture->ShowFlags.SetTemporalAA(true);Capture->ShowFlags.SetAntiAliasing(true);
    Capture->FOVAngle=40.f;Capture->bOverride_CustomNearClippingPlane=true;Capture->CustomNearClippingPlane=.1f;
    auto& PP=Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=.35f;
    PP.bOverride_FilmGrainIntensity=true;PP.FilmGrainIntensity=0;
    Studio->AddComponent(Capture.Get(),FTransform::Identity);
    GunsmithPreviewLighting::Create(*Studio,*Capture);
    TArray<TSharedPtr<FJsonValue>> Results;
    for (const auto& GroupValue:*Groups)
    {
        const auto Group=GroupValue->AsObject();
        const FString Name=Group->GetStringField(TEXT("name"));
        const auto& Entries=Group->GetArrayField(TEXT("parts"));
        TArray<UStaticMeshComponent*> Parts;
        FBox Bounds(ForceInit);
        for (const auto& EntryValue:Entries)
        {
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*EntryValue->AsObject()->GetStringField(TEXT("mesh")));
            if (!Mesh) return 13;
            auto* Part=NewObject<UStaticMeshComponent>(GetTransientPackage());
            Part->SetMobility(EComponentMobility::Movable);Part->SetStaticMesh(Mesh);
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Studio->AddComponent(Part,FTransform::Identity);
            Part->SetTextureForceResidentFlag(true);
            Capture->ShowOnlyComponent(Part);Parts.Add(Part);Bounds+=Part->Bounds.GetBox();
        }
        FVector Center=Bounds.GetCenter();
        const double Span=FMath::Max(Bounds.GetSize().Y,Bounds.GetSize().Z*2.);
        FVector Camera=Center+FVector(Span*1.65,Span*.08,Span*.35);
        const TArray<TSharedPtr<FJsonValue>>* Position=nullptr;
        if (Group->TryGetArrayField(TEXT("camera_cm"),Position) && Position->Num()==3)
            Camera=FVector((*Position)[0]->AsNumber(),(*Position)[1]->AsNumber(),(*Position)[2]->AsNumber());
        if (Group->TryGetArrayField(TEXT("target_cm"),Position) && Position->Num()==3)
            Center=FVector((*Position)[0]->AsNumber(),(*Position)[1]->AsNumber(),(*Position)[2]->AsNumber());
        Capture->SetWorldLocationAndRotation(Camera,(Center-Camera).Rotation());
        const FBox LocalBounds=Bounds.TransformBy(Capture->GetComponentTransform().ToInverseMatrixWithScale());
        GunsmithPreviewLighting::Update(*Capture,LocalBounds,false,.25f);
        const TArray<FString> Modes=bFlatNormalProbe ? TArray<FString>{TEXT("after"),TEXT("flat_normal")} :
            bAfterOnly ? TArray<FString>{TEXT("after")} : TArray<FString>{TEXT("before"),TEXT("after")};
        for (const FString& Mode:Modes)
        {
            TArray<TSharedPtr<FJsonValue>> Bindings;
            for (int32 Index=0;Index<Parts.Num();++Index)
            {
                const auto& Materials=Entries[Index]->AsObject()->GetArrayField(Mode==TEXT("flat_normal")?TEXT("after"):Mode);
                if (Materials.Num()!=Parts[Index]->GetNumMaterials()) return 14;
                for (int32 Slot=0;Slot<Materials.Num();++Slot)
                {
                    auto* Material=LoadObject<UMaterialInterface>(nullptr,*Materials[Slot]->AsString());
                    if (!Material) return 15;
                    if (Mode==TEXT("flat_normal"))
                    {
                        auto* Flat=LoadObject<UTexture>(nullptr,TEXT("/Engine/EngineMaterials/FlatNormal"));
                        if (!Flat) return 19;
                        auto* MID=UMaterialInstanceDynamic::Create(Material,Parts[Index]);
                        MID->SetTextureParameterValue(TEXT("SurfaceNormal"),Flat);Material=MID;
                    }
                    Parts[Index]->SetMaterial(Slot,Material);
                    Bindings.Add(MakeShared<FJsonValueString>(Material->GetPathName()));
                }
                Parts[Index]->MarkRenderStateDirty();
            }
            FAssetCompilingManager::Get().FinishAllCompilation();
            if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
            World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
            UTexture::ForceUpdateTextureStreaming();IStreamingManager::Get().StreamAllResources(0.f);
            Studio->UpdateCaptureContents();
            Capture->bCameraCutThisFrame=true;
            for (int32 Frame=0;Frame<16;++Frame)
            {
                ++GFrameCounter;World->SendAllEndOfFrameUpdates();
                Capture->CaptureScene();FlushRenderingCommands();
            }
            TArray<FLinearColor> Linear;
            if (!Target->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(Linear,FReadSurfaceDataFlags(RCM_MinMax))) return 16;
            TArray<FColor> Pixels;Pixels.Reserve(Linear.Num());
            for (const auto& Color:Linear) { FColor Pixel=Color.ToFColorSRGB();Pixel.A=255;Pixels.Add(Pixel); }
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(1600,800,Pixels,PNG);
            const FString Filename=Name+TEXT("_")+Mode+TEXT(".png");
            if (!FFileHelper::SaveArrayToFile(PNG,*(Output/Filename))) return 17;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("file"),Filename);
            Row->SetArrayField(TEXT("materials"),Bindings);Row->SetStringField(TEXT("camera"),Camera.ToString());
            Results.Add(MakeShared<FJsonValueObject>(Row));
            UE_LOG(LogTemp,Display,TEXT("M24_SURFACE_CAPTURE %s"),*Filename);
        }
        Capture->ClearShowOnlyComponents();
        for (auto* Part:Parts) Studio->RemoveComponent(Part);
        World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("captures"),Results);
    Report->SetBoolField(TEXT("complete"),true);Report->SetBoolField(TEXT("asset_writes"),false);
    Report->SetBoolField(TEXT("gameplay_test"),false);Report->SetNumberField(TEXT("exposure"),.35);
    Report->SetBoolField(TEXT("flat_normal_probe"),bFlatNormalProbe);
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    return FFileHelper::SaveStringToFile(Text,*(Output/TEXT("capture_receipt.json")))?0:18;
#else
    return 1;
#endif
}
