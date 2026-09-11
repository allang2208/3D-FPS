#include "ColdSteelPickup.h"
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
    Prompt=CreateDefaultSubobject<UWidgetComponent>(TEXT("PickupPrompt"));Prompt->SetupAttachment(Body);Prompt->SetWidgetSpace(EWidgetSpace::Screen);Prompt->SetDrawSize(FVector2D(360,42));Prompt->SetWidgetClass(UColdSteelPickupPrompt::StaticClass());Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);Prompt->SetVisibility(false);
}
void AColdSteelPickup::InitializeItem(const FColdSteelItem& Item)
{
    ItemId=Item.InstanceId;const bool Gun=BuildWeapon(Item);if(!Gun)BuildConsumable(Item);Mesh->SetVisibility(!Gun);
    auto* Surface=NewObject<UPhysicalMaterial>(this);Surface->Friction=.8f;Surface->Restitution=.08f;Body->SetPhysMaterialOverride(Surface);
    Body->SetMassOverrideInKg(NAME_None,Gun?3.4f:.4f);Body->SetEnableGravity(true);Body->SetSimulatePhysics(true);
    BuildLootGlow(Item);
    Prompt->InitWidget();if(auto* UI=Cast<UColdSteelPickupPrompt>(Prompt->GetUserWidgetObject())){
        FString Name=ColdSteelInventory::Text(Item,TEXT("name"));if(Name.IsEmpty())Name=Item.Definition;
        UI->SetCaption(FString::Printf(TEXT("E · 拾取 %s ×%lld"),*Name,Item.Count));
    }
}
bool AColdSteelPickup::CanInteract(const APawn* Pawn)const{return !ItemId.IsEmpty()&&IsValid(Pawn)&&FVector::DistSquared(Pawn->GetActorLocation(),GetActorLocation())<=FMath::Square(250.f)&&ColdSteelWorldInteraction::IsFocused(Pawn,this);}
void AColdSteelPickup::Tick(float Delta)
{
    Super::Tick(Delta);auto* PC=UGameplayStatics::GetPlayerController(this,0);
    FaceLootBeam(PC);
    Prompt->SetWorldLocation(GetActorLocation()+FVector(0,0,Body->Bounds.BoxExtent.Z+15));Prompt->SetVisibility(PC&&CanInteract(PC->GetPawn()));
}
