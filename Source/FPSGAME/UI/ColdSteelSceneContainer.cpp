#include "ColdSteelSceneContainer.h"

#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "../FPSGAMEPlayerController.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

AColdSteelSceneContainer::AColdSteelSceneContainer()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("ContainerRoot"));
    Root->SetMobility(EComponentMobility::Static);
    SetRootComponent(Root);
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
    Body->SetupAttachment(Root);
    Body->SetMobility(EComponentMobility::Static);
    Body->SetCollisionProfileName(TEXT("BlockAll"));
    DoorHinge=CreateDefaultSubobject<USceneComponent>(TEXT("DoorHinge"));
    DoorHinge->SetupAttachment(Root);
    DoorHinge->SetMobility(EComponentMobility::Movable);
    DoorHinge->SetRelativeLocation(FVector(-29.f,28.4f,0.f));
    Door=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Door"));
    Door->SetupAttachment(DoorHinge);
    Door->SetMobility(EComponentMobility::Movable);
    Door->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Tags.Add(TEXT("ColdSteel.SceneContainer"));
    SetViewHighlighted(false);
}

void AColdSteelSceneContainer::BeginPlay()
{
    Super::BeginPlay();
    ClosedDoorRotation=DoorHinge->GetRelativeRotation();
    ClosedMovingPartLocation=DoorHinge->GetRelativeLocation();
    // No profile claim/reward is generated here. Each cabinet has its own grid;
    // the reward table will populate this key in a later production step.
    FString MapName=GetWorld()->GetMapName();
    MapName.RemoveFromStart(GetWorld()->StreamingLevelsPrefix);
    RuntimeStorageKey=TEXT("SceneSearch.")+MapName+TEXT(".")
        +(ContainerId.IsEmpty()?GetName():ContainerId);
    if(OpeningMotion==EColdSteelContainerMotion::Swing&&ActorHasTag(TEXT("ColdSteel.SceneContainer.RandomOpen"))&&FMath::FRand()<.32f)
    {
        FRotator Initial=ClosedDoorRotation;
        Initial.Yaw+=FMath::FRandRange(38.f,78.f);
        DoorHinge->SetRelativeRotation(Initial);
    }
    SetViewHighlighted(false);
}

void AColdSteelSceneContainer::ApplyOutline()
{
    // Dedicated post-process uses 201=unsearched, 202=searched. Other stencil
    // users (including first-person whirlwind 231) are left untouched.
    for(auto* Part:{Body.Get(),Door.Get()})
    {
        Part->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
        Part->SetCustomDepthStencilValue(bSearched?202:201);
    }
}

void AColdSteelSceneContainer::SetViewHighlighted(bool bHighlighted)
{
    ApplyOutline();
    for(auto* Part:{Body.Get(),Door.Get()})Part->SetRenderCustomDepth(bHighlighted);
}

FString AColdSteelSceneContainer::GetPromptLabel() const
{
    return Caption+(bOpening?TEXT(" · 开启中"):bSearched?TEXT(" · 再次查看"):TEXT(" · 搜寻"));
}

bool AColdSteelSceneContainer::IsWithinPanelReach(const APlayerController* Controller) const
{
    const APawn* Pawn=Controller?Controller->GetPawn().Get():nullptr;
    return Pawn&&Pawn->GetWorld()==GetWorld()&&Pawn->GetNetMode()!=NM_Client
        &&FVector::Dist(Pawn->GetActorLocation(),GetActorLocation()+FVector(0,0,70))<=240.f;
}

void AColdSteelSceneContainer::OpenLootPanel(APlayerController* Controller)
{
    const auto* PC=Cast<AFPSGAMEPlayerController>(Controller);
    auto* HUD=PC?PC->GetColdSteelHUD():nullptr;
    if(HUD&&!HUD->IsInventoryOpen()&&IsWithinPanelReach(Controller))
        HUD->OpenChestLootStorage(this,RuntimeStorageKey,FMath::Clamp(StoragePages,1,8),Caption+TEXT(" · 搜寻物品"));
}

bool AColdSteelSceneContainer::TrySearch(APlayerController* Controller)
{
    const auto* PC=Cast<AFPSGAMEPlayerController>(Controller);
    if(!PC||!PC->GetColdSteelHUD()||!Door||!Door->GetStaticMesh()||bOpening||!IsWithinPanelReach(Controller)
        ||ColdSteelWorldInteraction::FocusedSceneContainer(Controller)!=this)return false;
    if(bSearched){OpenLootPanel(Controller);return true;}
    bSearched=true;
    ApplyOutline();
    // An initially ajar cabinet is still unsearched. Continue from its current
    // pose to the original final opening angle, without snapping closed first.
    if(OpeningMotion==EColdSteelContainerMotion::Swing)
    {
        const FRotator Start=DoorHinge->GetRelativeRotation();
        OpenedYaw-=Start.Yaw-ClosedDoorRotation.Yaw;
        ClosedDoorRotation=Start;
    }
    bOpening=true;
    OpeningElapsed=0.f;
    OpeningController=Controller;
    SetActorTickEnabled(true);
    return true;
}

void AColdSteelSceneContainer::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    OpeningElapsed+=DeltaSeconds;
    const float T=FMath::Clamp(OpeningElapsed/FMath::Max(.1f,OpeningDuration),0.f,1.f);
    const float Ease=T*T*(3.f-2.f*T);
    if(OpeningMotion==EColdSteelContainerMotion::Drawer||OpeningMotion==EColdSteelContainerMotion::OpenShelf)
        DoorHinge->SetRelativeLocation(ClosedMovingPartLocation+DrawerTravel*Ease);
    else
    {
        FRotator Rotation=ClosedDoorRotation;
        Rotation.Yaw+=OpenedYaw*Ease;
        DoorHinge->SetRelativeRotation(Rotation);
    }
    if(T>=1.f)
    {
        bOpening=false;
        SetActorTickEnabled(false);
        OpenLootPanel(OpeningController.Get());
        OpeningController.Reset();
    }
}

void AColdSteelSceneContainer::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    OpeningController.Reset();
    SetActorTickEnabled(false);
    Super::EndPlay(EndPlayReason);
}
