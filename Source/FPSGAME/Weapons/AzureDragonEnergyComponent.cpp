#include "AzureDragonEnergyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SceneView.h"

namespace AzureDragonEnergy
{
const FSoftObjectPath ColumnPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Meshes/SM_AzureDragonEnergyColumnV9.SM_AzureDragonEnergyColumnV9"));
const FSoftObjectPath FlamePath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Meshes/SM_AzureDragonEnergyFlameV9.SM_AzureDragonEnergyFlameV9"));
const FSoftObjectPath ColumnMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Materials/M_AzureDragonEnergyColumnV9.M_AzureDragonEnergyColumnV9"));
const FSoftObjectPath FlameMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Materials/M_AzureDragonEnergyFlameV9.M_AzureDragonEnergyFlameV9"));
const FSoftObjectPath CrestPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Meshes/SM_AzureDragonEnergyCrestV9.SM_AzureDragonEnergyCrestV9"));
const FSoftObjectPath HelixPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Meshes/SM_AzureDragonEnergyHelixV9.SM_AzureDragonEnergyHelixV9"));
const FSoftObjectPath CrestMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Materials/M_AzureDragonEnergyCrestV9.M_AzureDragonEnergyCrestV9"));
const FSoftObjectPath HelixMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Materials/M_AzureDragonEnergyHelixV9.M_AzureDragonEnergyHelixV9"));
}

UAzureDragonEnergyComponent::UAzureDragonEnergyComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UAzureDragonEnergyComponent::Configure(bool Enabled)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    Enabled=Enabled&&Pawn&&Pawn->IsLocallyControlled();
    if(Enabled!=bEnabled){EntryAge=0.f;bHaveYaw=false;}
    bEnabled=Enabled;
    SetComponentTickEnabled(Enabled);
    if(!Enabled){ClearEnergy();HideDisplay();return;}
    RequestAssets();
    if(ColumnMesh&&FlameMesh&&ColumnMaterial&&FlameMaterial&&CrestMesh&&HelixMesh&&CrestMaterial&&HelixMaterial)CreateDisplay();
}

void UAzureDragonEnergyComponent::SetEnergy(float NormalizedEnergy,bool Summoned,bool ContactPulse)
{
    TargetEnergy=FMath::Clamp(NormalizedEnergy,0.f,1.f);
    if(ContactPulse)HitAge=0.f;
    if(Summoned){DisplayEnergy=1.f;FlareAge=0.f;}
}

void UAzureDragonEnergyComponent::ClearEnergy()
{
    TargetEnergy=DisplayEnergy=0.f;HitAge=FlareAge=10.f;
}

void UAzureDragonEnergyComponent::RequestAssets()
{
    if(bRequested)return;
    bRequested=true;
    TWeakObjectPtr<UAzureDragonEnergyComponent> Weak(this);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{AzureDragonEnergy::ColumnPath,AzureDragonEnergy::FlamePath,
            AzureDragonEnergy::ColumnMaterialPath,AzureDragonEnergy::FlameMaterialPath,
            AzureDragonEnergy::CrestPath,AzureDragonEnergy::HelixPath,
            AzureDragonEnergy::CrestMaterialPath,AzureDragonEnergy::HelixMaterialPath},
        FStreamableDelegate::CreateLambda([Weak]()
        {
            if(!Weak.IsValid())return;
            auto* Self=Weak.Get();
            Self->ColumnMesh=Cast<UStaticMesh>(AzureDragonEnergy::ColumnPath.ResolveObject());
            Self->FlameMesh=Cast<UStaticMesh>(AzureDragonEnergy::FlamePath.ResolveObject());
            Self->ColumnMaterial=Cast<UMaterialInterface>(AzureDragonEnergy::ColumnMaterialPath.ResolveObject());
            Self->FlameMaterial=Cast<UMaterialInterface>(AzureDragonEnergy::FlameMaterialPath.ResolveObject());
            Self->CrestMesh=Cast<UStaticMesh>(AzureDragonEnergy::CrestPath.ResolveObject());
            Self->HelixMesh=Cast<UStaticMesh>(AzureDragonEnergy::HelixPath.ResolveObject());
            Self->CrestMaterial=Cast<UMaterialInterface>(AzureDragonEnergy::CrestMaterialPath.ResolveObject());
            Self->HelixMaterial=Cast<UMaterialInterface>(AzureDragonEnergy::HelixMaterialPath.ResolveObject());
            if(Self->bEnabled)Self->CreateDisplay();
        }));
}

void UAzureDragonEnergyComponent::CreateDisplay()
{
    if(Column||!ColumnMesh||!FlameMesh||!ColumnMaterial||!FlameMaterial
        ||!CrestMesh||!HelixMesh||!CrestMaterial||!HelixMaterial)return;
    auto Create=[&](UStaticMesh* Mesh,UMaterialInterface* Material,UMaterialInstanceDynamic*& MID)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());
        C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);
        C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);
        C->SetOnlyOwnerSee(true);C->SetVisibleInRayTracing(false);C->SetHiddenInGame(true);
        MID=UMaterialInstanceDynamic::Create(Material,this);
        MID->SetScalarParameterValue(TEXT("Reveal"),0.f);
        C->SetMaterial(0,MID);C->RegisterComponent();return C;
    };
    UMaterialInstanceDynamic* VesselMID=nullptr;UMaterialInstanceDynamic* FireMID=nullptr;
    Column=Create(ColumnMesh,ColumnMaterial,VesselMID);ColumnMID=VesselMID;
    Flame=Create(FlameMesh,FlameMaterial,FireMID);FlameMID=FireMID;
    UMaterialInstanceDynamic* DragonMID=nullptr;UMaterialInstanceDynamic* RuneMID=nullptr;
    Crest=Create(CrestMesh,CrestMaterial,DragonMID);CrestMID=DragonMID;
    Helix=Create(HelixMesh,HelixMaterial,RuneMID);HelixMID=RuneMID;
}

void UAzureDragonEnergyComponent::HideDisplay()
{
    if(Column)Column->SetHiddenInGame(true);
    if(Flame)Flame->SetHiddenInGame(true);
    if(Crest)Crest->SetHiddenInGame(true);
    if(Helix)Helix->SetHiddenInGame(true);
}

void UAzureDragonEnergyComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!bEnabled||!Column||!Flame||!Crest||!Helix)return;
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!Pawn||!PC||!Pawn->IsLocallyControlled()||PC->GetViewTarget()!=Pawn){HideDisplay();return;}
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {ClearEnergy();HideDisplay();return;}
    const auto* Local=PC->GetLocalPlayer();FSceneViewProjectionData Projection;
    if(!Local||!Local->ViewportClient||!Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))
    {HideDisplay();return;}
    Age=FMath::Fmod(Age+Delta,3600.f);EntryAge+=Delta;HitAge+=Delta;FlareAge+=Delta;
    // Briefly show the full vessel and flare before presenting the consumed charge.
    if(FlareAge>=.20f)DisplayEnergy=FMath::FInterpConstantTo(DisplayEnergy,TargetEnergy,Delta,3.8f);
    const float TanH=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[0][0]));
    const float TanV=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[1][1]));
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    const FQuat ViewRotation=View.Quaternion();
    const FVector Forward=ViewRotation.GetAxisX(),Right=ViewRotation.GetAxisY(),Up=ViewRotation.GetAxisZ();
    const float YawSpeed=bHaveYaw?FMath::FindDeltaAngleDegrees(LastYaw,View.Yaw)/FMath::Max(.001f,Delta):0.f;
    LastYaw=View.Yaw;bHaveYaw=true;
    Sway=FMath::FInterpTo(Sway,FMath::Clamp(-YawSpeed*.007f+FVector::DotProduct(Pawn->GetVelocity(),Right)*.002f,-2.f,2.f),Delta,9.f);
    constexpr float Depth=80.f;
    // Fit the complete dragon/fire silhouette, keeping the central aiming lane clear.
    const float Scale=FMath::Min(Depth*TanH*.14f/6.f,Depth*TanV*.82f/30.f);
    const float Bob=.38f*FMath::Sin(Age*1.73f+.6f);
    const FVector Center=Eye+Forward*(Depth+.14f*Scale*FMath::Sin(Age*.83f))
        -Right*(Depth*TanH*.85f)+Up*(Depth*TanV*.02f+(Bob-5.f)*Scale);
    const FQuat Hover=ViewRotation*FRotator(0.f,-12.f+Sway,.35f*FMath::Sin(Age*.91f)).Quaternion();
    Column->SetWorldTransform(FTransform(Hover,Center,FVector(Scale)));
    // All layers share a real 3D origin. Fire is curved geometry, not a forward card.
    Flame->SetWorldTransform(FTransform(Hover,Center,FVector(Scale)));
    Crest->SetWorldTransform(FTransform(Hover,Center,FVector(Scale)));
    const FQuat Orbit=Hover*FQuat(FVector::UpVector,Age*.12f);
    Helix->SetWorldTransform(FTransform(Orbit,Center,FVector(Scale)));
    Column->SetHiddenInGame(false);Flame->SetHiddenInGame(DisplayEnergy<=.001f);
    Crest->SetHiddenInGame(false);Helix->SetHiddenInGame(false);
    const float Reveal=FMath::SmoothStep(0.f,.24f,EntryAge);
    const float Pulse=FMath::Exp(-HitAge*10.f);
    const float Burst=1.f-FMath::SmoothStep(.04f,.42f,FlareAge);
    for(auto* MID:{ColumnMID.Get(),FlameMID.Get(),CrestMID.Get(),HelixMID.Get()})
    {
        MID->SetScalarParameterValue(TEXT("Fill"),DisplayEnergy);
        MID->SetScalarParameterValue(TEXT("Age"),Age);
        MID->SetScalarParameterValue(TEXT("Reveal"),Reveal);
        MID->SetScalarParameterValue(TEXT("Pulse"),Pulse);
        MID->SetScalarParameterValue(TEXT("Burst"),Burst);
    }
}

void UAzureDragonEnergyComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    HideDisplay();
    if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();
    if(Column)Column->DestroyComponent();if(Flame)Flame->DestroyComponent();
    if(Crest)Crest->DestroyComponent();if(Helix)Helix->DestroyComponent();
    Column=nullptr;Flame=nullptr;ColumnMID=nullptr;FlameMID=nullptr;
    Crest=nullptr;Helix=nullptr;CrestMID=nullptr;HelixMID=nullptr;
    Super::EndPlay(Reason);
}
