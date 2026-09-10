#include "ColdSteelWarehouseChest.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Materials/MaterialInterface.h"
void UColdSteelChestPrompt::NativeOnInitialized()
{
    Super::NativeOnInitialized();auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(TEXT("E · 武器仓库")));T->SetFont(ColdSteelUI::TextFont(16));T->SetColorAndOpacity(ColdSteelUI::TextPrimary);T->SetJustification(ETextJustify::Center);WidgetTree->RootWidget=T;
}
AColdSteelWarehouseChest::AColdSteelWarehouseChest()
{
    PrimaryActorTick.bCanEverTick=true;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Root);
    Collision=CreateDefaultSubobject<UBoxComponent>(TEXT("ChestCollision"));Collision->SetupAttachment(Root);Collision->SetBoxExtent(FVector(55,73,37));Collision->SetRelativeLocation(FVector(0,0,37));Collision->SetCollisionProfileName(TEXT("BlockAll"));
    Mesh=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("OriginalChest"));Mesh->SetupAttachment(Root);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Prompt=CreateDefaultSubobject<UWidgetComponent>(TEXT("InteractionPrompt"));Prompt->SetupAttachment(Root);Prompt->SetRelativeLocation(FVector(0,0,150));Prompt->SetWidgetSpace(EWidgetSpace::Screen);Prompt->SetDrawSize(FVector2D(220,45));Prompt->SetWidgetClass(UColdSteelChestPrompt::StaticClass());Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AColdSteelWarehouseChest::BeginPlay()
{
    Super::BeginPlay();FString JSON;TSharedPtr<FJsonObject> Root;
    if(FFileHelper::LoadFileToString(JSON,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/warehouse_assets.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(JSON),Root)){
        FString Path;if(!ChestAsset&&Root->TryGetStringField(TEXT("mesh"),Path))ChestAsset=LoadObject<USkeletalMesh>(nullptr,*Path);
        if(!OpenClip&&Root->TryGetStringField(TEXT("open"),Path))OpenClip=LoadObject<UAnimSequence>(nullptr,*Path);
        if(!CloseClip&&Root->TryGetStringField(TEXT("close"),Path))CloseClip=LoadObject<UAnimSequence>(nullptr,*Path);
    }
    if(ChestAsset)Mesh->SetSkeletalMesh(ChestAsset);
    const TSharedPtr<FJsonObject>* Surfaces=nullptr;
    if(Root.IsValid()&&Root->TryGetObjectField(TEXT("materials"),Surfaces))for(int32 Index=0;Index<Mesh->GetNumMaterials();++Index){
        auto* Original=Mesh->GetMaterial(Index);FString Path;
        if(Original&&(*Surfaces)->TryGetStringField(Original->GetName(),Path))if(auto* Surface=LoadObject<UMaterialInterface>(nullptr,*Path))Mesh->SetMaterial(Index,Surface);
    }
    if(CloseClip){Mesh->PlayAnimation(CloseClip,false);Mesh->SetPosition(CloseClip->GetPlayLength(),false);Mesh->SetPlayRate(0);}
    UE_LOG(LogTemp,Display,TEXT("WarehouseChest: mesh=%s open=%.3f close=%.3f"),*GetNameSafe(ChestAsset),OpenClip?OpenClip->GetPlayLength():0,CloseClip?CloseClip->GetPlayLength():0);
}
bool AColdSteelWarehouseChest::CanInteract(const APawn* Pawn)const
{
    return IsWithinReach(Pawn)&&ColdSteelWorldInteraction::IsFocused(Pawn,this,InteractionRadius);
}
bool AColdSteelWarehouseChest::IsWithinReach(const APawn* Pawn)const
{
    return IsValid(Pawn)&&Pawn->GetWorld()==GetWorld()&&Pawn->GetNetMode()==NM_Standalone&&FVector::Dist(Pawn->GetActorLocation(),GetActorLocation()+FVector(0,0,70))<=InteractionRadius;
}
void AColdSteelWarehouseChest::SetOpen(bool Open)
{
    bDesiredOpen=Open;if(bAnimating||bIsOpen==Open)return;
    auto* Clip=Open?OpenClip.Get():CloseClip.Get();if(!Clip)return;
    bAnimating=true;bPlayingOpen=Open;Elapsed=0;Mesh->SetPlayRate(1);Mesh->PlayAnimation(Clip,false);
}
void AColdSteelWarehouseChest::Tick(float Delta)
{
    Super::Tick(Delta);auto* PC=UGameplayStatics::GetPlayerController(this,0);Prompt->SetVisibility(PC&&!PC->bShowMouseCursor&&CanInteract(PC->GetPawn())&&!bDesiredOpen);
    if(bAnimating){Elapsed+=Delta;auto* Clip=bPlayingOpen?OpenClip.Get():CloseClip.Get();if(Clip&&Elapsed>=Clip->GetPlayLength()){
        Mesh->SetPosition(Clip->GetPlayLength(),false);Mesh->SetPlayRate(0);bIsOpen=bPlayingOpen;bAnimating=false;SetOpen(bDesiredOpen);
    }}
}
