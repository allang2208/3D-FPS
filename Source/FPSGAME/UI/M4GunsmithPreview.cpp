#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Framework/Application/SlateApplication.h"

void UM4GunsmithWidget::InitializePreview()
{
    if(Capture||!GetOwningPlayerPawn())return;
    PreviewTarget=NewObject<UTextureRenderTarget2D>(this);
    PreviewTarget->RenderTargetFormat=RTF_RGBA16f;PreviewTarget->ClearColor=FLinearColor(0,0,0,1);
    PreviewTarget->InitAutoFormat(1200,800);PreviewTarget->UpdateResourceImmediate(true);
    PreviewCoverageTarget=NewObject<UTextureRenderTarget2D>(this);
    PreviewCoverageTarget->RenderTargetFormat=RTF_RGBA8;PreviewCoverageTarget->ClearColor=FLinearColor(0,0,0,1);
    PreviewCoverageTarget->InitAutoFormat(1200,800);PreviewCoverageTarget->UpdateResourceImmediate(true);
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved.M_WeaponPreviewResolved"));
    if(!Material)return;
    PreviewMaterial=UMaterialInstanceDynamic::Create(Material,this);PreviewMaterial->SetTextureParameterValue(TEXT("PreviewTexture"),PreviewTarget);
    PreviewMaterial->SetTextureParameterValue(TEXT("PreviewCoverage"),PreviewCoverageTarget);
    PreviewBrush.SetResourceObject(PreviewMaterial);PreviewBrush.ImageSize=FVector2D(1200,800);PreviewBrush.DrawAs=ESlateBrushDrawType::Image;
    Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
    StudioFill=NewObject<UDirectionalLightComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StudioFill->SetIntensity(3.f);StudioFill->SetLightColor(FLinearColor(.82f,.91f,1.f));StudioFill->SetCastShadows(false);
    Studio->AddComponent(StudioFill,FTransform(FRotator(-15,150,0)));
    Studio->UpdateCaptureContents();
    Capture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);
    // Resolve the filmic tone curve before Slate composites the gun over the workbench.
    Capture->TextureTarget=PreviewTarget;Capture->CaptureSource=SCS_FinalToneCurveHDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);
    // Spatial AA remains stable for an intermittently captured, draggable preview.
    Capture->ShowFlags.SetAntiAliasing(true);Capture->ShowFlags.SetTemporalAA(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0.f;
    Studio->AddComponent(Capture,FTransform::Identity);
    // Final-color alpha depends on a project-wide postprocess setting. A separate
    // unlit coverage pass preserves holes and translucent lenses without changing it.
    PreviewCoverageCapture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);
    PreviewCoverageCapture->TextureTarget=PreviewCoverageTarget;PreviewCoverageCapture->CaptureSource=SCS_SceneColorHDR;
    PreviewCoverageCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    PreviewCoverageCapture->bCaptureEveryFrame=false;PreviewCoverageCapture->bCaptureOnMovement=false;
    PreviewCoverageCapture->ShowFlags=Capture->ShowFlags;
    PreviewCoverageCapture->ShowFlags.SetLighting(false);PreviewCoverageCapture->ShowFlags.SetDynamicShadows(false);
    PreviewCoverageCapture->bUseRayTracingIfEnabled=false;
    Studio->AddComponent(PreviewCoverageCapture,FTransform::Identity);
}
void UM4GunsmithWidget::SyncStudioPreview()
{
    // Copy only presentation geometry. Original mesh assets, materials, pose and section visibility remain authoritative.
    const auto Sources=Capture->ShowOnlyComponents;Capture->ShowOnlyComponents.Reset();
    const FTransform ViewTransform=Capture->GetComponentTransform();
    Capture->ProjectionType=bAimPreview?ECameraProjectionMode::Perspective:ECameraProjectionMode::Orthographic;
    Capture->bUseCustomProjectionMatrix=false;
    PreviewFramingBounds=FBox(ForceInit);
    FQuat AssemblyRotation=FQuat::Identity;FVector Pivot=FVector::ZeroVector,Target=FVector::ZeroVector;
    if(!bAimPreview)
        for(const auto& Weak:Sources)
            if(auto* Rifle=Cast<USkeletalMeshComponent>(Weak.Get());Rifle&&Rifle->DoesSocketExist(TEXT("WPN_SOCKET_Muzzle")))
            {
                Pivot=Rifle->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
                const FVector Barrel=(Rifle->GetSocketLocation(TEXT("WPN_FrontSight"))-Rifle->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
                const FVector Up=Rifle->GetSocketLocation(TEXT("WPN_RearSight"))-Pivot;
                // Align both barrel and the rifle's upright axis. A single-vector
                // alignment leaves an arbitrary roll inherited from the held pose.
                const FQuat SourceFrame=FRotationMatrix::MakeFromXZ(Barrel,Up).ToQuat();
                const FQuat FlatFrame=FRotationMatrix::MakeFromXZ(-ViewTransform.GetRotation().GetRightVector(),ViewTransform.GetRotation().GetUpVector()).ToQuat();
                const FQuat Align=FlatFrame*SourceFrame.Inverse();
                const FQuat LayFlat(ViewTransform.GetRotation().GetRightVector(),FMath::DegreesToRadians(PreviewOrbit.Y));
                const FQuat Turn(ViewTransform.GetRotation().GetUpVector(),FMath::DegreesToRadians(PreviewOrbit.X));
                AssemblyRotation=Turn*LayFlat*Align;
                Target=ViewTransform.TransformPosition(FVector(500.f,0.f,0.f));break;
            }
    TSet<UMeshComponent*> VisibleCopies;
    for(const auto& Weak:Sources)
    {
        auto* Source=Cast<UMeshComponent>(Weak.Get());if(!Source||!Source->IsVisible())continue;
        auto*& Copy=StudioCopies.FindOrAdd(Source);
        if(!Copy)
        {
            if(auto* Skinned=Cast<USkeletalMeshComponent>(Source))
            {
                auto* NewMesh=NewObject<USkeletalMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
                NewMesh->SetSkeletalMeshAsset(Skinned->GetSkeletalMeshAsset());NewMesh->SetLeaderPoseComponent(Skinned);NewMesh->SetForcedLOD(1);Copy=NewMesh;
            }
            else if(auto* Static=Cast<UStaticMeshComponent>(Source))
            {
                auto* NewMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
                NewMesh->SetStaticMesh(Static->GetStaticMesh());NewMesh->SetForcedLodModel(1);Copy=NewMesh;
            }
            if(!Copy)continue;
            Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);Copy->SetCastShadow(false);
            Studio->AddComponent(Copy,Source->GetComponentTransform());
            bPreviewStreamingDirty=true;
        }
        if(auto* SourceStatic=Cast<UStaticMeshComponent>(Source))
            if(auto* CopyStatic=Cast<UStaticMeshComponent>(Copy);CopyStatic&&CopyStatic->GetStaticMesh()!=SourceStatic->GetStaticMesh())
            {CopyStatic->EmptyOverrideMaterials();CopyStatic->SetStaticMesh(SourceStatic->GetStaticMesh());bPreviewStreamingDirty=true;}
        if(auto* SourceSkinned=Cast<USkeletalMeshComponent>(Source))
            if(auto* CopySkinned=Cast<USkeletalMeshComponent>(Copy);CopySkinned&&CopySkinned->GetSkeletalMeshAsset()!=SourceSkinned->GetSkeletalMeshAsset())
            {CopySkinned->EmptyOverrideMaterials();CopySkinned->SetSkeletalMeshAsset(SourceSkinned->GetSkeletalMeshAsset());CopySkinned->SetLeaderPoseComponent(SourceSkinned);bPreviewStreamingDirty=true;}
        FTransform Pose=Source->GetComponentTransform();
        if(!bAimPreview){Pose.SetLocation(Target+AssemblyRotation.RotateVector(Pose.GetLocation()-Pivot));Pose.SetRotation(AssemblyRotation*Pose.GetRotation());}
        if(!Copy->IsVisible())bPreviewStreamingDirty=true;
        Copy->SetWorldTransform(Pose);Copy->SetVisibility(true);VisibleCopies.Add(Copy);
        if(!bAimPreview||Cast<USkeletalMeshComponent>(Source))
        {
            FBox LocalBounds(ForceInit);FTransform BoundsFrame=Source->GetComponentTransform();
            if(auto* Static=Cast<UStaticMeshComponent>(Source);Static&&Static->GetStaticMesh())LocalBounds=Static->GetStaticMesh()->GetBoundingBox();
            else if(auto* Skinned=Cast<USkeletalMeshComponent>(Source);Skinned&&Skinned->GetSkeletalMeshAsset())
            {
                auto* Asset=Skinned->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();
                if(Render&&!Render->LODRenderData.IsEmpty())
                {
                    const auto& LOD=Render->LODRenderData[0];uint32 Signature=HashCombine(GetTypeHash(Asset),GetTypeHash(bAimPreview));
                    for(const auto& Section:LOD.RenderSections)Signature=HashCombine(Signature,GetTypeHash(Skinned->IsMaterialSectionShown(Section.MaterialIndex,0)));
                    for(const auto& Part:bStandalone?StandaloneParts:Model()->Draft())Signature=HashCombine(Signature,HashCombine(GetTypeHash(Part.Key),GetTypeHash(Part.Value)));
                    BoundsFrame=Skinned->DoesSocketExist(TEXT("WPN_root"))?Skinned->GetSocketTransform(TEXT("WPN_root")):Skinned->GetComponentTransform();
                    auto& Cached=PreviewBoundsCache.FindOrAdd(Source);
                    if(Cached.Signature!=Signature||!Cached.Box.IsValid)
                    {
                        Cached.Box=FBox(ForceInit);Cached.Signature=Signature;
                        if(auto* Weights=Skinned->GetSkinWeightBuffer(0))
                        {
                            TArray<FMatrix44f> Matrices;Skinned->GetCurrentRefToLocalMatrices(Matrices,0);
                            for(const auto& Section:LOD.RenderSections)if(Skinned->IsMaterialSectionShown(Section.MaterialIndex,0))
                                for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
                                {
                                    const FVector Position(USkinnedMeshComponent::GetSkinnedVertexPosition(Skinned,V,LOD,*Weights,Matrices));
                                    Cached.Box+=BoundsFrame.InverseTransformPosition(Skinned->GetComponentTransform().TransformPosition(Position));
                                }
                        }
                    }
                    LocalBounds=Cached.Box;
                }
            }
            FBox PosedCopyBounds(ForceInit);
            if(LocalBounds.IsValid)for(int32 Corner=0;Corner<8;++Corner)
            {
                const FVector P((Corner&1)?LocalBounds.Max.X:LocalBounds.Min.X,(Corner&2)?LocalBounds.Max.Y:LocalBounds.Min.Y,(Corner&4)?LocalBounds.Max.Z:LocalBounds.Min.Z);
                const FVector SourceWorld=BoundsFrame.TransformPosition(P);
                PosedCopyBounds+=Copy->GetComponentTransform().TransformPosition(Source->GetComponentTransform().InverseTransformPosition(SourceWorld));
                if(!bAimPreview)
                {
                    const FVector World=Target+AssemblyRotation.RotateVector(SourceWorld-Pivot);
                    PreviewFramingBounds+=ViewTransform.InverseTransformPosition(World);
                }
            }
            if(auto* SkinnedCopy=Cast<USkeletalMeshComponent>(Copy);SkinnedCopy&&PosedCopyBounds.IsValid)
            {
                // Leader-pose copies can fall back to imported arms/rest bounds.
                // A long muzzle recenters the preview, exposing that mismatch:
                // attachments stay visible while the posed gun is culled. Enclose
                // the measured visible pose, as the inventory capture already does.
                SkinnedCopy->SetBoundsScale(1.f);SkinnedCopy->InvalidateCachedBounds();SkinnedCopy->UpdateBounds();
                const FVector Required=(PosedCopyBounds.GetCenter()-SkinnedCopy->Bounds.Origin).GetAbs()+PosedCopyBounds.GetExtent();
                const FVector Extent=SkinnedCopy->Bounds.BoxExtent;
                const float CullingScale=FMath::Max3(float(Required.X/FMath::Max(Extent.X,.01)),float(Required.Y/FMath::Max(Extent.Y,.01)),float(Required.Z/FMath::Max(Extent.Z,.01)));
                const float SphereScale=float(((PosedCopyBounds.GetCenter()-SkinnedCopy->Bounds.Origin).Size()+PosedCopyBounds.GetExtent().Size())/FMath::Max(SkinnedCopy->Bounds.SphereRadius,.01));
                SkinnedCopy->SetBoundsScale(FMath::Max(1.f,FMath::Max(CullingScale,SphereScale)*1.02f));
                SkinnedCopy->InvalidateCachedBounds();SkinnedCopy->UpdateBounds();
                SkinnedCopy->MarkRenderTransformDirty();
            }
        }
        for(int32 M=0;M<Source->GetNumMaterials();++M)if(Copy->GetMaterial(M)!=Source->GetMaterial(M))
        {Copy->SetMaterial(M,Source->GetMaterial(M));bPreviewStreamingDirty=true;}
        if(auto* Skinned=Cast<USkeletalMeshComponent>(Source))
            if(const auto* Asset=Skinned->GetSkeletalMeshAsset())if(const auto* Render=Asset->GetResourceForRendering())
                for(int32 L=0;L<Render->LODRenderData.Num();++L)
                    for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
                    {
                        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                        Cast<USkeletalMeshComponent>(Copy)->ShowMaterialSection(M,S,Skinned->IsMaterialSectionShown(M,L),L);
                    }
        Capture->ShowOnlyComponent(Copy);
    }
    for(auto It=StudioCopies.CreateIterator();It;++It)
    {
        if(!It.Key().IsValid())
        {Studio->RemoveComponent(It.Value());It.Value()->DestroyComponent();PreviewBoundsCache.Remove(It.Key());It.RemoveCurrent();bPreviewStreamingDirty=true;}
        else if(!VisibleCopies.Contains(It.Value())&&It.Value()->IsVisible())
        {It.Value()->SetVisibility(false);bPreviewStreamingDirty=true;}
    }
    if(bPreviewStreamingDirty)PreviewMotion=FMath::Max(PreviewMotion,2.f);
    if(!bAimPreview&&PreviewFramingBounds.IsValid)
    {
        const float Aspect=float(PreviewTarget->SizeX)/FMath::Max(1,PreviewTarget->SizeY);
        const FVector Size=PreviewFramingBounds.GetSize(),Center=PreviewFramingBounds.GetCenter();
        // Reserve space around all visible parts, including future nested attachments.
        Capture->OrthoWidth=FMath::Max(30.f,FMath::Max(float(Size.Y)/.84f,float(Size.Z)*Aspect/.60f))/PreviewZoom;
        const FVector LocalShift(FMath::Max(500.,Size.X*.5+100.)-Center.X,-Center.Y,-Center.Z);
        const FVector Shift=ViewTransform.TransformVector(LocalShift);
        for(const auto& Weak:Capture->ShowOnlyComponents)if(auto* Copy=Weak.Get())Copy->AddWorldOffset(Shift);
        PreviewFramingBounds=PreviewFramingBounds.ShiftBy(LocalShift);
        Capture->bAutoCalculateOrthoPlanes=false;
        const float PreviewNear=.1f;
        const float PreviewFar=FMath::Max(2000.f,float(PreviewFramingBounds.Max.X)+100.f);
        Capture->bUseCustomProjectionMatrix=true;
        Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,
            Capture->OrthoWidth*.5f/Aspect,1.f/(PreviewFar-PreviewNear),-PreviewNear);
    }
    const FQuat View=Capture->GetComponentQuat();
    Studio->DirectionalLight->SetWorldRotation(View*FRotator(-40,-55,0).Quaternion());
    StudioFill->SetWorldRotation(View*FRotator(-15,150,0).Quaternion());
}
void UM4GunsmithWidget::RotatePreview(FVector2D Delta)
{
    if(bAimPreview||!bSidePreview)SetSidePreview(true);
    PreviewOrbit.X=FMath::UnwindDegrees(PreviewOrbit.X+float(Delta.X)*.35f);
    PreviewOrbit.Y=FMath::Clamp(PreviewOrbit.Y-float(Delta.Y)*.35f,-85.f,85.f);
    PreviewMotion=1.f;CaptureAccumulator=1.f;
}
void UM4GunsmithWidget::ZoomPreview(float WheelDelta)
{
    if(bAimPreview||!bSidePreview)SetSidePreview(true);
    PreviewZoom=FMath::Clamp(PreviewZoom*FMath::Pow(1.12f,WheelDelta),.65f,2.25f);
    PreviewMotion=1.f;CaptureAccumulator=1.f;
}
void UM4GunsmithWidget::ReleasePreview()
{
    if(PreviewSurface&&PreviewSurface->HasMouseCapture()&&FSlateApplication::IsInitialized())FSlateApplication::Get().ReleaseMouseCapture();
    PreviewSurface.Reset();
    if(StandaloneMelee){Studio->RemoveComponent(StandaloneMelee);StandaloneMelee->DestroyComponent();StandaloneMelee=nullptr;}
    if(Capture){Capture->TextureTarget=nullptr;Studio->RemoveComponent(Capture);Capture->DestroyComponent();Capture=nullptr;}
    if(PreviewCoverageCapture){PreviewCoverageCapture->TextureTarget=nullptr;Studio->RemoveComponent(PreviewCoverageCapture);PreviewCoverageCapture->DestroyComponent();PreviewCoverageCapture=nullptr;}
    StudioCopies.Reset();PreviewBoundsCache.Reset();StudioFill=nullptr;Studio.Reset();
    PreviewStreamedTextures.Reset();PreviewStreamingAccumulator=1.f;bPreviewStreamingDirty=true;bPreviewStreamingPending=false;
    PreviewBrush.SetResourceObject(nullptr);
    if(PreviewTarget)PreviewTarget->ReleaseResource();
    if(PreviewCoverageTarget)PreviewCoverageTarget->ReleaseResource();
    PreviewMaterial=nullptr;PreviewTarget=nullptr;PreviewCoverageTarget=nullptr;
}
void UM4GunsmithWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);UpdateResponsiveLayout();TickCapture(Delta);
}
void UM4GunsmithWidget::TickCapture(float Delta)
{
    CaptureAccumulator+=Delta;PreviewMotion=FMath::Max(0.f,PreviewMotion-Delta);
    UpdatePreviewStreaming(Delta);
    if(PreviewTarget&&PreviewSurface)
    {
        const auto& Geometry=PreviewSurface->GetCachedGeometry();
        const FVector2D Size=(Geometry.GetLocalSize()-FVector2D(16,28))*Geometry.GetAccumulatedLayoutTransform().GetScale();
        if(Size.X>32&&Size.Y>32)
        {
            const float Scale=FMath::Min(2.f,2048.f/float(FMath::Max(Size.X,Size.Y)));
            const int32 Width=FMath::Max(32,FMath::RoundToInt(Size.X*Scale)),Height=FMath::Max(32,FMath::RoundToInt(Size.Y*Scale));
            if(FMath::Abs(PreviewTarget->SizeX-Width)>2||FMath::Abs(PreviewTarget->SizeY-Height)>2)
            {PreviewTarget->ResizeTarget(Width,Height);PreviewCoverageTarget->ResizeTarget(Width,Height);PreviewBrush.ImageSize=FVector2D(Width,Height);CaptureAccumulator=1.f;PreviewMotion=FMath::Max(PreviewMotion,1.f);}
        }
    }
    if(!Capture||CaptureAccumulator<((PreviewMotion>0||bPreviewStreamingPending)?1.f/30.f:.2f))return;
    CaptureAccumulator=0;
    if(bStandalone){if(StandaloneMelee){SyncStandaloneMeleePreview();CapturePreview();}else if(StandaloneRig){StandaloneRig->UpdateGunsmithCapture(Capture,bAimPreview);SyncStudioPreview();CapturePreview();}return;}
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P->Equipped()||P->Equipped()->InstanceId!=Model()->Instance())return;
    if(auto* C=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn()))
    {C->UpdateGunsmithCapture(Capture,bAimPreview);SyncStudioPreview();CapturePreview();}
}
