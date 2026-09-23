#include "ColdSteelWeaponIcons.h"
#include "FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/ModularSwordVisual.h"
#include "ColdSteelPickupStudio.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "TextureResource.h"
#include "RenderingThread.h"
#include "Materials/Material.h"
#include "MaterialShared.h"
#include "Misc/DateTime.h"
#include "Materials/MaterialRenderProxy.h"
#include "SceneInterface.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#endif

bool UColdSteelWeaponIcons::Supports(const FColdSteelItem& I) const {return ColdSteelMeleePreview::Supports(I)||I.Definition==TEXT("ue_m4a1")||I.Definition==TEXT("ue_akm")||I.Definition==TEXT("ue_a762")||I.Definition==TEXT("ue_svd")||I.Definition==TEXT("ue_pkm_lowpoly")||I.Definition==TEXT("ue_qbz191")||I.Definition==TEXT("ue_ash12")||I.Definition==TEXT("ue_m16a2")||(I.Definition==TEXT("ue_m1911")||I.Definition==TEXT("ue_dan_wesson715"));}
FString UColdSteelWeaponIcons::Key(const FColdSteelItem& I) const
{
    if(ColdSteelModularSword::Supports(I))return I.Definition+TEXT("|")+ColdSteelModularSword::Key(I,nullptr,!bCatalogExport);
    if(ColdSteelMeleePreview::Supports(I))return I.Definition+TEXT("|")+ColdSteelMeleePreview::MeshPath(I)+TEXT("|")+(bCatalogExport?FString():ColdSteelMeleeRune::Selected(I));
    const auto Parts=bCatalogExport?FGunsmithParts():GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(I);TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();
    FString Result=I.Definition;for(const auto& N:Names)Result+=TEXT("|")+N+TEXT("=")+Parts[N];return Result;
}
void UColdSteelWeaponIcons::Request(const FColdSteelItem& I)
{
    if(!Supports(I))return;
    UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::Request);
    const FString K=Key(I);
    if(auto* E=Cache.Find(K)){E->Use=++Serial;UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::CacheHit);return;}
    if(Pending.Contains(K)){UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::PendingHit);return;}
    if(Failed.Contains(K)){UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::FailedHit);return;}
    Pending.Add(K);Queue.Add({I,K,FPlatformTime::Seconds()});
    UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::Queued);
}
FFPSIconTaskState UColdSteelWeaponIcons::GetPerformanceState() const
{
    FFPSIconTaskState State;
    State.bAvailable=true;State.ObservedSeconds=FPlatformTime::Seconds();
    State.Queued=Queue.Num();State.Cached=Cache.Num();State.FailedRecipes=Failed.Num();State.Stage=Stage;
    State.RecentFailures=RecentFailures;State.FailureCapacity=MaxFailureDetails;
    State.WaitReason=WaitReason;State.WaitResource=WaitResource;
    State.WaitAgeSeconds=WaitStartSeconds>0.0?FMath::Max(0.0,State.ObservedSeconds-WaitStartSeconds):0.0;
    State.ReadinessPolls=ReadinessPolls;State.CaptureSubmissions=CaptureSubmissions;State.bBoundsCacheHit=bBoundsCacheHit;
    State.bMaterialCheckPending=CaptureMaterialStatus.IsValid()&&CaptureMaterialStatus->Load()==-2;
    ReadbackPerformanceState(State);
    double Earliest=MAX_dbl;
    for(const auto& Job:Queue){
        State.CoolingDownRecipes+=Job.RetryAfterSeconds>State.ObservedSeconds?1:0;
        Earliest=FMath::Min(Earliest,Job.RetryAfterSeconds);
    }
    if(!Queue.IsEmpty())State.NextEligibleSeconds=FMath::Max(0.0,Earliest-State.ObservedSeconds);
    State.bFailureDetailsLimited=Failed.Num()>RecentFailures.Num();
    if(!Queue.IsEmpty()){
        State.Key=Queue[0].Key;
        State.DeferredAttempts=Queue[0].DeferredAttempts;
        State.RequestAgeSeconds=FMath::Max(0.0,State.ObservedSeconds-Queue[0].RequestedSeconds);
        State.AttemptAgeSeconds=AttemptStartSeconds>0.0?FMath::Max(0.0,State.ObservedSeconds-AttemptStartSeconds):0.0;
    }
    return State;
}
const FSlateBrush* UColdSteelWeaponIcons::Find(const FColdSteelItem& I) const
{
    if(auto* E=Cache.Find(Key(I))){E->Use=++Serial;return &E->Brush;}return nullptr;
}
void UColdSteelWeaponIcons::Deinitialize()
{
    CancelReadback();
    ResetPreparation();
    Queue.Empty();Pending.Empty();OnReady.Clear();if(Capture){Capture->TextureTarget=nullptr;Studio->RemoveComponent(Capture);Capture->DestroyComponent();}
    CaptureMeshes.Empty();CaptureMaterials.Empty();CaptureTextures.Empty();
    if(MeleeMesh){ColdSteelModularSword::Clear(MeleeMesh);Studio->RemoveComponent(MeleeMesh);MeleeMesh->DestroyComponent();MeleeMesh=nullptr;}
    Capture=nullptr;Rig=nullptr;Studio.Reset();Target=nullptr;Cache.Empty();PreparedBoundsCache.Empty();Textures.Empty();Failed.Empty();RecentFailures.Empty();Super::Deinitialize();
}
bool UColdSteelWeaponIcons::Prepare(const FColdSteelItem& I)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_Prepare);
    FFPSPerformanceScope PrepareScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.Prepare"));
    if(PrepareStep==0){
    if(!Studio){
        FFPSPerformanceScope StudioScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.CreateStudio"));
        Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
        Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
        Studio->DirectionalLight->SetWorldRotation(FRotator(-35,-35,0));
        auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage(),NAME_None,RF_Transient);Fill->SetIntensity(3.f);Fill->SetCastShadows(false);Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));Studio->UpdateCaptureContents();
        Target=NewObject<UTextureRenderTarget2D>(this);Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor(0,0,0,1);Target->InitAutoFormat(768,320);Target->UpdateResourceImmediate(true);
        Capture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);Capture->TextureTarget=Target;Capture->CaptureSource=SCS_SceneColorHDR;Capture->ProjectionType=ECameraProjectionMode::Orthographic;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
        Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;Studio->AddComponent(Capture,FTransform::Identity);
    }
    PrepareStep=1;return true;
    }
    if(ColdSteelMeleePreview::Supports(I)){const bool Ready=PrepareMelee(I);PrepareStep=7;return Ready;}
    if(PrepareStep==1){
    if(!Rig){
        FFPSPerformanceScope RigScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.CreateRig"));
        FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
        Spawn.bTemporaryEditorActor=true;
#endif
        Rig=Studio->GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
        if(!Rig)return false;
        // This actor only supplies visuals; the editor preview flag also blocks
        // nested BeginPlay inherited from an actor in the gameplay world.
        Rig->SetActorTickEnabled(false);Rig->SetActorEnableCollision(false);
    }
    PrepareStep=2;return true;
    }
    if(Rig->HasActorBegunPlay())return false;
    if(PrepareStep==2){
    if(RigDefinition!=I.Definition){
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_InitializeVisuals);
        FFPSPerformanceScope VisualScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.InitializeVisuals"));
        Rig->ActiveInventoryWeaponDefinition=I.Definition;Rig->bUseM4Infima=I.Definition==TEXT("ue_m4a1");Rig->bUseQBZ191=I.Definition==TEXT("ue_qbz191");Rig->bUseASH12=I.Definition==TEXT("ue_ash12");Rig->bUseM16=I.Definition==TEXT("ue_m16a2");Rig->bUseM1911=I.Definition==TEXT("ue_m1911");Rig->bUseDanWesson715=I.Definition==TEXT("ue_dan_wesson715");Rig->InitializeWeaponVisuals(true);RigDefinition=I.Definition;
    }
    PrepareStep=3;return true;
    }
    auto* Mesh=Rig->AKMViewmodel.Get();if(!Mesh||!Mesh->GetSkeletalMeshAsset())return false;
    const auto* Asset=Mesh->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render||Render->LODRenderData.IsEmpty())return false;
    if(PrepareStep==6){
        if(!bCatalogExport)GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Warm(I,&WorkingBounds.Pickup);
        PrepareStep=7;return true;
    }
    FFPSPerformanceScope AssemblyScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.AssemblyAndBounds"));
    if(PrepareStep==3){
    if(AttachmentStep==0){
    Mesh->SetRelativeTransform(FTransform::Identity);Mesh->SetVisibility(true,true);
    Mesh->PlayAnimation(Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();Mesh->UpdateComponentToWorld();
    }
    const auto Parts=bCatalogExport?FGunsmithParts():GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(I);
    // One fitting per tick; the game-thread component APIs are not thread safe.
    if(AttachmentStep<9){
        const TCHAR* Slots[]={TEXT("underbarrel"),TEXT("optic"),TEXT("magazine"),TEXT("muzzle"),TEXT("stock"),TEXT("reargrip"),TEXT("tactical"),TEXT("bipod"),TEXT("sights")};
        FFPSPerformanceScope FitScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.AttachmentSlice"),Slots[AttachmentStep]);
        switch(AttachmentStep++){
        case 0:Rig->SetGunsmithHandstop(Parts.FindRef(TEXT("underbarrel")));break;
        case 1:Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));break;
        case 2:Rig->SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));break;
        case 3:Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));break;
        case 4:Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));break;
        case 5:Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")));break;
        case 6:Rig->SetGunsmithTactical(Parts.FindRef(TEXT("tactical")));break;
        case 7:Rig->SetGunsmithBipod(Parts.FindRef(TEXT("bipod")));break;
        default:Rig->UpdateFoldingSights(1.f);break;
        }
        return true;
    }
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
        // Handguard is a gun surface, not part of the first-person hands.
        const bool HandMaterial=Name.Contains(TEXT("hand"))&&!Name.Contains(TEXT("handguard"));
        if(Name.Contains(TEXT("manny"))||HandMaterial||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin"))Mesh->ShowMaterialSection(M,S,false,L);
    }
    const FVector Pivot=Mesh->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
    const FVector Barrel=(Mesh->GetSocketLocation(TEXT("WPN_FrontSight"))-Mesh->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    const FVector Up=Mesh->GetSocketLocation(TEXT("WPN_RearSight"))-Pivot;
    if(!Barrel.IsNearlyZero()){
        const FQuat Align=FRotationMatrix::MakeFromXZ(-FVector::RightVector,FVector::UpVector).ToQuat()*FRotationMatrix::MakeFromXZ(Barrel,Up).ToQuat().Inverse();
        FTransform Pose=Mesh->GetComponentTransform();Pose.SetLocation(FVector(500,0,0)+Align.RotateVector(Pose.GetLocation()-Pivot));Pose.SetRotation(Align*Pose.GetRotation());Mesh->SetWorldTransform(Pose);
    }
    Mesh->RefreshBoneTransforms();Mesh->UpdateChildTransforms();Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(Mesh);
    PrepareStep=4;return true;
    }
    const auto& LOD=Render->LODRenderData[0];
    TArray<USceneComponent*> Children;Mesh->GetChildrenComponents(true,Children);
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){Part->UpdateComponentToWorld();Capture->ShowOnlyComponent(Part);}
    const FString BoundsKey=Key(I);
    if(PrepareStep==4){
        if(!bBoundsStarted){
            if(const auto* Cached=PreparedBoundsCache.Find(BoundsKey)){
                WorkingBounds=*Cached;bBoundsCacheHit=true;PrepareStep=5;return true;
            }
            bBoundsStarted=true;bBoundsCacheHit=false;
            const auto SocketLocal=[Mesh](const TCHAR* Name){return Mesh->GetSocketTransform(FName(Name),RTS_Component).GetLocation();};
            const FVector LocalBarrel=(SocketLocal(TEXT("WPN_FrontSight"))-SocketLocal(TEXT("WPN_RearSight"))).GetSafeNormal();
            const FVector LocalUp=SocketLocal(TEXT("WPN_RearSight"))-SocketLocal(TEXT("WPN_SOCKET_Magazine"));
            BoundsPickupPose=FTransform(LocalBarrel.IsNearlyZero()?FQuat::Identity:FRotationMatrix::MakeFromXZ(LocalBarrel,LocalUp).ToQuat().Inverse());
            BoundsIconPose=Mesh->GetComponentTransform();
            Mesh->GetCurrentRefToLocalMatrices(BoundsBoneMatrices,0);
        }
        FFPSPerformanceScope BoundsScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.SkinnedBounds"));
        const double Deadline=FPlatformTime::Seconds()+.0015;
        if(auto* Weights=Mesh->GetSkinWeightBuffer(0)){
            while(BoundsSection<LOD.RenderSections.Num()){
                const auto& Section=LOD.RenderSections[BoundsSection];
                if(!Mesh->IsMaterialSectionShown(Section.MaterialIndex,0)){++BoundsSection;BoundsVertex=0;continue;}
                const uint32 End=FMath::Min(BoundsVertex+512,Section.NumVertices);
                for(;BoundsVertex<End;++BoundsVertex){
                    const FVector Vertex(USkinnedMeshComponent::GetSkinnedVertexPosition(Mesh,Section.BaseVertexIndex+BoundsVertex,LOD,*Weights,BoundsBoneMatrices));
                    WorkingBounds.Icon+=BoundsIconPose.TransformPosition(Vertex);
                    WorkingBounds.Pickup+=BoundsPickupPose.TransformPosition(Vertex);
                }
                if(BoundsVertex==Section.NumVertices){++BoundsSection;BoundsVertex=0;}
                if(BoundsSection<LOD.RenderSections.Num()&&FPlatformTime::Seconds()>=Deadline)return true;
            }
        }
        for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){
            WorkingBounds.Icon+=Part->GetStaticMesh()->GetBoundingBox().TransformBy(Part->GetComponentTransform());
            const FTransform LocalPart=Part->GetComponentTransform().GetRelativeTransform(BoundsIconPose);
            WorkingBounds.Pickup+=Part->GetStaticMesh()->GetBoundingBox().TransformBy(LocalPart*BoundsPickupPose);
        }
        if(!WorkingBounds.Icon.IsValid||!WorkingBounds.Pickup.IsValid)return false;
        if(PreparedBoundsCache.Num()>=64)PreparedBoundsCache.Empty();
        PreparedBoundsCache.Add(BoundsKey,WorkingBounds);
        BoundsBoneMatrices.Reset();PrepareStep=5;return true;
    }
    const FBox Bounds=WorkingBounds.Icon;
    if(!Bounds.IsValid)return false;
    // A mesh without a physics asset can retain rest-pose arms bounds far from the posed gun.
    // Enclose the measured pose for frustum culling; framing still uses the visible geometry above.
    Mesh->SetBoundsScale(1.f);Mesh->InvalidateCachedBounds();Mesh->UpdateBounds();
    const FVector Required=(Bounds.GetCenter()-Mesh->Bounds.Origin).GetAbs()+Bounds.GetExtent();
    const FVector Extent=Mesh->Bounds.BoxExtent;
    const float CullingScale=FMath::Max3(float(Required.X/FMath::Max(Extent.X,.01)),float(Required.Y/FMath::Max(Extent.Y,.01)),float(Required.Z/FMath::Max(Extent.Z,.01)));
    Mesh->SetBoundsScale(FMath::Max(1.f,CullingScale*1.02f));Mesh->InvalidateCachedBounds();Mesh->UpdateBounds();
    const int32 Width=(I.Definition==TEXT("ue_m1911")||I.Definition==TEXT("ue_dan_wesson715"))?480:768;
    if(Target->SizeX!=Width||Target->SizeY!=320)Target->ResizeTarget(Width,320);
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();const float Aspect=float(Width)/320.f;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();CaptureMeshes.Add(Mesh);
    // Only visible gun sections and mounted parts participate; hidden arms must not delay an icon.
    for(const auto& Section:LOD.RenderSections)if(Mesh->IsMaterialSectionShown(Section.MaterialIndex,0))
        if(auto* Material=Mesh->GetMaterial(Section.MaterialIndex))CaptureMaterials.AddUnique(Material);
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){
        CaptureMeshes.Add(Part);for(auto* Material:Part->GetMaterials())if(Material)CaptureMaterials.AddUnique(Material);
    }
    for(UMaterialInterface* Material:CaptureMaterials){
        TArray<UTexture*> Used;Material->GetUsedTextures(Used);
        for(auto* Texture:Used)if(Texture)CaptureTextures.AddUnique(Texture);
    }
    RequestCaptureTextureMips();
    Studio->GetWorld()->SendAllEndOfFrameUpdates();
    AssemblyScope.Finish();
    PrepareStep=6;
    UE_LOG(LogTemp,Display,TEXT("WeaponIcon: prepare key=%s mesh=%s parts=%d bounds=%s"),*Key(I),*Asset->GetPathName(),Capture->ShowOnlyComponents.Num(),*Size.ToString());
    return true;
}
namespace
{
int32 IconTextureMipCount(UTexture2D* Texture, int32 CaptureSize)
{
    const int32 MaxPixels=FMath::Min(2048u,FMath::RoundUpToPowerOfTwo(uint32(FMath::Max(256,CaptureSize*2))));
    int32 Mips=Texture->GetNumMips();
    int32 Dimension=FMath::Max(Texture->GetSizeX(),Texture->GetSizeY());
    while(Dimension>MaxPixels && Mips>1){Dimension=FMath::Max(1,Dimension/2);--Mips;}
    return FMath::Min(Mips,Texture->GetNumMipsAllowed(false));
}
}

void UColdSteelWeaponIcons::RequestCaptureTextureMips()
{
    for(UTexture* Texture:CaptureTextures){
        if(bCatalogExport)Texture->SetForceMipLevelsToBeResident(12.f);
        else IsCaptureTextureReady(Texture);
    }
}

bool UColdSteelWeaponIcons::IsCaptureTextureReady(UTexture* Texture)
{
    if(bCatalogExport)return Texture->IsFullyStreamedIn();
    if(auto* Texture2D=Cast<UTexture2D>(Texture)){
        // The runtime preview only needs mips appropriate to its render target. Do not pin
        // full 4K/8K weapon maps or take away the game scene's texture budget.
        if(Texture2D->VirtualTextureStreaming)return Texture2D->GetResource()!=nullptr;
        const int32 Wanted=IconTextureMipCount(Texture2D,FMath::Max(Target->SizeX,Target->SizeY));
        if(Wanted<=0 || !Texture2D->GetResource())return false;
        if(Texture2D->GetNumResidentMips()>=Wanted && !Texture2D->HasPendingInitOrStreaming())return true;
        if(!Texture2D->HasPendingInitOrStreaming())Texture2D->StreamIn(Wanted,false);
        return false;
    }
    return Texture->IsFullyStreamedIn();
}

void UColdSteelWeaponIcons::FinishJob(bool bSuccess)
{
    CancelReadback();
    ResetPreparation();
    const FString K=Queue[0].Key;
    UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),bSuccess?EFPSIconAction::Completed:EFPSIconAction::Failed);
    if(bSuccess)UFPSPerformanceMetricsSubsystem::RecordMarker(GetGameInstance(),TEXT("Icon.Completed"),K);
    else{
        FFPSIconFailure Failure;Failure.Recipe=K;Failure.Stage=FailureStage;Failure.Resource=FailureResource;
        Failure.Reason=FailureReason.IsEmpty()?TEXT("图标准备失败，尚无更细分原因"):FailureReason;
        Failure.bReasonTruncated=Failure.Reason.Len()>2048;Failure.Reason=Failure.Reason.Left(2048);
        Failure.Seconds=FPlatformTime::Seconds();Failure.FrameId=GFrameCounter;Failure.OccurredAtUtc=FDateTime::UtcNow().ToIso8601();
        if(RecentFailures.Num()==MaxFailureDetails)RecentFailures.RemoveAt(0,1,EAllowShrinking::No);
        RecentFailures.Add(Failure);
        UFPSPerformanceMetricsSubsystem::RecordMarker(GetGameInstance(),TEXT("Icon.Failed"),
            FString::Printf(TEXT("%s stage=%s resource=%s reason=%s%s"),*K,*Failure.Stage.ToString(),*Failure.Resource,*Failure.Reason,Failure.bReasonTruncated?TEXT(" [truncated]"):TEXT("")));
        UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: render failed %s; using catalog image"),*K);Failed.Add(K);
    }
    Pending.Remove(K);Queue.RemoveAt(0);Stage=0;Warmup=0;AttemptStartSeconds=0.0;CaptureMaterialStatus.Reset();
    WaitReason=NAME_None;WaitResource.Reset();WaitStartSeconds=0.0;
    ReadinessPolls=CaptureSubmissions=0;bBoundsCacheHit=false;
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_NotifyReady);
    FFPSPerformanceScope NotifyScope(GetGameInstance(),TEXT("Icon.NotifyReady"),K);
    OnReady.Broadcast(K);
}
void UColdSteelWeaponIcons::SetWaitState(FName Reason, const FString& Resource)
{
    if(WaitReason==Reason&&WaitResource==Resource)return;
    WaitReason=Reason;WaitResource=Resource;
    WaitStartSeconds=Reason.IsNone()?0.0:FPlatformTime::Seconds();
    if(!bCatalogExport&&!Queue.IsEmpty())UFPSPerformanceMetricsSubsystem::RecordMarker(GetGameInstance(),TEXT("Icon.WaitState"),
        FString::Printf(TEXT("%s reason=%s resource=%s"),*Queue[0].Key,*Reason.ToString(),*Resource));
}

bool UColdSteelWeaponIcons::SubmitMaterialReadiness()
{
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.MaterialReadinessSubmit"));
    FailureStage=TEXT("Icon.MaterialReadiness");
    TArray<const FMaterialRenderProxy*> Proxies;
    for(UMaterialInterface* Material:CaptureMaterials){
#if WITH_EDITOR
        if(const auto* Resource=Material->GetMaterialResource(Studio->GetScene()->GetShaderPlatform());Resource&&!Resource->GetCompileErrors().IsEmpty()){
            FailureResource=Material->GetPathName();FailureReason=FString::Join(Resource->GetCompileErrors(),TEXT("; "));
            UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: material compile failed %s: %s"),*FailureResource,*FailureReason);
            return false;
        }
#endif
        Proxies.Add(Material->GetRenderProxy());
    }
    if(Proxies.IsEmpty()){FailureReason=TEXT("没有可用于图标捕获的材质代理");return false;}
    CaptureMaterialStatus=MakeShared<TAtomic<int32>,ESPMode::ThreadSafe>(-2);
    const auto Status=CaptureMaterialStatus;
    const auto Level=Studio->GetScene()->GetFeatureLevel();
    ++ReadinessPolls;
    ENQUEUE_RENDER_COMMAND(WeaponIconMaterialsReady)([Status,Proxies,Level](FRHICommandListImmediate&){
        int32 Result=-1;
        for(int32 Index=0;Index<Proxies.Num();++Index){
            const FMaterialRenderProxy* Fallback=nullptr;
            if(!Proxies[Index]){Result=Index;break;}
            const auto& Material=Proxies[Index]->GetMaterialWithFallback(Level,Fallback);
            if(Fallback||!Material.IsRenderingThreadShaderMapComplete()){Result=Index;break;}
        }
        Status->Store(Result);
    });
    return true;
}

void UColdSteelWeaponIcons::DeferCurrentJob(double Now)
{
    // A blocked preview must eventually use its catalog image, not retain a permanent retry queue.
    if(Queue[0].DeferredAttempts>=5){
        FailureStage=TEXT("Icon.ReadinessBudget");FailureResource=WaitResource;
        FailureReason=FString::Printf(TEXT("图标准备超过 6 次尝试，使用目录图标；最后等待状态：%s"),*WaitReason.ToString());
        FinishJob(false);return;
    }
    UFPSPerformanceMetricsSubsystem::CountIconAction(GetGameInstance(),EFPSIconAction::Deferred);
    UFPSPerformanceMetricsSubsystem::RecordMarker(GetGameInstance(),TEXT("Icon.Deferred"),
        FString::Printf(TEXT("%s reason=%s resource=%s polls=%d captures=%d"),*Queue[0].Key,*WaitReason.ToString(),*WaitResource,ReadinessPolls,CaptureSubmissions));
    ResetPreparation();
    FJob Deferred=MoveTemp(Queue[0]);++Deferred.DeferredAttempts;
    Deferred.RetryAfterSeconds=Now+2.0*FMath::Min(Deferred.DeferredAttempts,4);
    UE_LOG(LogTemp,Display,TEXT("WeaponIcon: deferred %s reason=%s retry_in=%.1fs"),*Deferred.Key,*WaitReason.ToString(),Deferred.RetryAfterSeconds-Now);
    Queue.RemoveAt(0);Queue.Add(MoveTemp(Deferred));
    Stage=0;Warmup=0;AttemptStartSeconds=0.0;CaptureMaterialStatus.Reset();
    WaitReason=NAME_None;WaitResource.Reset();WaitStartSeconds=0.0;ReadinessPolls=CaptureSubmissions=0;bBoundsCacheHit=false;
}

void UColdSteelWeaponIcons::Tick(float Delta)
{
    if(Queue.IsEmpty())return;
    const double Now=FPlatformTime::Seconds();
    if(Stage==0){
        const int32 Eligible=Queue.IndexOfByPredicate([Now](const FJob& Job){return Job.RetryAfterSeconds<=Now;});
        if(Eligible==INDEX_NONE){SetWaitState(TEXT("RetryCooldown"));return;}
        if(Eligible>0){FJob Next=MoveTemp(Queue[Eligible]);Queue.RemoveAt(Eligible);Queue.Insert(MoveTemp(Next),0);}
    }
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_Tick);
    FFPSPerformanceScope TickScope(GetGameInstance(),TEXT("Icon.Tick"),Queue[0].Key);
    if(Stage==3){PollReadback();return;}
    if(Stage!=0){
        const double AttemptAge=Now-AttemptStartSeconds;
        if(AttemptAge>=(Stage==4?20.0:10.0)){DeferCurrentJob(Now);return;}
    }
    // Only yield after this tick has confirmed the blocker: a just-ready recipe should finish.
    const auto YieldForOtherJob=[this,Now](){
        if(Now-AttemptStartSeconds<2.0)return false;
        for(int32 Index=1;Index<Queue.Num();++Index)if(Queue[Index].RetryAfterSeconds<=Now){DeferCurrentJob(Now);return true;}
        return false;
    };
    if(Stage==0){
        ReadinessPolls=CaptureSubmissions=0;bBoundsCacheHit=false;
        FailureReason.Reset();FailureResource.Reset();FailureStage=TEXT("Icon.Prepare");AttemptStartSeconds=FPlatformTime::Seconds();
        BeginResourceLoad(Queue[0].Item);Stage=4;return;
    }
    else if(Stage==4){
        if(ResourceLoad&&!ResourceLoad->HasLoadCompleted())return;
        for(const auto& Ref:RequiredResources)if(!Ref.ResolveObject()){
            FailureStage=TEXT("Icon.AsyncResources");FailureResource=Ref.ToString();FailureReason=TEXT("异步加载结束但展示资源不可用");FinishJob(false);return;
        }
        Stage=5;AttemptStartSeconds=Now;SetWaitState(TEXT("PreparationSlices"));return;
    }
    else if(Stage==5){
        if(!Prepare(Queue[0].Item)){FinishJob(false);return;}
        if(PrepareStep>=7){Warmup=0;Stage=1;SetWaitState(TEXT("Warmup"));}
        return;
    }
    else if(Stage==1){
        Warmup+=Delta;if(Warmup<.3f)return;
        if(!SubmitMaterialReadiness()){FinishJob(false);return;}
        // One warm capture prepares scene resources. Polling readiness must not render the same scene repeatedly.
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_CaptureSubmit);
        FFPSPerformanceScope CaptureScope(GetGameInstance(),TEXT("Icon.CaptureSubmit"));
        Capture->CaptureScene();++CaptureSubmissions;Warmup=0;Stage=2;SetWaitState(TEXT("RenderReadiness"));return;
    }
    else if(Stage==2){
        Warmup+=Delta;
        const int32 MaterialStatus=CaptureMaterialStatus.IsValid()?CaptureMaterialStatus->Load():-2;
        if(MaterialStatus==-2){
            // Preserve the last known blocker/age while its next asynchronous query is pending.
            if(WaitReason!=FName(TEXT("MaterialShader")))SetWaitState(TEXT("RenderReadiness"));
            return;
        }
        if(MaterialStatus>=0){
            SetWaitState(TEXT("MaterialShader"),CaptureMaterials.IsValidIndex(MaterialStatus)?CaptureMaterials[MaterialStatus]->GetPathName():FString());
            if(YieldForOtherJob())return;
            if(Warmup>=.3f){Warmup=0;if(!SubmitMaterialReadiness())FinishJob(false);}
            return;
        }
        for(UTexture* Texture:CaptureTextures)if(!IsCaptureTextureReady(Texture)){
            SetWaitState(Texture->HasPendingInitOrStreaming()?TEXT("TextureStreaming"):TEXT("TextureNotFullyResident"),Texture->GetPathName());
            if(YieldForOtherJob())return;
            return;
        }
        SetWaitState(NAME_None);
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_FinalCaptureSubmit);
        FFPSPerformanceScope CaptureScope(GetGameInstance(),TEXT("Icon.FinalCaptureSubmit"));
        for(UMeshComponent* Part:CaptureMeshes)Part->MarkRenderStateDirty();Studio->GetWorld()->SendAllEndOfFrameUpdates();
        Capture->CaptureScene();++CaptureSubmissions;Stage=3;BeginReadback(Queue[0].Key);return;
    }
    FinishJob(false);
}

#if WITH_EDITOR
bool UColdSteelWeaponIcons::ExportCatalogIcon(const FString& Definition,const FString& Filename)
{
    // The commandlet supplies an uninitialized GameInstance solely as an UObject outer.
    // No profile subsystems, gameplay world or player equipment are created.
    bCatalogExport=true;
    FColdSteelItem Item;Item.Definition=Definition;Item.Data=TEXT("{}");
    FString CatalogText;TSharedPtr<FJsonObject> Catalog;
    if(FFileHelper::LoadFileToString(CatalogText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CatalogText),Catalog)&&Catalog)
    {
        const TSharedPtr<FJsonObject>* Data=nullptr;
        if(Catalog->TryGetObjectField(Definition,Data)){Item.Data.Reset();FJsonSerializer::Serialize((*Data).ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));}
    }
    Request(Item);Tick(0.f);
    FAssetCompilingManager::Get().FinishAllCompilation();
    for(UTexture* Texture:CaptureTextures)Texture->WaitForStreaming();
    FlushRenderingCommands();
    // Offline catalog authoring may wait; runtime Tick never blocks for a GPU fence or worker.
    const double Deadline=FPlatformTime::Seconds()+30.0;
    while(!IsIdle()&&FPlatformTime::Seconds()<Deadline){
        ++GFrameCounter;
        FAssetCompilingManager::Get().ProcessAsyncTasks();
        ENQUEUE_RENDER_COMMAND(WeaponIconBeginFrame)([](FRHICommandListImmediate&){++GFrameNumberRenderThread;});
        Tick(.05f);
        ENQUEUE_RENDER_COMMAND(WeaponIconEndFrame)([](FRHICommandListImmediate& RHICmdList){RHICmdList.EndFrame();});
        FlushRenderingCommands();
        FPlatformProcess::Sleep(.005f);
    }
    const auto* Entry=Textures.Find(Key(Item));if(!Entry)return false;
    auto* Texture=Entry->Get();auto& Mip=Texture->GetPlatformData()->Mips[0];
    TArray64<uint8> Png;
    const auto* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());
    FImageUtils::PNGCompressImageArray(Texture->GetSizeX(),Texture->GetSizeY(),TArrayView64<const FColor>(Pixels,int64(Texture->GetSizeX())*Texture->GetSizeY()),Png);
    Mip.BulkData.Unlock();
    const bool bSaved=FFileHelper::SaveArrayToFile(Png,*Filename);
    if(bSaved)UE_LOG(LogTemp,Display,TEXT("WeaponIconCatalog: wrote %s"),*Filename);
    return bSaved;
}
#endif
