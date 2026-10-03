#include "M4GunsmithWidget.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/Bow/BowAssembly.h"
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
    if(G->IsBow(Item.Definition)){SetStandaloneBowItem(Item);return;}
    // 采集工具没有 world_mesh，走 tool_mesh 的独立预览，不进剑类或角色枪架路径。
    if(G->IsTool(Item.Definition)){SetStandaloneToolItem(Item);return;}
    if(ColdSteelMeleePreview::Supports(Item)){SetStandaloneMeleeItem(Item);return;}
    if(!G->Weapon(Item.Definition)){CloseStandalonePreview();return;}
    if(StandaloneMelee)CloseStandalonePreview();
    const auto Parts=G->Installed(Item);TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();
    FString Key=Item.InstanceId+TEXT("|")+Item.Definition;for(const auto& N:Names)Key+=TEXT("|")+N+TEXT("=")+Parts[N];
    if(Key==StandaloneKey&&StandaloneRig)return;
    InitializePreview();if(!Studio)return;
    if(!StandaloneRig)
    {
        FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
        Spawn.bTemporaryEditorActor=true;
#endif
        StandaloneRig=Studio->GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
    }
    if(!StandaloneRig)return;
    auto* Rig=StandaloneRig.Get();Rig->SetActorTickEnabled(false);Rig->SetActorEnableCollision(false);
    Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima=(Item.Definition==TEXT("ue_m4a1")||Item.Definition==TEXT("ue_hk416"));Rig->bUseQBZ191=Item.Definition==TEXT("ue_qbz191");Rig->bUseASH12=Item.Definition==TEXT("ue_ash12");Rig->bUseM16=Item.Definition==TEXT("ue_m16a2");Rig->bUseM1911=(Item.Definition==TEXT("ue_m1911")||Item.Definition==TEXT("ue_g18")||Item.Definition==TEXT("ue_pit_viper2011"));Rig->bUseDanWesson715=(Item.Definition==TEXT("ue_dan_wesson715")||Item.Definition==TEXT("ue_rsh12"));Rig->InitializeWeaponVisuals();
    Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")),G->Weapon(Item.Definition));Rig->SetGunsmithTactical(Parts.FindRef(TEXT("tactical")));Rig->SetGunsmithHandstop(Parts.FindRef(TEXT("underbarrel")));Rig->UpdateFoldingSights(1.f);
    Rig->SetGunsmithBipod(Parts.FindRef(TEXT("bipod")));
    StandaloneKey=Key;StandaloneParts=Parts;PreviewBoundsCache.Empty();SetSidePreview(true);
}
void UM4GunsmithWidget::PoseStandalone()
{
    if(StandaloneMelee){if(ColdSteelBowAssembly::IsBowRoot(StandaloneMelee))SyncStandaloneBowPreview();else SyncStandaloneMeleePreview();return;}
    if(!StandaloneRig)return;auto* Rig=StandaloneRig.Get();auto* Mesh=Rig->AKMViewmodel.Get();
    Mesh->SetVisibility(true);if(!Rig->SampleRSH12Presentation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation)){Mesh->PlayAnimation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);}Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
    Rig->FirstPersonCamera->SetFieldOfView(Rig->VerticalToHorizontalFOV(bAimPreview?Rig->EffectiveADSVerticalFOV():Rig->BaseVerticalFieldOfView));
    Rig->SetGunsmithInspection(!bAimPreview);
    // SyncStudioPreview applies the same arm mask to standalone and equipped guns.
    if(bAimPreview){Rig->bSightCalibrated=false;Rig->UpdateADSPose();Mesh->SetRelativeTransform(FTransform(Rig->CalibratedADSRotation,Rig->CalibratedADSLocation,FVector(Rig->ViewmodelScale)));}
    Mesh->UpdateComponentToWorld();Mesh->UpdateChildTransforms();PreviewBoundsCache.Empty();
}
void UM4GunsmithWidget::TickStandalonePreview(float Delta,TSharedPtr<SWidget> Surface){PreviewSurface=Surface;TickCapture(Delta);}
void UM4GunsmithWidget::CloseStandalonePreview(){StandaloneRig=nullptr;StandaloneKey.Reset();StandaloneParts.Empty();ReleasePreview();}
