#include "ColdSteelSlidingDoor.h"
#include "ColdSteelDoor.h"
#include "ColdSteelWindow.h"
#include "ColdSteelRevolvingDoor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 与平开门同族的补缝网格（框 40×120×240、扇 94.74×226.42），两扇各缩为洞口半宽对滑。
    const TCHAR* SlidingLeafMesh=TEXT("/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40.SM_SingleDoorLeaf_D40");
    const TCHAR* SlidingFrameMesh=TEXT("/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40.SM_SingleDoorFrame_D40");
    // 开/关门音效与平开门同一套（qubodup DoorSet，CC0）。
    const TCHAR* SlidingOpenSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_Open.S_Door_Open");
    const TCHAR* SlidingCloseSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_Close.S_Door_Close");
}

AColdSteelSlidingDoor::AColdSteelSlidingDoor()
{
    PrimaryActorTick.bCanEverTick=true;
    bReplicates=true;SetReplicateMovement(true);
    DoorRoot=CreateDefaultSubobject<USceneComponent>(TEXT("DoorRoot"));
    SetRootComponent(DoorRoot);

    static ConstructorHelpers::FObjectFinder<USoundBase> OpenAsset(SlidingOpenSoundPath);
    static ConstructorHelpers::FObjectFinder<USoundBase> CloseAsset(SlidingCloseSoundPath);
    if(OpenAsset.Succeeded())OpenSound=OpenAsset.Object;
    if(CloseAsset.Succeeded())CloseSound=CloseAsset.Object;

    Frame=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DoorFrame"));
    Frame->SetupAttachment(DoorRoot);
    Frame->SetMobility(EComponentMobility::Movable);
    Frame->SetCollisionProfileName(TEXT("BlockAll"));
    Frame->SetCanEverAffectNavigation(false);

    LeafLeft=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeafLeft"));
    LeafLeft->SetupAttachment(DoorRoot);
    LeafLeft->SetMobility(EComponentMobility::Movable);
    LeafLeft->SetCollisionProfileName(TEXT("BlockAll"));
    LeafLeft->SetCanEverAffectNavigation(false);

    LeafRight=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeafRight"));
    LeafRight->SetupAttachment(DoorRoot);
    LeafRight->SetMobility(EComponentMobility::Movable);
    LeafRight->SetCollisionProfileName(TEXT("BlockAll"));
    LeafRight->SetCanEverAffectNavigation(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeafAsset(SlidingLeafMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> FrameAsset(SlidingFrameMesh);
    if(LeafAsset.Succeeded()){LeafLeft->SetStaticMesh(LeafAsset.Object);LeafRight->SetStaticMesh(LeafAsset.Object);}
    if(FrameAsset.Succeeded())Frame->SetStaticMesh(FrameAsset.Object);
}

void AColdSteelSlidingDoor::BeginPlay()
{
    Super::BeginPlay();
    if(HasAuthority())NetScale=GetActorScale3D();
    else OnRep_Setup();
    AlignGeometry();
    if(!HasAuthority())OnRep_Swing();
}

void AColdSteelSlidingDoor::AlignGeometry()
{
    if(const UStaticMesh* FrameMesh=Frame->GetStaticMesh())
    {
        const FBoxSphereBounds Bounds=FrameMesh->GetBounds();
        Frame->SetRelativeLocation(FVector(-Bounds.Origin.X,-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
    }
    if(const UStaticMesh* LeafMesh=LeafLeft->GetStaticMesh())
    {
        // 两扇各缩为洞口半宽（Y 0.5），关拢时中缝相接铺满洞口；缩放按包围盒折算定位。
        const FBoxSphereBounds Bounds=LeafMesh->GetBounds();
        LeafLeft->SetRelativeScale3D(FVector(1.f,0.5f,1.f));
        LeafRight->SetRelativeScale3D(FVector(1.f,0.5f,1.f));
        const FVector ScaledOrigin=Bounds.Origin*FVector(1.f,0.5f,1.f);
        const FVector ScaledExtent=Bounds.BoxExtent*FVector(1.f,0.5f,1.f);
        LeafHalfCm=ScaledExtent;
        LeafOriginCm=ScaledOrigin;
        const float HalfSpan=ScaledExtent.Y;   // 半扇宽 = 缩放后的包围盒 Y 半尺寸
        ClosedLeftLoc=FVector(-ScaledOrigin.X,-HalfSpan-ScaledOrigin.Y,ScaledExtent.Z-ScaledOrigin.Z);
        ClosedRightLoc=FVector(-ScaledOrigin.X, HalfSpan-ScaledOrigin.Y,ScaledExtent.Z-ScaledOrigin.Z);
        LeafLeft->SetRelativeLocation(ClosedLeftLoc);
        LeafRight->SetRelativeLocation(ClosedRightLoc);
    }
}

bool AColdSteelSlidingDoor::IsSlideBlocked() const
{
    UWorld* World=GetWorld();
    if(!World||LeafHalfCm.IsNearlyZero())return false;
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_WorldStatic);
    ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
    ObjectParams.AddObjectTypesToQuery(ECC_Destructible);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelSlideDoor),false,this);
    Params.AddIgnoredActor(this);
    if(const AActor* Parent=GetAttachParentActor())Params.AddIgnoredActor(Parent);
    // 略缩检测盒（2/4cm），避免与门框贴合面产生假阻塞。
    const FVector Extent=FVector(FMath::Max(1.f,LeafHalfCm.X-2.f),FMath::Max(1.f,LeafHalfCm.Y-2.f),
        FMath::Max(1.f,LeafHalfCm.Z-4.f));
    const FCollisionShape Shape=FCollisionShape::MakeBox(Extent);
    // 两扇全开位置的包围盒中心：闭位中心 ± SlideDistance。
    const float HalfSpan=LeafHalfCm.Y;
    for(const float Side:{-1.f,1.f})
    {
        const FVector LocalCentre=FVector(0.f,Side*(HalfSpan+SlideDistanceCm),LeafHalfCm.Z);
        TArray<FOverlapResult> Hits;
        if(!World->OverlapMultiByObjectType(Hits,GetActorTransform().TransformPosition(LocalCentre),
            GetActorQuat(),ObjectParams,Shape,Params))continue;
        for(const FOverlapResult& Hit:Hits)
        {
            const AActor* Blocker=Hit.GetActor();
            // 门族互免（与平开门同一口径）：相邻门板/窗扇互不死锁。
            if(Blocker&&(Cast<AColdSteelDoor>(Blocker)||Cast<AColdSteelWindow>(Blocker)||
                Cast<AColdSteelSlidingDoor>(Blocker)||Cast<AColdSteelRevolvingDoor>(Blocker)))continue;
            UE_LOG(LogTemp,Display,TEXT("ColdSteelSlidingDoor %s 滑动被挡：侧=%s 阻挡=%s:%s"),*GetName(),
                Side<0.f?TEXT("-"):TEXT("+"),*GetNameSafe(Blocker),*GetNameSafe(Hit.Component.Get()));
            return true;
        }
    }
    return false;
}

bool AColdSteelSlidingDoor::OpenDoorFrom(const APawn* InstigatorPawn)
{
    if(!HasAuthority()||bOpen)return bOpen;
    // 滑动路径被实体挡住就拒绝开门（与平开门“两侧皆堵不开”同一口径，2026-10-04 用户拍板）。
    if(IsSlideBlocked())
    {
        UE_LOG(LogTemp,Display,TEXT("ColdSteelSlidingDoor %s 滑动路径被阻挡，拒绝开门"),*GetName());
        return false;
    }
    bOpen=true;
    NetSwing.bOpen=true;
    NetSwing.From=CurrentOffset;
    NetSwing.To=SlideDistanceCm;
    NetSwing.Speed=SlideSpeedCm;
    NetSwing.StartedAt=FColdSteelDoorNetState::Now(GetWorld());
    AutoCloseRemaining=AutoCloseSeconds;
    ForceNetUpdate();
    MulticastDoorSound(true);
    UE_LOG(LogTemp,Display,TEXT("ColdSteelSlidingDoor %s 开门"),*GetName());
    return true;
}

void AColdSteelSlidingDoor::CloseDoor()
{
    if(!HasAuthority()||!bOpen)return;
    bOpen=false;
    NetSwing.bOpen=false;
    NetSwing.From=CurrentOffset;
    NetSwing.To=0.f;
    NetSwing.Speed=SlideSpeedCm;
    NetSwing.StartedAt=FColdSteelDoorNetState::Now(GetWorld());
    AutoCloseRemaining=0.f;
    ForceNetUpdate();
    MulticastDoorSound(false);
}

void AColdSteelSlidingDoor::MulticastDoorSound_Implementation(bool bOpening)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Sound=bOpening?OpenSound.Get():CloseSound.Get())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,GetActorLocation());
}

void AColdSteelSlidingDoor::ToggleDoorFrom(const APawn* InstigatorPawn)
{
    if(bOpen)CloseDoor();else OpenDoorFrom(InstigatorPawn);
}

void AColdSteelSlidingDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!HasAuthority())CurrentOffset=NetSwing.Angle(GetWorld());
    else CurrentOffset=FMath::FInterpConstantTo(CurrentOffset,NetSwing.To,DeltaSeconds,SlideSpeedCm);
    ApplyOffset();
    UpdateLeafPawnCollision();
    if(HasAuthority()&&bOpen&&FMath::IsNearlyEqual(CurrentOffset,NetSwing.To,.5f))
    {
        AutoCloseRemaining-=DeltaSeconds;
        if(AutoCloseRemaining<=0.f)CloseDoor();
    }
}

void AColdSteelSlidingDoor::ApplyOffset()
{
    // 绝对定位：闭位相对坐标 ± 当前偏移，避免增量累加漂移。
    if(LeafLeft)LeafLeft->SetRelativeLocation(ClosedLeftLoc+FVector(0.f,-CurrentOffset,0.f));
    if(LeafRight)LeafRight->SetRelativeLocation(ClosedRightLoc+FVector(0.f, CurrentOffset,0.f));
}

bool AColdSteelSlidingDoor::LeavesOverlapPawn() const
{
    UWorld* World=GetWorld();
    if(!World||LeafHalfCm.IsNearlyZero())return false;
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelSlideDoorPawn),false,this);
    Params.AddIgnoredActor(this);
    const FVector Extent=FVector(FMath::Max(1.f,LeafHalfCm.X-2.f),FMath::Max(1.f,LeafHalfCm.Y-2.f),
        FMath::Max(1.f,LeafHalfCm.Z-4.f));
    const FCollisionShape Shape=FCollisionShape::MakeBox(Extent);
    for(const UStaticMeshComponent* Leaf:{LeafLeft.Get(),LeafRight.Get()})
    {
        if(!Leaf)continue;
        const FTransform Transform=Leaf->GetComponentTransform();
        if(World->OverlapAnyTestByObjectType(Transform.TransformPosition(LeafOriginCm),Transform.GetRotation(),
            ObjectParams,Shape,Params))return true;
    }
    return false;
}

void AColdSteelSlidingDoor::UpdateLeafPawnCollision()
{
    // 与平开门同一口径：关着且已静止才挡 Pawn，开/关过程与开着时放行。
    const bool bSettled=FMath::IsNearlyEqual(CurrentOffset,NetSwing.To,.5f);
    const bool bBlock=!bOpen&&bSettled;
    for(UStaticMeshComponent* Leaf:{LeafLeft,LeafRight})
    {
        if(!Leaf)continue;
        const bool bBlockingNow=Leaf->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
        bool bWants=bBlock;
        if(bWants&&!bBlockingNow&&LeavesOverlapPawn())bWants=false;
        if(bWants!=bBlockingNow)Leaf->SetCollisionResponseToChannel(ECC_Pawn,bWants?ECR_Block:ECR_Ignore);
    }
}

void AColdSteelSlidingDoor::Configure(UMaterialInterface* Surface)
{
    if(!Surface)return;
    if(HasAuthority()){NetSurface=Surface;ForceNetUpdate();}
    for(UStaticMeshComponent* Part:{Frame,LeafLeft,LeafRight})
        if(Part)for(int32 Index=0;Index<FMath::Max(1,Part->GetNumMaterials());++Index)Part->SetMaterial(Index,Surface);
}

void AColdSteelSlidingDoor::OnRep_Swing()
{
    bOpen=NetSwing.bOpen;
}

void AColdSteelSlidingDoor::OnRep_Setup()
{
    if(NetSurface)Configure(NetSurface);
    if(!NetScale.IsNearlyZero()&&!GetActorScale3D().Equals(NetScale))SetActorScale3D(NetScale);
}

void AColdSteelSlidingDoor::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelSlidingDoor,NetSwing);
    DOREPLIFETIME(AColdSteelSlidingDoor,NetSurface);
    DOREPLIFETIME(AColdSteelSlidingDoor,NetScale);
}
