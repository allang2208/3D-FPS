#include "ColdSteelWeaponIcons.h"
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
#include "Rendering/SkeletalMeshRenderData.h"
#include "TextureResource.h"
#include "RenderingThread.h"
#include "Materials/Material.h"
#include "MaterialShared.h"
#include "Materials/MaterialRenderProxy.h"
#include "SceneInterface.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#endif

bool UColdSteelWeaponIcons::Supports(const FColdSteelItem& I) const {return ColdSteelMeleePreview::Supports(I)||I.Definition==TEXT("ue_m4a1")||I.Definition==TEXT("ue_akm")||I.Definition==TEXT("ue_qbz191")||I.Definition==TEXT("ue_ash12")||I.Definition==TEXT("ue_m16a2")||(I.Definition==TEXT("ue_m1911")||I.Definition==TEXT("ue_dan_wesson715"));}
FString UColdSteelWeaponIcons::Key(const FColdSteelItem& I) const
{
    if(ColdSteelModularSword::Supports(I))return I.Definition+TEXT("|")+ColdSteelModularSword::Key(I,nullptr,!bCatalogExport);
    if(ColdSteelMeleePreview::Supports(I))return I.Definition+TEXT("|")+ColdSteelMeleePreview::MeshPath(I)+TEXT("|")+(bCatalogExport?FString():ColdSteelMeleeRune::Selected(I));
    const auto Parts=bCatalogExport?FGunsmithParts():GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(I);TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();
    FString Result=I.Definition;for(const auto& N:Names)Result+=TEXT("|")+N+TEXT("=")+Parts[N];return Result;
}
void UColdSteelWeaponIcons::Request(const FColdSteelItem& I)
{
    if(!Supports(I))return;const FString K=Key(I);if(auto* E=Cache.Find(K)){E->Use=++Serial;return;}
    if(Pending.Contains(K)||Failed.Contains(K))return;Pending.Add(K);Queue.Add({I,K});
}
const FSlateBrush* UColdSteelWeaponIcons::Find(const FColdSteelItem& I) const
{
    if(auto* E=Cache.Find(Key(I))){E->Use=++Serial;return &E->Brush;}return nullptr;
}
void UColdSteelWeaponIcons::Deinitialize()
{
    Queue.Empty();Pending.Empty();OnReady.Clear();if(Capture){Capture->TextureTarget=nullptr;Studio->RemoveComponent(Capture);Capture->DestroyComponent();}
    CaptureMeshes.Empty();CaptureMaterials.Empty();CaptureTextures.Empty();
    if(MeleeMesh){ColdSteelModularSword::Clear(MeleeMesh);Studio->RemoveComponent(MeleeMesh);MeleeMesh->DestroyComponent();MeleeMesh=nullptr;}
    Capture=nullptr;Rig=nullptr;Studio.Reset();Target=nullptr;Cache.Empty();Textures.Empty();Failed.Empty();Super::Deinitialize();
}
bool UColdSteelWeaponIcons::Prepare(const FColdSteelItem& I)
{
    if(!Studio){
        Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
        Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
        Studio->DirectionalLight->SetWorldRotation(FRotator(-35,-35,0));
        auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage(),NAME_None,RF_Transient);Fill->SetIntensity(3.f);Fill->SetCastShadows(false);Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));Studio->UpdateCaptureContents();
        Target=NewObject<UTextureRenderTarget2D>(this);Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor(0,0,0,1);Target->InitAutoFormat(768,320);Target->UpdateResourceImmediate(true);
        Capture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);Capture->TextureTarget=Target;Capture->CaptureSource=SCS_SceneColorHDR;Capture->ProjectionType=ECameraProjectionMode::Orthographic;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
        Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;Studio->AddComponent(Capture,FTransform::Identity);
    }
    if(ColdSteelMeleePreview::Supports(I))return PrepareMelee(I);
    if(!Rig){
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
    if(Rig->HasActorBegunPlay())return false;
    if(RigDefinition!=I.Definition){Rig->bUseM4Infima=I.Definition==TEXT("ue_m4a1");Rig->bUseQBZ191=I.Definition==TEXT("ue_qbz191");Rig->bUseASH12=I.Definition==TEXT("ue_ash12");Rig->bUseM16=I.Definition==TEXT("ue_m16a2");Rig->bUseM1911=I.Definition==TEXT("ue_m1911");Rig->bUseDanWesson715=I.Definition==TEXT("ue_dan_wesson715");Rig->InitializeWeaponVisuals();RigDefinition=I.Definition;}
    auto* Mesh=Rig->AKMViewmodel.Get();if(!Mesh||!Mesh->GetSkeletalMeshAsset())return false;
    Mesh->SetRelativeTransform(FTransform::Identity);Mesh->SetVisibility(true,true);
    Mesh->PlayAnimation(Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();Mesh->UpdateComponentToWorld();
    const auto Parts=bCatalogExport?FGunsmithParts():GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(I);
    Rig->SetGunsmithHandstop(Parts.FindRef(TEXT("underbarrel")));
    Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")));Rig->SetGunsmithTactical(Parts.FindRef(TEXT("tactical")));Rig->UpdateFoldingSights(1.f);
    const auto* Asset=Mesh->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render||Render->LODRenderData.IsEmpty())return false;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
        if(Name.Contains(TEXT("manny"))||Name.Contains(TEXT("hand"))||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin"))Mesh->ShowMaterialSection(M,S,false,L);
    }
    const FVector Pivot=Mesh->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
    const FVector Barrel=(Mesh->GetSocketLocation(TEXT("WPN_FrontSight"))-Mesh->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    const FVector Up=Mesh->GetSocketLocation(TEXT("WPN_RearSight"))-Pivot;
    if(!Barrel.IsNearlyZero()){
        const FQuat Align=FRotationMatrix::MakeFromXZ(-FVector::RightVector,FVector::UpVector).ToQuat()*FRotationMatrix::MakeFromXZ(Barrel,Up).ToQuat().Inverse();
        FTransform Pose=Mesh->GetComponentTransform();Pose.SetLocation(FVector(500,0,0)+Align.RotateVector(Pose.GetLocation()-Pivot));Pose.SetRotation(Align*Pose.GetRotation());Mesh->SetWorldTransform(Pose);
    }
    Mesh->RefreshBoneTransforms();Mesh->UpdateChildTransforms();Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(Mesh);
    FBox Bounds(ForceInit);const auto& LOD=Render->LODRenderData[0];
    if(auto* Weights=Mesh->GetSkinWeightBuffer(0)){
        TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);
        for(const auto& Section:LOD.RenderSections)if(Mesh->IsMaterialSectionShown(Section.MaterialIndex,0))for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
            Bounds+=Mesh->GetComponentTransform().TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Mesh,V,LOD,*Weights,Matrices)));
    }
    TArray<USceneComponent*> Children;Mesh->GetChildrenComponents(true,Children);
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){Part->UpdateComponentToWorld();Bounds+=Part->GetStaticMesh()->GetBoundingBox().TransformBy(Part->GetComponentTransform());Capture->ShowOnlyComponent(Part);}
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
        for(auto* Texture:Used)if(Texture){CaptureTextures.AddUnique(Texture);Texture->SetForceMipLevelsToBeResident(12.f);}
    }
    for(UMeshComponent* Part:CaptureMeshes)Part->PrestreamTextures(12.f,true);
    Studio->GetWorld()->SendAllEndOfFrameUpdates();
    if(!bCatalogExport)GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Warm(I);
    UE_LOG(LogTemp,Display,TEXT("WeaponIcon: prepare key=%s mesh=%s parts=%d bounds=%s"),*Key(I),*Asset->GetPathName(),Capture->ShowOnlyComponents.Num(),*Size.ToString());
    return true;
}
bool UColdSteelWeaponIcons::Readback(const FString& K)
{
    TArray<FLinearColor> Linear;FReadSurfaceDataFlags Flags(RCM_MinMax);Flags.SetLinearToGamma(false);
    const int32 Width=Target->SizeX,Height=Target->SizeY;
    if(!Target->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(Linear,Flags)||Linear.Num()!=Width*Height){
        UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: readback size=%d expected=%dx%d key=%s"),Linear.Num(),Width,Height,*K);return false;
    }
    TArray<FColor> Pixels;Pixels.Reserve(Linear.Num());int32 Visible=0;
    for(auto P:Linear){const float Alpha=FMath::Clamp(1.f-P.A,0.f,1.f);if(Alpha>.1f)++Visible;P.A=Alpha;auto Color=P.ToFColorSRGB();Color.A=FMath::RoundToInt(Alpha*255);Pixels.Add(Color);}
    if(Visible<100){UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: empty capture key=%s visible=%d"),*K,Visible);return false;}
    auto* Texture=UTexture2D::CreateTransient(Width,Height,PF_B8G8R8A8);if(!Texture)return false;Texture->SRGB=true;Texture->NeverStream=true;Texture->Filter=TF_Bilinear;
    auto& Mip=Texture->GetPlatformData()->Mips[0];void* Data=Mip.BulkData.Lock(LOCK_READ_WRITE);FMemory::Memcpy(Data,Pixels.GetData(),Pixels.Num()*sizeof(FColor));Mip.BulkData.Unlock();Texture->UpdateResource();
    if(Cache.Num()>=64){FString Old;uint64 Use=MAX_uint64;for(const auto& Pair:Cache)if(Pair.Value.Use<Use){Use=Pair.Value.Use;Old=Pair.Key;}Cache.Remove(Old);Textures.Remove(Old);}
    Textures.Add(K,Texture);auto& E=Cache.Add(K);E.Use=++Serial;E.Brush.SetResourceObject(Texture);E.Brush.ImageSize=FVector2D(Width,Height);E.Brush.DrawAs=ESlateBrushDrawType::Image;
    ++Completed;UE_LOG(LogTemp,Display,TEXT("WeaponIcon: ready key=%s visible=%d renders=%d"),*K,Visible,Completed);return true;
}
void UColdSteelWeaponIcons::FinishJob(bool bSuccess)
{
    const FString K=Queue[0].Key;
    if(!bSuccess){UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: render failed %s; using catalog image"),*K);Failed.Add(K);}
    Pending.Remove(K);Queue.RemoveAt(0);Stage=0;Warmup=0;JobSeconds=0;CaptureMaterialsReady.Reset();
    OnReady.Broadcast();
}
void UColdSteelWeaponIcons::Tick(float Delta)
{
    if(Queue.IsEmpty())return;
    // Shader/texture preparation can outlast the first icon request. Yield to
    // other items, then retry this pending recipe instead of permanently
    // caching a failure and leaving an old catalog image for the whole session.
    if(Stage!=0){JobSeconds+=Delta;if(JobSeconds>=10.f){
        UE_LOG(LogTemp,Display,TEXT("WeaponIcon: material preparation deferred %s"),*Queue[0].Key);
        FJob Deferred=MoveTemp(Queue[0]);Queue.RemoveAt(0);Queue.Add(MoveTemp(Deferred));
        Stage=0;Warmup=0;JobSeconds=0;CaptureMaterialsReady.Reset();return;
    }}
    if(Stage==0){JobSeconds=0;if(Prepare(Queue[0].Item)){Warmup=0;Stage=1;return;}}
    else if(Stage==1){
        Warmup+=Delta;if(Warmup<.3f)return;
        CaptureMaterialsReady.Reset();
        {
            CaptureMaterialsReady=MakeShared<TAtomic<bool>,ESPMode::ThreadSafe>(false);
            const auto Ready=CaptureMaterialsReady;TArray<const FMaterialRenderProxy*> Proxies;
            for(UMaterialInterface* Material:CaptureMaterials){
#if WITH_EDITOR
                if(const auto* Resource=Material->GetMaterialResource(Studio->GetScene()->GetShaderPlatform());Resource&&!Resource->GetCompileErrors().IsEmpty()){
                    UE_LOG(LogTemp,Warning,TEXT("WeaponIcon: material compile failed %s: %s"),*Material->GetPathName(),*FString::Join(Resource->GetCompileErrors(),TEXT("; ")));
                    FinishJob(false);return;
                }
#endif
                Proxies.Add(Material->GetRenderProxy());
            }
            if(Proxies.IsEmpty()){FinishJob(false);return;}
            const auto Level=Studio->GetScene()->GetFeatureLevel();
            // Warm captures are required to prepare this preview's render resources.
            // Only cache an image once the render thread uses the actual materials.
            ENQUEUE_RENDER_COMMAND(WeaponIconMaterialsReady)([Ready,Proxies,Level](FRHICommandListImmediate&){
                bool Complete=!Proxies.IsEmpty();for(const auto* Proxy:Proxies){const FMaterialRenderProxy* Fallback=nullptr;const auto& Material=Proxy->GetMaterialWithFallback(Level,Fallback);Complete&=!Fallback&&Material.IsRenderingThreadShaderMapComplete();}Ready->Store(Complete);
            });
        }
        Capture->CaptureScene();Stage=2;return;
    }
    else if((CaptureMaterialsReady.IsValid()&&!CaptureMaterialsReady->Load())||CaptureTextures.ContainsByPredicate([](const auto& Texture){return !Texture->IsFullyStreamedIn();})){Warmup=0;Stage=1;return;}
    else if(Stage==2&&CaptureMaterialsReady.IsValid()){
        for(UMeshComponent* Part:CaptureMeshes)Part->MarkRenderStateDirty();Studio->GetWorld()->SendAllEndOfFrameUpdates();
        Capture->CaptureScene();Stage=3;return;
    }
    else if(Readback(Queue[0].Key)){FinishJob(true);return;}
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
    for(int32 Frame=0;!IsIdle()&&Frame<240;++Frame){
        ++GFrameCounter;
        FAssetCompilingManager::Get().ProcessAsyncTasks();
        ENQUEUE_RENDER_COMMAND(WeaponIconBeginFrame)([](FRHICommandListImmediate&){++GFrameNumberRenderThread;});
        Tick(.05f);
        ENQUEUE_RENDER_COMMAND(WeaponIconEndFrame)([](FRHICommandListImmediate& RHICmdList){RHICmdList.EndFrame();});
        FlushRenderingCommands();
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
