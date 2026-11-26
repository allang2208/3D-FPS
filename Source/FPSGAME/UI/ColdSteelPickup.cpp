#include "ColdSteelPickup.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Components/TextBlock.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "UObject/ConstructorHelpers.h"
#include "Net/UnrealNetwork.h"
void UColdSteelPickupPrompt::NativeOnInitialized()
{
    Super::NativeOnInitialized();Text=WidgetTree->ConstructWidget<UTextBlock>();Text->SetFont(ColdSteelUI::TextFont(16));Text->SetColorAndOpacity(ColdSteelUI::TextPrimary);Text->SetJustification(ETextJustify::Center);WidgetTree->RootWidget=Text;
}
void UColdSteelPickupPrompt::SetCaption(const FString& Caption){if(Text)Text->SetText(FText::FromString(Caption));}
AColdSteelPickup::AColdSteelPickup()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.05f;
    Body=CreateDefaultSubobject<UBoxComponent>(TEXT("PickupBody"));SetRootComponent(Body);Body->SetBoxExtent(FVector(8));
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->SetCollisionObjectType(ECC_PhysicsBody);
    Body->SetCollisionResponseToAllChannels(ECR_Block);Body->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);Body->SetCollisionResponseToChannel(ECC_Camera,ECR_Ignore);
    Body->SetGenerateOverlapEvents(false);Body->SetUseCCD(true);Body->SetLinearDamping(.25f);Body->SetAngularDamping(1.8f);
    Mesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PickupMesh"));Mesh->SetupAttachment(Body);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube.Cube"));if(Shape.Succeeded())Mesh->SetStaticMesh(Shape.Object);
    Mesh->SetRelativeScale3D(FVector(.16f));Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LootFXRoot=CreateDefaultSubobject<USceneComponent>(TEXT("LootFXRoot"));LootFXRoot->SetupAttachment(Body);LootFXRoot->SetAbsolute(false,true,true);
    LootBeam=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LootBeam"));LootBeam->SetupAttachment(LootFXRoot);LootBeam->SetCollisionEnabled(ECollisionEnabled::NoCollision);LootBeam->SetCastShadow(false);LootBeam->SetVisibility(false);LootBeam->SetCullDistance(8000.f);
    LootCenter=CreateDefaultSubobject<UMaterialBillboardComponent>(TEXT("LootCenter"));LootCenter->SetupAttachment(LootFXRoot);LootCenter->SetCollisionEnabled(ECollisionEnabled::NoCollision);LootCenter->SetCastShadow(false);LootCenter->SetVisibility(false);LootCenter->SetCullDistance(8000.f);
    Weapon=CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("DroppedWeapon"));Weapon->SetupAttachment(Body);Weapon->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AColdSteelPickup::InitializeItem(const FColdSteelItem& Item)
{
    ItemId=Item.InstanceId;const bool Gun=BuildWeapon(Item);if(!Gun&&!BuildProductionTool(Item)&&!BuildProductionMaterial(Item)&&!BuildVoxelBlock(Item))BuildConsumable(Item);Mesh->SetVisibility(!Gun);
    auto* Surface=NewObject<UPhysicalMaterial>(this);Surface->Friction=.8f;Surface->Restitution=.08f;Body->SetPhysMaterialOverride(Surface);
    Body->SetMassOverrideInKg(NAME_None,Gun?3.4f:bVoxelBlock?2.5f:bProductionMaterial?ProductionMassKg:.4f);Body->SetEnableGravity(true);Body->SetSimulatePhysics(HasAuthority()&&(!bProductionMaterial||bProductionMaterialReady));
    BuildLootGlow(Item);
    FString Name=ColdSteelInventory::Text(Item,TEXT("name"));if(Name.IsEmpty())Name=Item.Definition;
    PromptCaption=FString::Printf(TEXT("拾取 %s ×%lld"),*Name,Item.Count); // 准星统一小浮窗读取；不再有模型上方名牌
}
void AColdSteelPickup::InitializeSharedItem(const FColdSteelItem& Item)
{
    if(!HasAuthority())return;
    SharedItem=Item;SetReplicates(true);SetReplicateMovement(true);
    SetNetUpdateFrequency(10.f);SetMinNetUpdateFrequency(2.f);
    InitializeItem(Item);ForceNetUpdate();
}
void AColdSteelPickup::OnRep_SharedItem()
{
    InitializeItem(SharedItem);
    // Definition and movement notifications can arrive in either order.
    // InitializeItem rebuilds the collision body and disables local simulation;
    // restore physics already received from authority and its latest target.
    // Otherwise an unchanged bRepPhysics bit never enables the body again,
    // leaving the client pickup suspended at its original spawn transform.
    if(IsReplicatingMovement()&&GetReplicatedMovement().bRepPhysics)
    {
        SyncReplicatedPhysicsSimulation();
        PostNetReceivePhysicState();
    }
}
void AColdSteelPickup::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(AColdSteelPickup,SharedItem,COND_InitialOnly);
}
bool AColdSteelPickup::CanInteract(const APawn* Pawn)const{return !bWorkbenchDisplay&&!ItemId.IsEmpty()&&IsValid(Pawn)&&FVector::DistSquared(Pawn->GetActorLocation(),GetActorLocation())<=FMath::Square(250.f)&&ColdSteelWorldInteraction::IsFocused(Pawn,this);}
void AColdSteelPickup::Tick(float Delta)
{
    Super::Tick(Delta);auto* PC=UGameplayStatics::GetPlayerController(this,0);
    if(bProductionMaterial)TickProductionMaterial(Delta);
    FaceLootBeam(PC);
}


bool AColdSteelPickup::IsWorkbenchDisplayReady() const
{
    if(!bWorkbenchDisplay||(StaffLoad.IsValid()&&!StaffLoad->HasLoadCompleted())
        ||(ProductionToolLoad.IsValid()&&!ProductionToolLoad->HasLoadCompleted()))return false;
    if(Weapon->IsVisible()&&Weapon->GetSkinnedAsset())return true;
    if(Mesh->IsVisible()&&Mesh->GetStaticMesh())return true;
    // Skeletal bow risers live under a deliberately empty static assembly root.
    // Readiness must recognize the actual rendered children, not that root only.
    TArray<USceneComponent*> Parts;Mesh->GetChildrenComponents(true,Parts);
    for(auto* Part:Parts)
    {
        if(auto* Static=Cast<UStaticMeshComponent>(Part);Static&&Static->IsVisible()&&Static->GetStaticMesh())return true;
        if(auto* Skin=Cast<USkinnedMeshComponent>(Part);Skin&&Skin->IsVisible()&&Skin->GetSkinnedAsset())return true;
    }
    return false;
}
bool AColdSteelPickup::InitializeWorkbenchDisplay(const FColdSteelItem& Item)
{
    bWorkbenchDisplay=true;ItemId=Item.InstanceId;SetReplicates(false);
    SetActorEnableCollision(false);SetActorTickEnabled(false);
    Body->SetSimulatePhysics(false);Body->SetEnableGravity(false);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LootFXRoot->SetVisibility(false,true);PromptCaption.Reset();
    bool Built=false;
    const bool Gun=BuildWeapon(Item);
    if(Gun)Built=true;
    else if(ColdSteelInventory::IsBow(Item))
    {
        Mesh->SetRelativeScale3D(FVector(1));
        TArray<FSoftObjectPath> Paths;ColdSteelBowAssembly::GatherResources(Item,Paths);
        Mesh->SetStaticMesh(nullptr);Body->SetBoxExtent(FVector(8,8,60));
        StaffLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Item]()
        {
            if(!bWorkbenchDisplay||ItemId!=Item.InstanceId||!ColdSteelBowAssembly::Apply(Mesh,Item))return;
            const FBox B=ColdSteelBowAssembly::LocalBounds(Mesh);Mesh->SetRelativeLocation(-B.GetCenter());
            Body->SetBoxExtent(B.GetExtent().ComponentMax(FVector(1)));Mesh->SetVisibility(true,true);
        }));
        Built=StaffLoad.IsValid();
    }
    else Built=BuildProductionTool(Item)||BuildConsumable(Item);
    Mesh->SetVisibility(Built&&!Gun,true);
    Weapon->SetVisibility(Built&&Gun);
    if(!Built)SetActorHiddenInGame(true);
    return Built;
}
