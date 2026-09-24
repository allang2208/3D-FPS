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
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerStart.h"

namespace
{
    /** 固定生成探针高度（cm）：从候选点在竖直方向上找地面。 */
    constexpr float ChestSpawnProbeUp=300.f;
    constexpr float ChestSpawnProbeDown=2000.f;

    /** 宝箱资产/生成配置：Content/ColdSteelData/warehouse_assets.json（缺失时保持代码默认值）。 */
    bool LoadChestConfig(TSharedPtr<FJsonObject>& Out)
    {
        FString JSON;
        return FFileHelper::LoadFileToString(JSON,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/warehouse_assets.json")))
            &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(JSON),Out)&&Out.IsValid();
    }

    /** 读取 {x,y,z} 对象；字段缺失或非数字时不改动 Out。 */
    bool TryReadXYZ(const TSharedPtr<FJsonObject>& Owner,const TCHAR* Field,FVector& Out)
    {
        if(!Owner.IsValid())return false;
        const TSharedPtr<FJsonObject>* Vector=nullptr;
        if(!Owner->TryGetObjectField(Field,Vector)||!Vector||!Vector->IsValid())return false;
        double X=0,Y=0,Z=0;
        // 不用 ||：短路会跳过后续字段的读取。
        if(!(*Vector)->TryGetNumberField(TEXT("x"),X)&!(*Vector)->TryGetNumberField(TEXT("y"),Y)&!(*Vector)->TryGetNumberField(TEXT("z"),Z))return false;
        Out=FVector(X,Y,Z);
        return true;
    }
}

bool AColdSteelWarehouseChest::ResolveFixedSpawn(UWorld* World,const APawn* FallbackPawn,FVector& OutLocation,FRotator& OutRotation,FString& OutSource)
{
    if(!World)return false;
    // 1) 固定锚点：地图 PlayerStart。GameMode 也用 PlayerStart 出生，因此锚点只跟关卡走。
    FVector Pivot=FVector::ZeroVector;
    float AnchorYaw=0.f;
    bool bHasAnchor=false;
    {
        FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelChestAnchor),false);
        if(IsValid(FallbackPawn))Query.AddIgnoredActor(FallbackPawn);
        for(TActorIterator<APlayerStart> It(World);It;++It)
        {
            Query.AddIgnoredActor(*It);
            const FVector Probe=It->GetActorLocation();
            FHitResult Floor;
            if(!World->LineTraceSingleByChannel(Floor,Probe+FVector(0,0,ChestSpawnProbeUp),Probe-FVector(0,0,ChestSpawnProbeDown),ECC_Visibility,Query))continue;
            if(Floor.bStartPenetrating||Floor.ImpactNormal.Z<.8f)continue;
            Pivot=Floor.ImpactPoint;
            AnchorYaw=It->GetActorRotation().Yaw;
            bHasAnchor=true;
            break;
        }
    }
    if(!bHasAnchor)
    {
        // 关卡没有可用 PlayerStart 时才保留旧口径（玩家当前位置），并在日志里说明来源。
        if(!IsValid(FallbackPawn))return false;
        Pivot=FallbackPawn->GetActorLocation();
        AnchorYaw=FallbackPawn->GetActorRotation().Yaw;
    }

    // 2) 配置覆盖（可选）：spawn.location = 世界坐标（Z 会重新贴地，用于钉死具体位置）；
    //    spawn.offset = 锚点局部偏移，cm，X 前/Y 右/Z 上（缺省 190cm 正前方，即原自动生成距离）；
    //    spawn.yaw = 绝对朝向，spawn.yawOffset = 相对锚点朝向的偏航；spawn.angles = 被占用时的候选偏航顺序。
    FVector Offset(190.f,0,0);
    float BaseYaw=AnchorYaw;
    bool bPinned=false;
    TArray<float> Angles{0.f,60.f,-60.f,120.f,-120.f,180.f};
    {
        TSharedPtr<FJsonObject> Config;
        const TSharedPtr<FJsonObject>* Spawn=nullptr;
        if(LoadChestConfig(Config)&&Config->TryGetObjectField(TEXT("spawn"),Spawn)&&Spawn&&Spawn->IsValid())
        {
            FVector Pinned;
            if(TryReadXYZ(*Spawn,TEXT("location"),Pinned)){Pivot=Pinned;bPinned=true;}
            TryReadXYZ(*Spawn,TEXT("offset"),Offset);
            double Number=0;
            if((*Spawn)->TryGetNumberField(TEXT("yaw"),Number))BaseYaw=static_cast<float>(Number);
            else if((*Spawn)->TryGetNumberField(TEXT("yawOffset"),Number))BaseYaw=AnchorYaw+static_cast<float>(Number);
            const TArray<TSharedPtr<FJsonValue>>* List=nullptr;
            if((*Spawn)->TryGetArrayField(TEXT("angles"),List)&&List)
            {
                TArray<float> Parsed;
                for(const TSharedPtr<FJsonValue>& Value:*List){double A=0;if(Value.IsValid()&&Value->TryGetNumber(A))Parsed.Add(static_cast<float>(A));}
                if(Parsed.Num()>0)Angles=MoveTemp(Parsed);
            }
        }
    }

    // 3) 候选落点：固定锚点 + 局部偏移，按候选偏航逐个校验地面与阻挡。
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelChestSpot),false);
    if(IsValid(FallbackPawn))Query.AddIgnoredActor(FallbackPawn);
    for(const float Angle:Angles)
    {
        const float Yaw=BaseYaw+Angle;
        const FVector Probe=Pivot+Offset.RotateAngleAxis(Yaw,FVector::UpVector);
        FHitResult Floor;
        if(!World->LineTraceSingleByChannel(Floor,Probe+FVector(0,0,ChestSpawnProbeUp),Probe-FVector(0,0,ChestSpawnProbeDown),ECC_Visibility,Query))continue;
        if(Floor.bStartPenetrating||Floor.ImpactNormal.Z<.8f)continue;
        const FRotator Facing(0,Yaw,0);
        const FVector Spot=Floor.ImpactPoint+FVector(0,0,2);
        if(World->OverlapBlockingTestByChannel(Spot+FVector(0,0,68),Facing.Quaternion(),ECC_Pawn,FCollisionShape::MakeBox(FVector(58,76,65)),Query))continue;
        OutLocation=Spot;
        OutRotation=Facing;
        OutSource=FString::Printf(TEXT("%s%s"),bHasAnchor?TEXT("playerStart"):TEXT("player"),bPinned?TEXT("+jsonLocation"):TEXT("+offset"));
        return true;
    }
    UE_LOG(LogTemp,Warning,TEXT("WarehouseChest: no valid fixed spawn near %s (anchor=%s)"),*Pivot.ToString(),bHasAnchor?TEXT("playerStart"):TEXT("player"));
    return false;
}

AColdSteelWarehouseChest::AColdSteelWarehouseChest()
{
    PrimaryActorTick.bCanEverTick=true;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Root);
    Collision=CreateDefaultSubobject<UBoxComponent>(TEXT("ChestCollision"));Collision->SetupAttachment(Root);Collision->SetBoxExtent(FVector(55,73,37));Collision->SetRelativeLocation(FVector(0,0,37));Collision->SetCollisionProfileName(TEXT("BlockAll"));
    Mesh=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("OriginalChest"));Mesh->SetupAttachment(Root);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    // 2026-09-24：模型上方的世界空间名牌组件已撤除，E 提示统一进准星小浮窗。
}
void AColdSteelWarehouseChest::BeginPlay()
{
    Super::BeginPlay();
    if(ActorHasTag(TEXT("DungeonStorageCabinet")))return;
    TSharedPtr<FJsonObject> Root;LoadChestConfig(Root);
    if(Root.IsValid()){
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
    if(ActorHasTag(TEXT("DungeonStorageCabinet"))){bDesiredOpen=Open;bIsOpen=Open;return;}
    bDesiredOpen=Open;if(bAnimating||bIsOpen==Open)return;
    auto* Clip=Open?OpenClip.Get():CloseClip.Get();if(!Clip)return;
    bAnimating=true;bPlayingOpen=Open;Elapsed=0;Mesh->SetPlayRate(1);Mesh->PlayAnimation(Clip,false);
}
void AColdSteelWarehouseChest::Tick(float Delta)
{
    Super::Tick(Delta); // 名牌显隐旧逻辑已废：交互提示由准星小浮窗统一呈现
    if(bAnimating){Elapsed+=Delta;auto* Clip=bPlayingOpen?OpenClip.Get():CloseClip.Get();if(Clip&&Elapsed>=Clip->GetPlayLength()){
        Mesh->SetPosition(Clip->GetPlayLength(),false);Mesh->SetPlayRate(0);bIsOpen=bPlayingOpen;bAnimating=false;SetOpen(bDesiredOpen);
    }}
}
