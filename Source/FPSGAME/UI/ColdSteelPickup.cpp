#include "ColdSteelPickup.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "UObject/ConstructorHelpers.h"
AColdSteelPickup::AColdSteelPickup()
{
    PrimaryActorTick.bCanEverTick=false;
    Mesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PickupMesh"));SetRootComponent(Mesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube.Cube"));if(Shape.Succeeded())Mesh->SetStaticMesh(Shape.Object);
    Mesh->SetWorldScale3D(FVector(.20f));Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("PickupLabel"));Label->SetupAttachment(Mesh);Label->SetRelativeLocation(FVector(0,0,100));Label->SetWorldSize(36);Label->SetHorizontalAlignment(EHTA_Center);Label->SetText(FText::FromString(TEXT("[E] Pick up")));
}
void AColdSteelPickup::InitializeItem(const FColdSteelItem& Item){ItemId=Item.InstanceId;Label->SetText(FText::FromString(FString::Printf(TEXT("[E] %s x%lld"),*Item.Definition,Item.Count)));}
