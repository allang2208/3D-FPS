#include "M4GunsmithWidget.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

void UM4GunsmithWidget::SetStandaloneItem(const FColdSteelItem& Item)
{
    bStandalone=true;auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!G->Weapon(Item.Definition)){CloseStandalonePreview();return;}
    const auto Parts=G->Installed(Item);TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();
    FString Key=Item.InstanceId+TEXT("|")+Item.Definition;for(const auto& N:Names)Key+=TEXT("|")+N+TEXT("=")+Parts[N];
    if(Key==StandaloneKey&&StandaloneRig)return;
    InitializePreview();if(!Studio)return;
    if(!StandaloneRig){FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;StandaloneRig=Studio->GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);}
    if(!StandaloneRig)return;
    auto* Rig=StandaloneRig.Get();Rig->SetActorTickEnabled(false);Rig->SetActorEnableCollision(false);
    Rig->bUseM4Infima=Item.Definition==TEXT("ue_m4a1");Rig->bUseQBZ191=Item.Definition==TEXT("ue_qbz191");Rig->bUseM1911=Item.Definition==TEXT("ue_m1911");Rig->InitializeWeaponVisuals();
    Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithDrum(Parts.FindRef(TEXT("magazine"))==TEXT("large_drum"));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));Rig->SetGunsmithTactical(Parts.FindRef(TEXT("tactical")));Rig->SetGunsmithHandstop(Parts.FindRef(TEXT("underbarrel")));Rig->UpdateFoldingSights(1.f);
    StandaloneKey=Key;StandaloneParts=Parts;PreviewBoundsCache.Empty();SetSidePreview(true);
}
void UM4GunsmithWidget::PoseStandalone()
{
    if(!StandaloneRig)return;auto* Rig=StandaloneRig.Get();auto* Mesh=Rig->AKMViewmodel.Get();
    Mesh->SetVisibility(true);Mesh->PlayAnimation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
    Rig->FirstPersonCamera->SetFieldOfView(Rig->VerticalToHorizontalFOV(bAimPreview?Rig->EffectiveADSVerticalFOV():Rig->BaseVerticalFieldOfView));
    Rig->SetGunsmithInspection(!bAimPreview);
    if(auto* Asset=Mesh->GetSkeletalMeshAsset())if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            if(Name.Contains(TEXT("manny"))||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin")||Name.Contains(TEXT("hands")))Mesh->ShowMaterialSection(M,S,bAimPreview,L);
        }
    if(bAimPreview){Rig->bSightCalibrated=false;Rig->UpdateADSPose();Mesh->SetRelativeTransform(FTransform(Rig->CalibratedADSRotation,Rig->CalibratedADSLocation,FVector(Rig->ViewmodelScale)));}
    Mesh->UpdateComponentToWorld();Mesh->UpdateChildTransforms();PreviewBoundsCache.Empty();
}
void UM4GunsmithWidget::TickStandalonePreview(float Delta,TSharedPtr<SWidget> Surface){PreviewSurface=Surface;TickCapture(Delta);}
void UM4GunsmithWidget::CloseStandalonePreview(){StandaloneRig=nullptr;StandaloneKey.Reset();StandaloneParts.Empty();ReleasePreview();}
