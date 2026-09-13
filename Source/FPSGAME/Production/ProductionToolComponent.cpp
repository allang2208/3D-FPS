#include "ProductionToolComponent.h"
#include "ProductionHarvestSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"

UProductionToolComponent::UProductionToolComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UProductionToolComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    if (!Pawn || Pawn->GetNetMode()!=NM_Standalone) { SetComponentTickEnabled(false); return; }
    AddTickPrerequisiteActor(Pawn);
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Pivot=NewObject<USceneComponent>(Pawn,TEXT("ProductionToolPivot"));
    Pawn->AddInstanceComponent(Pivot); Pivot->SetupAttachment(Camera); Pivot->RegisterComponent();
    Pivot->SetRelativeLocation(FVector(55,24,-35));
    ToolMesh=NewObject<UStaticMeshComponent>(Pawn,TEXT("ProductionToolMesh"));
    Pawn->AddInstanceComponent(ToolMesh); ToolMesh->SetupAttachment(Pivot);
    ToolMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); ToolMesh->SetCanEverAffectNavigation(false);
    ToolMesh->SetCastShadow(false); ToolMesh->SetOnlyOwnerSee(true); ToolMesh->SetVisibility(false); ToolMesh->RegisterComponent();
    if (auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->GrantProductionTools();
    RefreshHeldTool();
}

void UProductionToolComponent::RefreshHeldTool()
{
    if (!ToolMesh) return;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const FString Id=Item?Item->InstanceId:FString();
    if (Id==EquippedId) return;
    CancelUse(); EquippedId=Id; Kind.Reset(); Feedback.Reset();
    ToolMesh->SetVisibility(false); ToolMesh->SetStaticMesh(nullptr); HitSound=nullptr;
    if (LoadHandle) { LoadHandle->CancelHandle(); LoadHandle.Reset(); }
    if (!Item) return;
    Kind=ColdSteelInventory::Text(*Item,TEXT("tool_kind")); ToolName=ColdSteelInventory::Text(*Item,TEXT("name"));
    if(Kind==TEXT("axe")||Kind==TEXT("pickaxe"))
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->Prepare(Kind==TEXT("axe"));
    SwingSeconds=FMath::Max(.4f,float(ColdSteelInventory::Number(*Item,TEXT("swing_seconds"),.68)));
    ContactSeconds=FMath::Clamp(float(ColdSteelInventory::Number(*Item,TEXT("contact_seconds"),.24)),.1f,SwingSeconds-.1f);
    const float Scale=ColdSteelInventory::Number(*Item,TEXT("tool_scale"),.65);
    ToolMesh->SetRelativeScale3D(FVector(Scale));
    ToolMesh->SetRelativeRotation(FRotator(ColdSteelInventory::Number(*Item,TEXT("mount_pitch")),
        ColdSteelInventory::Number(*Item,TEXT("mount_yaw")),ColdSteelInventory::Number(*Item,TEXT("mount_roll"))));
    const FSoftObjectPath MeshPath(ColdSteelInventory::Text(*Item,TEXT("tool_mesh")));
    const FSoftObjectPath SoundPath(ColdSteelInventory::Text(*Item,TEXT("tool_sound")));
    const FSoftObjectPath DustPath(TEXT("/Game/EasyBuildingSystem/Effects/PS_Dust.PS_Dust"));
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad({MeshPath,SoundPath,DustPath},
        FStreamableDelegate::CreateWeakLambda(this,[this,Id,MeshPath,SoundPath,DustPath]()
        {
            if (EquippedId!=Id || !ToolMesh) return;
            ToolMesh->SetStaticMesh(Cast<UStaticMesh>(MeshPath.ResolveObject()));
            HitSound=Cast<USoundBase>(SoundPath.ResolveObject()); ImpactDust=Cast<UParticleSystem>(DustPath.ResolveObject());
            Feedback=ToolMesh->GetStaticMesh()?TEXT("左键采集 · F7 收起工具"):TEXT("工具模型加载失败，请重新装备");
            FeedbackSeconds=3.f;
        }));
}

bool UProductionToolComponent::CanUse() const
{
    auto* Pawn=Character.Get();
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return PC && !PC->bShowMouseCursor && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored() &&
        !Pawn->IsTraversing() && (!Health || !Health->IsDead()) && (!Building || !Building->IsBuilding());
}

void UProductionToolComponent::BeginUse()
{
    if (!IsEquipped() || !CanUse() || Elapsed>=0) return;
    if (!ToolMesh || !ToolMesh->GetStaticMesh()) { Feedback=TEXT("正在加载工具…"); FeedbackSeconds=1.f; return; }
    Elapsed=0; bContacted=false;
}

void UProductionToolComponent::CancelUse()
{
    Elapsed=-1; bContacted=false;
    if (Pivot) Pivot->SetRelativeRotation(FRotator::ZeroRotator);
}

void UProductionToolComponent::ShowFeedback(const FString& Message)
{
    Feedback=Message; FeedbackSeconds=4.f;
}

bool UProductionToolComponent::TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const
{
    if (!Camera || !Character.IsValid()) return false;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FVector Start=Camera->GetComponentLocation();
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Camera->GetForwardVector()*Reach,ECC_Visibility,Q))
    { Reason=TEXT("靠近树干、独立岩块或干燥地面（3.2 米内）"); return false; }
    for (TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if (It->ResolveProductionResource(Hit,Resource,Reason)) return true;
    if (Reason.IsEmpty()) Reason=TEXT("此物体不可采集，前往温带丘陵寻找资源");
    return false;
}

void UProductionToolComponent::ResolveContact()
{
    FProductionResource Target; FHitResult Hit; FString Reason;
    if (!TraceResource(Target,Hit,Reason)) { Feedback=Reason; FeedbackSeconds=2; return; }
    if (Kind!=Target.RequiredTool)
    {
        Feedback=Target.RequiredTool==TEXT("axe")?TEXT("砍树需要伐木斧（6）"):
            Target.RequiredTool==TEXT("pickaxe")?TEXT("开采岩块需要矿镐（7）"):TEXT("采集表土需要铁铲（8）");
        FeedbackSeconds=2; return;
    }
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bool Depleted=false;
    Target.Direction=Camera->GetForwardVector();
    if(Target.Layer==0)
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->PrepareFall(Target);
    if (!Profile->CommitHarvestStrike(Target,Depleted)) { Feedback=Profile->ResultMessage(); FeedbackSeconds=3; return; }
    Feedback=Profile->ResultMessage(); FeedbackSeconds=2;
    if (HitSound) UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.65f);
    if (ImpactDust&&(!Depleted||Target.Layer==2)) UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactDust,Hit.ImpactPoint,Hit.ImpactNormal.Rotation(),FVector(.25f),true,EPSCPoolMethod::AutoRelease);
    if (Depleted && Target.World.IsValid()) Target.World->CompleteProductionHarvest(Target,Hit,Camera->GetForwardVector());
}

void UProductionToolComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const bool Usable=IsEquipped() && CanUse();
    if (ToolMesh) ToolMesh->SetVisibility(Usable && ToolMesh->GetStaticMesh());
    if (!Usable) CancelUse();
    if (Elapsed>=0)
    {
        Elapsed+=Delta;
        // Godot donor: brief backswing, angled downward contact, slower recovery;
        // contact is resolved once using the current camera ray, not button-down aim.
        float Angle;
        if (Elapsed<ContactSeconds) Angle=FMath::Lerp(-.45f,.95f,FMath::Square(Elapsed/ContactSeconds));
        else { const float T=FMath::Clamp((Elapsed-ContactSeconds)/(SwingSeconds-ContactSeconds),0.f,1.f); Angle=FMath::Lerp(.95f,0.f,T*T*(3-2*T)); }
        Pivot->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Angle),0,FMath::RadiansToDegrees(Angle*.26f)));
        if (!bContacted && Elapsed>=ContactSeconds) { bContacted=true; ResolveContact(); }
        if (Elapsed>=SwingSeconds) CancelUse();
    }
    FeedbackSeconds=FMath::Max(0.f,FeedbackSeconds-Delta);
    HintCountdown-=Delta;
    if (HintCountdown<=0) { HintCountdown=.15f; UpdateHint(); }
}

void UProductionToolComponent::UpdateHint()
{
    auto* PC=Character.IsValid()?Cast<APlayerController>(Character->GetController()):nullptr;
    if (!PC) return;
    if (!Prompt)
    {
        Prompt=CreateWidget<UColdSteelPickupPrompt>(PC,UColdSteelPickupPrompt::StaticClass());
        Prompt->AddToViewport(25); Prompt->SetAlignmentInViewport(FVector2D(.5,.5));
    }
    const bool Show=(IsEquipped() || FeedbackSeconds>0) && CanUse();
    Prompt->SetVisibility(Show?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if (!Show) return;
    int32 X=0,Y=0; PC->GetViewportSize(X,Y);
    Prompt->SetPositionInViewport(FVector2D(X*.5f,Y*.68f),true);
    FString Detail;
    if (FeedbackSeconds>0) Detail=Feedback;
    else
    {
        FProductionResource Target; FHitResult Hit;
        if (TraceResource(Target,Hit,Detail))
        {
            auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            Detail=FString::Printf(TEXT("%s · %d / %d"),*Target.Name,Profile->HarvestProgress(Target.Id),FProductionResource::RequiredHits);
        }
    }
    Prompt->SetCaption((IsEquipped()?ToolName+TEXT(" · 左键使用 · 6 斧 / 7 镐 / 8 铲 · F7 收起\n"):FString())+Detail);
}

void UProductionToolComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (LoadHandle) { LoadHandle->CancelHandle(); LoadHandle.Reset(); }
    if (Prompt) { Prompt->RemoveFromParent(); Prompt=nullptr; }
    Super::EndPlay(Reason);
}
