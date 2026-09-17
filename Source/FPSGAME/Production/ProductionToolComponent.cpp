#include "ProductionToolComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "ProductionHarvestSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "HAL/IConsoleManager.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"

namespace
{
    // The shovel digs where the crosshair points; the heightfield keeps its 20 cm
    // layer rule, so one swing is one whole layer instead of a melee poke.
    // The shovel is an aiming tool, not a melee reach: without this it could only hit
    // ground inside 3.2 m, i.e. straight down at the player's feet.
    static TAutoConsoleVariable<float> ToolDigReach(
        TEXT("fps.Tool.DigReach"), 1000.f,
        TEXT("Shovel aim trace length in cm; the shovel digs where the crosshair points."));
    FSoftObjectPath HarvestMotionPath(const FString& Prefix,const TCHAR* Clip)
    {
        const FString Package=Prefix+Clip;
        return FSoftObjectPath(Package+TEXT(".")+FPackageName::GetLongPackageAssetName(Package));
    }
}

UProductionToolComponent::UProductionToolComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UProductionToolComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    auto* World=GetWorld();
    auto* GameInstance=World?World->GetGameInstance():nullptr;
    // Preview worlds also report standalone. They have no player inventory and
    // can receive BeginPlay while a different world's pawn is being spawned.
    if (!Pawn || !GameInstance || (World->WorldType!=EWorldType::Game && World->WorldType!=EWorldType::PIE) || Pawn->GetNetMode()!=NM_Standalone)
    { SetComponentTickEnabled(false); return; }
    AddTickPrerequisiteActor(Pawn);
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Pivot=NewObject<USceneComponent>(Pawn,TEXT("ProductionToolPivot"));
    Pawn->AddInstanceComponent(Pivot); Pivot->SetupAttachment(Camera); Pivot->RegisterComponent();
    Pivot->SetRelativeLocation(FVector(55,24,-35));
    ToolMesh=NewObject<UStaticMeshComponent>(Pawn,TEXT("ProductionToolMesh"));
    Pawn->AddInstanceComponent(ToolMesh); ToolMesh->SetupAttachment(Pivot);
    ToolMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); ToolMesh->SetCanEverAffectNavigation(false);
    ToolMesh->SetCastShadow(false); ToolMesh->SetOnlyOwnerSee(true); ToolMesh->SetVisibility(false); ToolMesh->RegisterComponent();
    Viewmodel=NewObject<UFPSCastingMeshComponent>(Pawn,TEXT("ProductionToolHands"));
    Pawn->AddInstanceComponent(Viewmodel); Viewmodel->SetupAttachment(Camera);
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision); Viewmodel->SetCanEverAffectNavigation(false);
    Viewmodel->SetCastShadow(false); Viewmodel->SetOnlyOwnerSee(true); Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent(); Viewmodel->SetVisibility(false);
    // Sample once from the harvest clock; hidden tools do not evaluate animation.
    Viewmodel->SetComponentTickEnabled(false);
    if (auto* Profile=GameInstance->GetSubsystem<UColdSteelStatusModel>()) Profile->GrantProductionTools();
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
    ToolMesh->SetVisibility(false); ToolMesh->SetStaticMesh(nullptr); HitSound=nullptr; SwingSound=nullptr;
    Viewmodel->SetVisibility(false); Viewmodel->SetSkeletalMesh(nullptr);
    CurrentMotion=nullptr; Motions.Reset(); bUsesArms=false; VisualTime=0; SprintBlend=0;
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
    const FSoftObjectPath ViewmodelPath(ColdSteelInventory::Text(*Item,TEXT("tool_viewmodel")));
    const FSoftObjectPath SwingPath(ColdSteelInventory::Text(*Item,TEXT("tool_swing_sound")));
    const FString MotionPrefix=ColdSteelInventory::Text(*Item,TEXT("tool_animation_prefix"));
    bUsesArms=!ViewmodelPath.IsNull();
    TArray<FSoftObjectPath> Paths={SoundPath,DustPath};
    if(bUsesArms)
    {
        Paths.Add(ViewmodelPath);
        if(!SwingPath.IsNull())Paths.Add(SwingPath);
        for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
            Paths.Add(HarvestMotionPath(MotionPrefix,Clip));
    }
    else Paths.Add(MeshPath);
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this,Id,MeshPath,SoundPath,DustPath,ViewmodelPath,SwingPath,MotionPrefix]()
        {
            if (EquippedId!=Id || !ToolMesh) return;
            if(bUsesArms)
            {
                Viewmodel->SetSkeletalMesh(Cast<USkeletalMesh>(ViewmodelPath.ResolveObject()));
                for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
                    Motions.Add(FName(Clip),Cast<UAnimSequence>(HarvestMotionPath(MotionPrefix,Clip).ResolveObject()));
                SwingSound=Cast<USoundBase>(SwingPath.ResolveObject());
                if(HasReadyPresentation()){EquipElapsed=0; SampleMotion(TEXT("Equip"),0);}
            }
            else ToolMesh->SetStaticMesh(Cast<UStaticMesh>(MeshPath.ResolveObject()));
            HitSound=Cast<USoundBase>(SoundPath.ResolveObject()); ImpactDust=Cast<UParticleSystem>(DustPath.ResolveObject());
            Feedback=HasReadyPresentation()?TEXT("左键采集 · F7 收起工具"):TEXT("工具或手部动作加载失败，请重新装备");
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
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction())return;
    if (!IsEquipped() || !CanUse() || Elapsed>=0) return;
    if (!HasReadyPresentation()) { Feedback=TEXT("正在加载工具…"); FeedbackSeconds=1.f; return; }
    if(EquipElapsed>=0)return;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(!Profile->SpendStamina(Profile->StaminaSettings().HarvestCost)){Feedback=TEXT("体力不足，稍作休息再采集");FeedbackSeconds=1.5f;return;}
    Elapsed=0; bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
}

void UProductionToolComponent::CancelUse()
{
    Elapsed=-1; EquipElapsed=-1; bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
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
    const float Length=Kind==TEXT("shovel")?ToolDigReach.GetValueOnGameThread():Reach;
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Camera->GetForwardVector()*Length,ECC_Visibility,Q))
    { Reason=TEXT("靠近树干、独立岩块或干燥地面（3.2 米内）"); return false; }
    for (TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if (It->ResolveProductionResource(Hit,Resource,Reason)) return true;
    if (Reason.IsEmpty()) Reason=TEXT("此物体不可采集，前往温带丘陵寻找资源");
    return false;
}

bool UProductionToolComponent::ResolveContact()
{
    FProductionResource Target; FHitResult Hit; FString Reason;
    if (!TraceResource(Target,Hit,Reason)) { Feedback=Reason; FeedbackSeconds=2; return false; }
    if (Kind!=Target.RequiredTool)
    {
        Feedback=Target.RequiredTool==TEXT("axe")?TEXT("砍树需要伐木斧（6）"):
            Target.RequiredTool==TEXT("pickaxe")?TEXT("开采岩块需要矿镐（7）"):TEXT("采集表土需要铁铲（8）");
        FeedbackSeconds=2; return false;
    }
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bool Depleted=false;
    Target.Direction=Camera->GetForwardVector();
    if(Target.Layer==0)
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->PrepareFall(Target);
    if (!Profile->CommitHarvestStrike(Target,Depleted)) { Feedback=Profile->ResultMessage(); FeedbackSeconds=3; return false; }
    Feedback=Profile->ResultMessage(); FeedbackSeconds=2;
    if (HitSound) UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.65f);
    if (ImpactDust&&(!Depleted||Target.Layer==2)) UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactDust,Hit.ImpactPoint,Hit.ImpactNormal.Rotation(),FVector(.25f),true,EPSCPoolMethod::AutoRelease);
    if (Depleted && Target.World.IsValid()) Target.World->CompleteProductionHarvest(Target,Hit,Camera->GetForwardVector());
    if (Depleted && Target.Layer==2)
    {
        // The world just removed one 20 cm layer; say so instead of only "collected".
        Feedback=TEXT("表土挖低 20 cm（继续左键下挖，右键回填）");
        FeedbackSeconds=3.f;
    }
    return true;
}

void UProductionToolComponent::BeginRefill()
{
    if(!IsEquipped()||IsBusy())return;
    if(Kind!=TEXT("shovel")){ShowFeedback(TEXT("回填地面需要铁铲（8）"));return;}
    if(!Camera||!Character.IsValid())return;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FVector Start=Camera->GetComponentLocation();
    FHitResult Hit;
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Camera->GetForwardVector()*ToolDigReach.GetValueOnGameThread(),ECC_Visibility,Q))
    {ShowFeedback(TEXT("瞄准地面再回填"));return;}
    FString Message;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->ApplySoilRefill(Hit.ImpactPoint,Message))break;
    if(Message.IsEmpty())Message=TEXT("这里不是可回填的地形");
    ShowFeedback(Message);
}

void UProductionToolComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const bool Usable=IsEquipped() && CanUse();
    if (ToolMesh) ToolMesh->SetVisibility(Usable && !bUsesArms && ToolMesh->GetStaticMesh());
    if (Viewmodel) Viewmodel->SetVisibility(Usable && bUsesArms && HasReadyPresentation());
    if (!Usable) CancelUse();
    if (Elapsed>=0)
    {
        Elapsed+=Delta;
        if(bUsesArms && !bSwingSoundPlayed && Elapsed>=ContactSeconds*.65f)
        {
            bSwingSoundPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.38f,Kind==TEXT("axe")?.86f:.76f);
        }
        // The shovel keeps its original procedural arc. Skeletal tools use the same
        // one-contact clock and resolve against the camera ray at the contact time.
        if(!bUsesArms)
        {
            float Angle;
            if (Elapsed<ContactSeconds) Angle=FMath::Lerp(-.45f,.95f,FMath::Square(Elapsed/ContactSeconds));
            else { const float T=FMath::Clamp((Elapsed-ContactSeconds)/(SwingSeconds-ContactSeconds),0.f,1.f); Angle=FMath::Lerp(.95f,0.f,T*T*(3-2*T)); }
            Pivot->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Angle),0,FMath::RadiansToDegrees(Angle*.26f)));
        }
        if (!bContacted && Elapsed>=ContactSeconds) { bContacted=true; bHitConfirmed=ResolveContact(); }
        if (Elapsed>=SwingSeconds) CancelUse();
    }
    if(Usable && bUsesArms && HasReadyPresentation())UpdateHandPresentation(Delta);
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
            Detail=FString::Printf(TEXT("%s · %d / %d"),*Target.Name,Profile->HarvestProgress(Target.Id),Target.HitsNeeded());
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
