#include "BowWeaponComponent.h"
#include "BowArrow.h"
#include "BowArmsMeshComponent.h"
#include "BowPartComponent.h"
#include "BowStats.h"
#include "../WeaponStatEvaluation.h"
#include "../GunsmithSystem.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../UI/ColdSteelPickup.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Sound/SoundBase.h"

namespace
{
    const TCHAR* const NockRoles[] = {TEXT("Nock"), TEXT("QuickNock"), TEXT("ChainNock")};
    const TCHAR* const NockKeys[] = {TEXT("bow_nock_animation"), TEXT("bow_draw_entry_animation"), TEXT("bow_chain_entry_animation")};
    const TCHAR* const GaitRoles[] = {TEXT("Walk"), TEXT("Run"), TEXT("LoadedWalk"), TEXT("LoadedRun"), TEXT("LoadedIdle")};
    // Exact critically damped response for a target held over this frame.
    // Unlike a fixed crossfade this retains velocity when movement reverses.
    template<typename T>
    void DampCarry(T& Value, T& Velocity, const T& Target, float Frequency, float Delta)
    {
        const T Error = Value - Target;
        const T Change = Velocity + Error * Frequency;
        const float Decay = FMath::Exp(-Frequency * Delta);
        Value = Target + (Error + Change * Delta) * Decay;
        Velocity = (Velocity - Change * (Frequency * Delta)) * Decay;
    }
    /** 与采集工具同一拼接口径：`<前缀><角色名>` 的包内资产名。 */
    FSoftObjectPath BowAssetPath(const FString& Prefix, const TCHAR* Clip)
    {
        const FString Package = Prefix + Clip;
        return FSoftObjectPath(Package + TEXT(".") + FPackageName::GetLongPackageAssetName(Package));
    }

    /**
     * 三分量向量在 JSON 里写成 "x,y,z" 字符串：物品 Data 是扁平 JSON 文本，
     * 这里不引入第二套解析口径，读不到就保留代码里的实测默认值。
     * 5.8 的 `LexFromString` 只覆盖标量、`FParse::ParseVector` 已移除，故 cvar 也走这个解析器。
     */
    bool ReadVector3Text(const FString& Text, FVector& Out)
    {
        if (Text.IsEmpty()) return false;
        TArray<FString> Parts;
        Text.ParseIntoArray(Parts, TEXT(","), false);
        if (Parts.Num() < 3) return false;
        Out = FVector(FCString::Atof(*Parts[0]), FCString::Atof(*Parts[1]), FCString::Atof(*Parts[2]));
        return true;
    }

    bool ReadVector3(const FColdSteelItem* Item, const TCHAR* Key, FVector& Out)
    {
        return ReadVector3Text(ColdSteelInventory::Text(*Item, Key), Out);
    }

    // 弓体是移除旧烘焙弦后的静态网格；锚点在弓局部空间，长度沿 Z、出膛沿 +X。
    // 下面两个 cvar 是**叠加在数据表之上的实机对点偏移**，默认 0，不改存档也不改 JSON。
    // `TAutoConsoleVariable` 只支持标量／字符串，向量按 "x,y,z" 文本解析（与数据表同一口径）。
    TAutoConsoleVariable<FString> CVarBowLocation(TEXT("fps.Bow.LocationOffset"), TEXT("0,0,0"),
        TEXT("Additive camera-space offset (cm) on the bow viewmodel, \"x,y,z\"."));
    TAutoConsoleVariable<FString> CVarBowRotation(TEXT("fps.Bow.RotationOffset"), TEXT("0,0,0"),
        TEXT("Additive camera-space rotation (degrees, pitch,yaw,roll) on the bow viewmodel."));
    TAutoConsoleVariable<float> CVarBowSway(TEXT("fps.Bow.Sway"), 1.f,
        TEXT("Scale on the hold sway and the draw camera motion."));
}

const TCHAR* UBowWeaponComponent::ClipIdle = TEXT("Idle");
const TCHAR* UBowWeaponComponent::ClipDraw = TEXT("Draw");
const TCHAR* UBowWeaponComponent::ClipHold = TEXT("Hold");
const TCHAR* UBowWeaponComponent::ClipRelease = TEXT("Release");
const TCHAR* UBowWeaponComponent::ClipNock = TEXT("Nock");

// 三个默认部件槽。数据表用 `bow_part_slots` 覆盖这个清单（改造系统加瞄具／稳定器时只加键）。
const TCHAR* UBowWeaponComponent::SlotRiser = TEXT("riser");
const TCHAR* UBowWeaponComponent::SlotString = TEXT("string");
const TCHAR* UBowWeaponComponent::SlotArrow = TEXT("arrow");

namespace
{
    /** 逗号分隔的槽名清单；为空时回到默认三件（弓体／弓弦／弦上箭）。 */
    TArray<FName> BowSlotNames(const FString& Text)
    {
        TArray<FName> Slots;
        TArray<FString> Names;
        Text.ParseIntoArray(Names, TEXT(","), false);
        for (FString& Raw : Names)
        {
            Raw.TrimStartAndEndInline();
            if (!Raw.IsEmpty()) Slots.Add(FName(*Raw));
        }
        if (Slots.IsEmpty()) Slots = { FName(TEXT("riser")), FName(TEXT("string")), FName(TEXT("arrow")) };
        return Slots;
    }
}

UBowWeaponComponent::UBowWeaponComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UBowWeaponComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn = Cast<AFPSGAMECharacter>(GetOwner());
    auto* World = GetWorld();
    auto* GameInstance = World ? World->GetGameInstance() : nullptr;
    // 预览世界也会报 standalone，但没有玩家库存，会在别的 pawn 生成时收到 BeginPlay。
    if (!Pawn || !GameInstance || (World->WorldType != EWorldType::Game && World->WorldType != EWorldType::PIE)
        || Pawn->GetNetMode() != NM_Standalone)
    {
        SetComponentTickEnabled(false);
        return;
    }
    Character = Pawn;
    AddTickPrerequisiteActor(Pawn);
    Camera = Pawn->FindComponentByClass<UCameraComponent>();
    Pivot = NewObject<USceneComponent>(Pawn, TEXT("BowPivot"));
    Pawn->AddInstanceComponent(Pivot);
    Pivot->SetupAttachment(Camera);
    Pivot->RegisterComponent();

    // 占位几何不在这里管：部件与箭各自兜底（引擎圆柱／圆锥）。
    // 弓体、弓弦、弦上箭拆成三个独立部件：各自一个挂点 + 自己的网格／细杆。
    // 改造系统之后只按槽名写数据键，不必再碰状态机与弹道。
    auto MakePart = [&](const TCHAR* Slot, USceneComponent* Parent, int32 Rods)
    {
        const FName Key(Slot);
        auto* Component = NewObject<UBowPartComponent>(Pawn,
            *FString::Printf(TEXT("BowPart_%s"), Slot));
        Component->InitializeAsPart(Pawn, Key, Parent);
        Parts.Add(Key, Component);
        TArray<int32>& Handles = PartRods.FindOrAdd(Key);
        for (int32 Index = Handles.Num(); Index < Rods; ++Index)
            Handles.Add(Component->AddRod(*FString::Printf(TEXT("%sRod%d"), Slot, Index)));
        return Component;
    };
    auto* Riser = MakePart(SlotRiser, Pivot, 0);
    MakePart(SlotString, Riser, 2);
    MakePart(SlotArrow, Riser, 1);

    Viewmodel = NewObject<UBowArmsMeshComponent>(Pawn, TEXT("BowHands"));
    Pawn->AddInstanceComponent(Viewmodel);
    Viewmodel->SetupAttachment(Pivot);
    Viewmodel->SetRelativeRotation(ArmsRotation);
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Viewmodel->SetCanEverAffectNavigation(false);
    Viewmodel->SetCastShadow(false);
    Viewmodel->SetOnlyOwnerSee(true);
    Viewmodel->bReceivesDecals = false;
    Viewmodel->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    // 没有 AnimBP：手臂序列由本组件按动作时钟单节点播放（与采集工具一致）。
    Viewmodel->SetComponentTickEnabled(false);
    Viewmodel->RegisterComponent();
    Viewmodel->SetVisibility(false);
    // 与采集工具同一发放口径：目录里配了弓就补进背包（幂等，不覆盖玩家已有摆放）。
    if (auto* Profile = GameInstance->GetSubsystem<UColdSteelStatusModel>()) Profile->GrantBow();
    RefreshEquipment(GameInstance->GetSubsystem<UColdSteelStatusModel>());
}

void UBowWeaponComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    StopDrawAudio();
    StopHandlingAudio();
    if (LoadHandle)
    {
        LoadHandle->CancelHandle();
        LoadHandle.Reset();
    }
    if (Prompt)
    {
        Prompt->RemoveFromParent();
        Prompt = nullptr;
    }
    Super::EndPlay(Reason);
}

void UBowWeaponComponent::RefreshEquipment(UColdSteelStatusModel* Profile)
{
    if (!Part(SlotRiser) || !Pivot) return;
    const auto* Item = Profile ? Profile->ActiveBow() : nullptr;
    const FString NewId = Item ? Item->InstanceId : FString();
    const FString NewArrow = Item ? Profile->AmmoDefinitionFor(*Item) : FString();
    const bool bArrowTypeChanged=ArrowId!=NewArrow;
    // LoadedAmmoType lives outside Item.Data. A type-only change must invalidate
    // the nocked reservation without unloading the same hands and bow assets.
    if (NewId == InstanceId && bArrowTypeChanged)
    {
        CancelAction();
        bArrowNocked = false;
    }
    ArrowId = NewArrow;
    const uint32 DataHash = Item ? GetTypeHash(Item->Data) : 0u;
    if (NewId == InstanceId && DataHash == EquippedDataHash && !bArrowTypeChanged) return;
    FColdSteelItem Resolved;
    if(Item)
    {
        auto* G=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        Resolved=G?G->ResolveBowVisual(*Item):*Item;Item=&Resolved;
    }
    // 同一实例、资源集合没变（只改数值或部件参数）：保留已加载视模，只重算，手上不闪帧。
    // 改造系统换的是部件网格时签名会变，才走下面的重新加载。
    const FString NewSignature = Item ? PresentationSignature(Item) : FString();
    // All compatible arrow meshes were preloaded with this bow. A wheel change
    // only replaces the arrow; hands, aim transition and carry pose stay loaded.
    if(NewId==InstanceId&&Item&&bArrowTypeChanged&&DataHash==EquippedDataHash&&bPresentationReady)
    {
        const FSoftObjectPath ArrowPath(ColdSteelInventory::Text(*Item,TEXT("bow_part_arrow_mesh")));
        if(auto* Mesh=Cast<UStaticMesh>(ArrowPath.ResolveObject()))if(auto* ArrowPart=Part(SlotArrow))
        {
            ArrowPart->SetMesh(Mesh);
            PendingPartMeshes.Add(SlotArrow,ArrowPath);
            EquippedSignature=NewSignature;
            return;
        }
    }
    if (NewId == InstanceId && Item && NewSignature == EquippedSignature)
    {
        EquippedDataHash = DataHash;
        ApplyNumbers(Item);
        ApplyParts(Item);
        return;
    }
    CancelAction();
    InstanceId = NewId;
    EquippedDataHash = DataHash;
    EquippedSignature = NewSignature;
    EquippedDefinition.Reset();
    DisplayName.Reset();
    Feedback.Reset();
    for (auto& Pair : Parts)
    {
        if (!Pair.Value) continue;
        Pair.Value->SetMesh(nullptr);
        Pair.Value->SetPartVisible(false);
    }
    Viewmodel->SetSkeletalMesh(nullptr);
    Viewmodel->SetVisibility(false);
    Animations.Reset();
    ArrowHeadMesh = nullptr;
    DrawSound = ReleaseSound = NockSound = TakeArrowSound = nullptr;
    CurrentClip = NAME_None;
    bUsesArms = false;
    bPresentationReady = false;
    bHasGripMarker = bHasNockMarker = false;
    bHasRightHandBone = false;
    bArrowNocked = false;
    VisualTime = 0.f;
    GaitPhase = GaitWeight = GaitWeightVelocity = SprintBlend = SprintBlendVelocity = 0.f;
    TravelSpeed = TravelSpeedVelocity = TurnFollow = TurnFollowVelocity = 0.f;
    TravelDirection = TravelDirectionVelocity = CarryOffset = FVector::ZeroVector;
    CarryRotation = FRotator::ZeroRotator;
    bHaveViewYaw = false;
    Viewmodel->SetLocomotion(nullptr, nullptr, 0.f, 0.f, 0.f, false, BraceNockCM);
    AimProgress = CrouchProgress = 0.f;
    AimVelocity = AimSegmentStart = AimSegmentVelocity = 0.f;
    AimSegmentElapsed = AimSegmentDuration = 0.f;
    bAimBlendTarget = bAimBraking = false;
    MoveSpread = AirSpread = ShotBloom = 0.f;
    HipAimProgress = 0.f;
    Pivot->SetRelativeTransform(FTransform::Identity);
    if (LoadHandle)
    {
        LoadHandle->CancelHandle();
        LoadHandle.Reset();
    }
    if (!Item)
    {
        Stage = EBowStage::Stowed;
        Elapsed = -1.f;
        for (auto& Pair : Parts) if (Pair.Value) Pair.Value->SetPartVisible(false);
        return;
    }
    EquippedDefinition = Item->Definition;
    DisplayName = ColdSteelInventory::Text(*Item, TEXT("name"));
    ApplyNumbers(Item);

    // 部件表先定下来（槽名、细杆条数、半径），再收集各槽资源做一次异步加载。
    ApplyParts(Item);
    const FSoftObjectPath ArmsPath(ColdSteelInventory::Text(*Item, TEXT("bow_viewmodel")));
    const FSoftObjectPath HeadPath(ColdSteelInventory::Text(*Item, TEXT("arrow_head_mesh")));
    const FString Prefix = ColdSteelInventory::Text(*Item, TEXT("bow_animation_prefix"));
    const FString GaitPrefix = ColdSteelInventory::Text(*Item, TEXT("bow_locomotion_prefix"));
    bUsesArms = !ArmsPath.IsNull();
    TArray<FSoftObjectPath> Paths;
    for (const auto& Pair : PendingPartMeshes) if (!Pair.Value.IsNull()) Paths.Add(Pair.Value);
    for (const auto& Pair : PendingPartMaterials) if (!Pair.Value.IsNull()) Paths.Add(Pair.Value);
    // Retained by LoadHandle until unequip; switching ammo requires no blocking load.
    if(Profile)for(const auto& Ammo:Profile->AmmoCatalog())
        if(Ammo.Enabled&&Ammo.Group==TEXT("arrow")&&!Ammo.ProjectileMesh.IsEmpty())Paths.AddUnique(FSoftObjectPath(Ammo.ProjectileMesh));
    if (bUsesArms)
    {
        Paths.Add(ArmsPath);
        for (const TCHAR* Clip : { ClipIdle, ClipDraw, ClipHold, ClipRelease, ClipNock, TEXT("Ready"), TEXT("Equip"), TEXT("Run") })
            Paths.Add(BowAssetPath(Prefix, Clip));
        for (const TCHAR* Key : NockKeys)
        {
            const FSoftObjectPath Path(ColdSteelInventory::Text(*Item, Key));
            if (!Path.IsNull()) Paths.AddUnique(Path);
        }
        if (!GaitPrefix.IsEmpty())
            for (const TCHAR* Role : GaitRoles) Paths.AddUnique(BowAssetPath(GaitPrefix, Role));
    }
    if (!HeadPath.IsNull()) Paths.Add(HeadPath);
    for (const TCHAR* Key : { TEXT("bow_draw_sound"), TEXT("bow_release_sound"), TEXT("bow_nock_sound"), TEXT("bow_take_arrow_sound") })
    {
        const FSoftObjectPath Sound(ColdSteelInventory::Text(*Item, Key));
        if (!Sound.IsNull()) Paths.Add(Sound);
    }
    LoadHandle = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this, [this, Prefix, GaitPrefix, ArmsPath, HeadPath, NewId, NewSignature, Resolved]()
        {
            auto* LiveProfile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            const auto* LiveItem = LiveProfile ? LiveProfile->ActiveBow() : nullptr;
            if (!LiveItem || LiveItem->InstanceId != NewId || InstanceId != NewId || EquippedSignature != NewSignature) return;
            const auto* Item=&Resolved;
            // 每个部件自己认领网格与材质覆盖：换弓臂／换弦／换箭台都只是改数据键。
            for (const auto& Pair : Parts)
            {
                UBowPartComponent* Component = Pair.Value;
                if (!Component) continue;
                UObject* MeshAsset = PendingPartMeshes.FindRef(Pair.Key).ResolveObject();
                if (auto* Skeletal = Cast<USkeletalMesh>(MeshAsset)) Component->SetSkeletalMesh(Skeletal);
                else Component->SetMesh(Cast<UStaticMesh>(MeshAsset));
                if (auto* Material = Cast<UMaterialInterface>(PendingPartMaterials.FindRef(Pair.Key).ResolveObject()))
                {
                    // 本包的弦是烘进网格的直线：填上槽名 + 隐形材质后，用组件级材质覆盖消掉它，
                    // 只留程序化的两段弦跟手走。覆盖在组件上，不动资产本身。
                    const FString HideSlot = ColdSteelInventory::Text(*Item, *PartKey(Pair.Key, TEXT("hide_slot")));
                    UBowPartComponent* Target = Pair.Key == SlotString && !HideSlot.IsEmpty() ? Part(SlotRiser) : Component;
                    if (Target) Target->SetMaterialOverride(HideSlot, Material);
                }
            }
            ArrowHeadMesh = Cast<UStaticMesh>(HeadPath.ResolveObject());
            if (bUsesArms)
            {
                auto* Mesh = Cast<USkeletalMesh>(ArmsPath.ResolveObject());
                Viewmodel->SetSkeletalMesh(Mesh);
                const auto* Skeleton = Mesh ? Mesh->GetSkeleton() : nullptr;
                // 5.8 的 USkeleton 不再直接暴露 GetRefSkeleton，用组件级 socket／骨骼查询。
                bHasRightHandBone = Skeleton && Viewmodel->DoesSocketExist(FName(TEXT("hand_r")));
                bHasGripMarker = Skeleton && Viewmodel->DoesSocketExist(TEXT("bow_grip"));
                bHasNockMarker = Skeleton && Viewmodel->DoesSocketExist(TEXT("bow_nock"));
                for (const TCHAR* Clip : { ClipIdle, ClipDraw, ClipHold, ClipRelease, ClipNock, TEXT("Ready"), TEXT("Equip"), TEXT("Run") })
                    Animations.Add(FName(Clip), Cast<UAnimSequence>(BowAssetPath(Prefix, Clip).ResolveObject()));
                for (int32 I = 0; I < UE_ARRAY_COUNT(NockKeys); ++I)
                    if (auto* Clip = Cast<UAnimSequence>(FSoftObjectPath(ColdSteelInventory::Text(*Item, NockKeys[I])).ResolveObject()))
                        Animations.Add(NockRoles[I], Clip);
                if (!GaitPrefix.IsEmpty())
                    for (const TCHAR* Role : GaitRoles)
                        if (auto* Clip = Cast<UAnimSequence>(BowAssetPath(GaitPrefix, Role).ResolveObject()))
                            Animations.Add(Role, Clip);
            }
            DrawSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_draw_sound"))).ResolveObject());
            ReleaseSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_release_sound"))).ResolveObject());
            NockSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_nock_sound"))).ResolveObject());
            TakeArrowSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_take_arrow_sound"))).ResolveObject());
            auto* Riser = Part(SlotRiser);
            const bool bReady = Riser && Riser->HasMesh() && (!bUsesArms ||
                (Viewmodel->GetSkeletalMeshAsset() && Animations.FindRef(ClipIdle) && Animations.FindRef(ClipDraw)
                 && Animations.FindRef(ClipNock) && Animations.FindRef(ClipRelease)));
            bPresentationReady = bReady;
            Feedback = bReady ? FString()
                              : TEXT("弓模型未加载完成，重新装备试试");
            FeedbackSeconds = bReady ? 0.f : 3.f;
            if (bReady) SetStage(EBowStage::Equip, EquipSeconds);
        }));
}

void UBowWeaponComponent::ApplyNumbers(const FColdSteelItem* Item)
{
    const auto* G=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto Mods=G?G->Calculate(Item->Definition,G->Installed(*Item)).Bow:FGunsmithStats::FBowModifiers();
    auto Number = [&](const TCHAR* Key, float Default)
    { return static_cast<float>(ColdSteelInventory::Number(*Item, Key, Default)); };
    NockSeconds = FMath::Max(.12f, Number(TEXT("nock_seconds"), .68f));
    const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    DrawSeconds = FMath::Max(.3f, float(ColdSteelWeaponStats::Interval(Item, Profile, Number(TEXT("draw_seconds"), 1.4f))));
    HoldSeconds = FMath::Max(0.f, Number(TEXT("hold_seconds"), 2.2f));
    ReleaseSeconds = FMath::Max(.08f, Number(TEXT("release_seconds"), .3f));
    RecoverSeconds = FMath::Max(.08f, Number(TEXT("recover_seconds"), .34f));
    EquipSeconds = FMath::Max(.1f, Number(TEXT("equip_seconds"), .45f));
    DrawEntrySeconds = FMath::Max(.01f, Number(TEXT("bow_draw_entry_seconds"), .2f));
    NockContactFraction = FMath::Clamp(Number(TEXT("nock_contact_fraction"), .82f), 0.f, 1.f);
    bNockKeepsDrawPose = Number(TEXT("bow_nock_keeps_draw_pose"), 0.f) > .5f;
    TakeArrowContactFraction = FMath::Clamp(Number(TEXT("nock_take_fraction"), .28f), 0.f, NockContactFraction);
    bOriginalAudioSpeed = Number(TEXT("bow_audio_original_speed"), 0.f) > .5f;
    bNockHasCarryAxis = !ColdSteelInventory::Text(*Item, TEXT("bow_nock_animation")).IsEmpty();
    FlexDistribution = FMath::Clamp(Number(TEXT("bow_flex_distribution"), 1.15f), .5f, 2.f);
    StringReturnSeconds = FMath::Clamp(Number(TEXT("bow_release_return_seconds"), .032f), .025f, .04f);
    RingSeconds = FMath::Clamp(Number(TEXT("bow_release_ring_seconds"), .17f), .12f, .2f);
    FeedbackScale = FMath::Clamp(Number(TEXT("bow_feedback_scale"), 1.f), .5f, 1.5f);
    DrawCurve.Reset();
    TArray<FString> CurveText;
    ColdSteelInventory::Text(*Item, TEXT("draw_curve")).ParseIntoArray(CurveText, TEXT(","), true);
    for (const FString& Value : CurveText) DrawCurve.Add(FMath::Clamp(FCString::Atof(*Value), 0.f, 1.f));
    FullDamage = Number(TEXT("full_damage"), 69.f);
    FullSpeedCM = Number(TEXT("full_speed_cm"), 9800.f);
    MinSpeedRatio = FMath::Clamp(Number(TEXT("min_speed_ratio"), .35f), 0.f, 1.f);
    GravityCM = Number(TEXT("arrow_gravity_cm"), 520.f);
    RangeCM = Number(TEXT("range_cm"), 3200.f);
    StaminaCost = Number(TEXT("stamina_cost"), 3.f);
    CriticalChance = Number(TEXT("critical_chance"), -1.f);
    ToughnessMultiplier = Number(TEXT("toughness_multiplier"), 0.f);
    LengthCM = Number(TEXT("bow_length_cm"), LengthCM);
    DepthCM = Number(TEXT("bow_depth_cm"), DepthCM);
    BowScale = Number(TEXT("bow_scale"), BowScale);
    // 旧平铺半径键作为回落；部件键 `bow_part_<槽名>_radius_cm` 在 ApplyParts 里覆盖。
    StringRadiusCM = Number(TEXT("string_radius_cm"), StringRadiusCM);
    ArrowRadiusCM = Number(TEXT("arrow_radius_cm"), ArrowRadiusCM);
    ArrowLengthCM = Number(TEXT("arrow_length_cm"), ArrowLengthCM);
    SwayAmplitudeCM = Number(TEXT("sway_amplitude_cm"), .9f);
    SteadySwayScale = FMath::Clamp(Number(TEXT("steady_sway_scale"), SteadySwayScale), 0.f, 1.f);
    AimInSeconds = FMath::Max(.01f, Number(TEXT("bow_ads_in_seconds"), .18f));
    AimOutSeconds = FMath::Max(.01f, Number(TEXT("bow_ads_out_seconds"), .16f));
    AimFOVScale = FMath::Clamp(Number(TEXT("bow_ads_fov_scale"), .9f), .5f, 1.f);
    OpticalMagnification = FMath::Clamp(Number(TEXT("bow_scope_magnification"), 1.f), 1.f, 4.f);
    CrouchInSeconds = FMath::Max(.01f, Number(TEXT("bow_crouch_in_seconds"), .18f));
    CrouchOutSeconds = FMath::Max(.01f, Number(TEXT("bow_crouch_out_seconds"), .22f));
    CrouchCantDegrees = Number(TEXT("bow_crouch_cant_deg"), -55.f);
    HipSpread = FMath::Max(0.f, Number(TEXT("bow_hip_spread"), .035f));
    MoveSpreadMax = FMath::Max(0.f, Number(TEXT("bow_move_spread"), .04f));
    AirSpreadMax = FMath::Max(0.f, Number(TEXT("bow_air_spread"), .05f));
    ShotSpreadStep = FMath::Max(0.f, Number(TEXT("bow_shot_spread"), .012f));
    SpreadRecovery = FMath::Max(0.f, Number(TEXT("bow_spread_recovery"), .06f));
    CrouchSpreadScale = FMath::Clamp(Number(TEXT("bow_crouch_spread_scale"), .7f), 0.f, 1.f);
    NockSeconds*=Mods.Nock;HoldSeconds*=Mods.Hold;FullDamage*=Mods.Damage;
    FullSpeedCM*=Mods.Speed;StaminaCost*=Mods.Stamina;SwayAmplitudeCM*=Mods.Sway;
    HipSpread*=Mods.Spread;MoveSpreadMax*=Mods.Spread;AirSpreadMax*=Mods.Spread;
    ShotSpreadStep*=Mods.Spread;SpreadRecovery*=Mods.Spread;
    AimInSeconds*=Mods.ADS;AimOutSeconds*=Mods.ADS;
    ReadVector3(Item, TEXT("bow_hip_offset_cm"), HipOffsetCM);
    ReadVector3(Item, TEXT("bow_ads_rest_cm"), AimRestLocationCM);
    bHasAimSight = ReadVector3(Item, TEXT("bow_ads_sight_cm"), AimSightPointCM);
    AimSightDistanceCM = FMath::Max(30.f, Number(TEXT("bow_ads_sight_distance_cm"), 78.f));
    ReadVector3(Item, TEXT("bow_crouch_offset_cm"), CrouchOffsetCM);
    ReadVector3(Item, TEXT("nock_upper_cm"), UpperTipCM);
    ReadVector3(Item, TEXT("nock_lower_cm"), LowerTipCM);
    ReadVector3(Item, TEXT("brace_nock_cm"), BraceNockCM);
    ReadVector3(Item, TEXT("draw_anchor_cm"), DrawAnchorCM);
    ReadVector3(Item, TEXT("arrow_rest_cm"), ArrowRestCM);
    ReadVector3(Item, TEXT("bow_location_cm"), BowLocationCM);
    ReadVector3(Item, TEXT("bow_grip_trim_cm"), GripTrimCM);
    FVector Rotation;
    if (ReadVector3(Item, TEXT("bow_ads_rotation_deg"), Rotation))
        AimBowRotation = FRotator(Rotation.X, Rotation.Y, Rotation.Z);
    if (ReadVector3(Item, TEXT("bow_rotation_deg"), Rotation))
        BowRotation = FRotator(Rotation.X, Rotation.Y, Rotation.Z);
    // 原生 Bow 动画的相机空间变换；不沿用 M4 的组件旋转。
    if (ReadVector3(Item, TEXT("bow_arms_rotation_deg"), Rotation))
    {
        Viewmodel->SetRelativeRotation(FRotator(Rotation.X, Rotation.Y, Rotation.Z));
    }
}

FString UBowWeaponComponent::PartKey(FName Slot, const TCHAR* Suffix)
{
    return FString::Printf(TEXT("bow_part_%s_%s"), *Slot.ToString(), Suffix);
}

UBowPartComponent* UBowWeaponComponent::Part(FName Slot) const
{
    const auto* Found = Parts.Find(Slot);
    return Found ? Found->Get() : nullptr;
}

UBowPartComponent* UBowWeaponComponent::FindPart(FName Slot) const
{
    return Part(Slot);
}

TArray<FName> UBowWeaponComponent::PartSlots() const
{
    return SlotOrder;
}

FString UBowWeaponComponent::PartMeshPath(FName Slot) const
{
    const auto* Found = PendingPartMeshes.Find(Slot);
    return Found ? Found->ToString() : FString();
}

int32 UBowWeaponComponent::RodFor(FName Slot, int32 Index)
{
    UBowPartComponent* Component = Part(Slot);
    if (!Component) return INDEX_NONE;
    TArray<int32>& Handles = PartRods.FindOrAdd(Slot);
    while (Handles.Num() <= Index)
        Handles.Add(Component->AddRod(*FString::Printf(TEXT("%sRod%d"), *Slot.ToString(), Handles.Num())));
    return Handles.IsValidIndex(Index) ? Handles[Index] : INDEX_NONE;
}

float UBowWeaponComponent::AimVerticalFOV(float BaseFOV) const
{
    const float OnePowerFOV = BaseFOV * AimFOVScale;
    return FMath::RadiansToDegrees(2.f * FMath::Atan(
        FMath::Tan(FMath::DegreesToRadians(OnePowerFOV) * .5f) / ScopeMagnification()));
}

FString UBowWeaponComponent::PresentationSignature(const FColdSteelItem* Item) const
{
    FString Text = ColdSteelInventory::Text(*Item, TEXT("bow_viewmodel")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("bow_animation_prefix")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("bow_quick_combat_animation")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_head_mesh")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_ammo")) + TEXT("|");
    for (const TCHAR* Key : NockKeys) Text += ColdSteelInventory::Text(*Item, Key) + TEXT("|");
    Text += ColdSteelInventory::Text(*Item, TEXT("bow_locomotion_prefix")) + TEXT("|");
    for (const FName& Slot : BowSlotNames(ColdSteelInventory::Text(*Item, TEXT("bow_part_slots"))))
    {
        Text += Slot.ToString() + TEXT("=") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("mesh")))
            + TEXT("/") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("material")))
            + TEXT("/") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("hide_slot"))) + TEXT(";");
    }
    // 旧平铺键也进签名：还没写部件键的表，改 `bow_mesh` 同样能触发表现代码的重载。
    Text += ColdSteelInventory::Text(*Item, TEXT("bow_mesh")) + TEXT("/")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_mesh"));
    for (const TCHAR* Key : { TEXT("bow_draw_sound"), TEXT("bow_release_sound"), TEXT("bow_nock_sound"), TEXT("bow_take_arrow_sound"), TEXT("bow_string_hidden_material") })
        Text += TEXT("|") + ColdSteelInventory::Text(*Item, Key);
    return Text;
}

void UBowWeaponComponent::CollectPartAssets(const FColdSteelItem* Item)
{
    PendingPartMeshes.Reset();
    PendingPartMaterials.Reset();
    for (const FName& Slot : SlotOrder)
    {
        // 每槽资源键：bow_part_<槽名>_mesh / _material；留空回落到旧平铺键。
        FSoftObjectPath Mesh(ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("mesh"))));
        if (Mesh.IsNull())
        {
            if (Slot == SlotRiser) Mesh = FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_mesh")));
            else if (Slot == SlotArrow) Mesh = FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("arrow_mesh")));
        }
        FSoftObjectPath Material(ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("material"))));
        if (Material.IsNull() && Slot == SlotString)
            Material = FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_string_hidden_material")));
        PendingPartMeshes.Add(Slot, Mesh);
        PendingPartMaterials.Add(Slot, Material);
    }
}

void UBowWeaponComponent::ApplyParts(const FColdSteelItem* Item)
{
    SlotOrder = BowSlotNames(ColdSteelInventory::Text(*Item, TEXT("bow_part_slots")));
    auto* Riser = Part(SlotRiser);
    // 数据表新增的槽就地补建（挂在弓体下，共享它的局部坐标），改造系统不必重建组件。
    for (const FName& Slot : SlotOrder)
    {
        if (Part(Slot)) continue;
        auto* Component = NewObject<UBowPartComponent>(GetOwner(),
            *FString::Printf(TEXT("BowPart_%s"), *Slot.ToString()));
        Component->InitializeAsPart(GetOwner(), Slot, Riser);
        Parts.Add(Slot, Component);
    }
    auto Number = [&](const TCHAR* Key, float Default)
    { return static_cast<float>(ColdSteelInventory::Number(*Item, Key, Default)); };
    for (const FName& Slot : SlotOrder)
    {
        UBowPartComponent* Component = Part(Slot);
        if (!Component) continue;
        const int32 Rods = FMath::Max(0, static_cast<int32>(Number(*PartKey(Slot, TEXT("rods")),
            Slot == SlotString ? 2.f : Slot == SlotArrow ? 1.f : 0.f)));
        while (Component->RodCount() < Rods) RodFor(Slot, Component->RodCount());
        if (Slot != SlotRiser && Slot != SlotString && Slot != SlotArrow)
        {
            FVector Location = FVector::ZeroVector, Rotation = FVector::ZeroVector;
            ReadVector3(Item, *PartKey(Slot, TEXT("location_cm")), Location);
            ReadVector3(Item, *PartKey(Slot, TEXT("rotation_deg")), Rotation);
            Component->SetMount(Location, FRotator(Rotation.X, Rotation.Y, Rotation.Z),
                Number(*PartKey(Slot, TEXT("scale")), 1.f));
        }
    }
    // 细杆粗细同样两键并存：新键优先，旧平铺键兜底。
    StringRadiusCM = Number(*PartKey(SlotString, TEXT("radius_cm")), StringRadiusCM);
    ArrowRadiusCM = Number(*PartKey(SlotArrow, TEXT("radius_cm")), ArrowRadiusCM);
    BowScale = Number(*PartKey(SlotRiser, TEXT("scale")), BowScale);
    if (Riser) Riser->SetRelativeScale3D(FVector(BowScale));
    for (auto& Pair : Parts) if (!SlotOrder.Contains(Pair.Key) && Pair.Value) Pair.Value->SetPartVisible(false);
    CollectPartAssets(Item);
}

bool UBowWeaponComponent::CanUse() const
{
    auto* Pawn = Character.Get();
    if (!Pawn) return false;
    const auto* PC = Cast<APlayerController>(Pawn->GetController());
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Building = PC ? PC->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    return bPresentationReady && !AFPSGAMEPlayerController::BlocksOngoingActions(PC) && !Pawn->IsTraversing()
        && !Pawn->IsCastBlockingLeftHandAction()
        && (!Health || !Health->IsDead()) && (!Building || !Building->IsBuilding());
}

float UBowWeaponComponent::DrawFraction() const
{
    if (Stage == EBowStage::Holding) return 1.f;
    if (Stage != EBowStage::Drawing || Elapsed < 0.f) return 0.f;
    const float T = FMath::Clamp(Elapsed / FMath::Max(.0001f, DrawSeconds), 0.f, 1.f);
    if (DrawCurve.Num() < 2) return T;
    const float Sample = T * (DrawCurve.Num() - 1);
    const int32 I = FMath::Min(FMath::FloorToInt(Sample), DrawCurve.Num() - 2);
    return FMath::Lerp(DrawCurve[I], DrawCurve[I + 1], Sample - I);
}

int32 UBowWeaponComponent::ArrowsInPouch() const
{
    auto* World = GetWorld();
    auto* GameInstance = World ? World->GetGameInstance() : nullptr;
    const auto* Profile = GameInstance ? GameInstance->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!Profile || ArrowId.IsEmpty()) return 0;
    return static_cast<int32>(FMath::Clamp<int64>(Profile->PouchCount(ArrowId), 0, MAX_int32));
}

bool UBowWeaponComponent::ConsumeArrowFromPouch(FString& Reason, bool& bSpentOwnedArrow)
{
    bSpentOwnedArrow = false;
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return false;
    auto* Pawn = Character.Get();
    // 开发面板的"无限备弹"按弹种生效：arrow_wood 在 ammo_types.json 里允许无限，
    // 于是发射不扣箭袋，与枪械无限备弹同一口径。
    if (Pawn && Pawn->HasInfiniteReserveAmmoFor(ArrowId)) return true;
    if (Profile->PouchCount(ArrowId) <= 0)
    {
        Reason = FString::Printf(TEXT("箭袋里没有%s"), *Profile->AmmoLabel(ArrowId));
        return false;
    }
    if (!Profile->SpendAmmo(ArrowId, 1))
    {
        Reason = TEXT("箭支扣除未保存，未发射");
        return false;
    }
    bSpentOwnedArrow = true;
    return true;
}

void UBowWeaponComponent::StopDrawAudio()
{
    if (IsValid(DrawAudio)) DrawAudio->FadeOut(.018f, 0.f);
    DrawAudio = nullptr;
}

void UBowWeaponComponent::StopHandlingAudio()
{
    if (IsValid(HandlingAudio)) HandlingAudio->Stop();
    HandlingAudio = nullptr;
}

void UBowWeaponComponent::PlayHandlingSound(USoundBase* Sound, float Volume, float FitSeconds)
{
    StopHandlingAudio();
    if (!Sound) return;
    // Only speed up a short handling sample when the quick-entry window is
    // smaller. R nocking retains the original texture and pitch.
    const float Pitch = FitSeconds > 0.f ? FMath::Max(1.f, Sound->GetDuration() / FitSeconds) : 1.f;
    HandlingAudio = UGameplayStatics::SpawnSound2D(this, Sound, Volume, Pitch);
}

void UBowWeaponComponent::SetStage(EBowStage Next, float Seconds, float StartSeconds)
{
    StopDrawAudio();
    if (Next == EBowStage::Drawing)
        if (const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            if (const auto* Item = Profile->ActiveBow())
                DrawSeconds = FMath::Max(.3f, float(ColdSteelWeaponStats::Interval(Item, Profile,
                    ColdSteelInventory::Number(*Item, TEXT("draw_seconds"), 1.4))));
    Stage = Next;
    StageSeconds = Seconds;
    Elapsed = FMath::Max(0.f, StartSeconds);
    HoldElapsed = 0.f;
    bNockSoundPlayed = false;
    bTakeArrowSoundPlayed = false;
    // Start exactly when Drawing begins, after the 0.2 s entry. Direct-video
    // cues retain their native speed/pitch and may end before the draw motion;
    // do not stretch or loop the recording to fill the skill-adjusted clock.
    // Early release, cancellation and unequip still stop this voice.
    if (Next == EBowStage::Drawing && DrawSound && Elapsed < DrawSeconds)
    {
        const float Pitch = bOriginalAudioSpeed ? 1.f : FMath::Max(.01f, DrawSound->GetDuration() / DrawSeconds);
        const float StartTime = Elapsed * Pitch;
        if (StartTime < DrawSound->GetDuration())
            DrawAudio = UGameplayStatics::SpawnSound2D(this, DrawSound, bOriginalAudioSpeed ? .6f : .42f, Pitch, StartTime);
    }
}

void UBowWeaponComponent::BeginNock()
{
    if (!IsEquipped() || !CanUse()) return;
    if (Character.IsValid() && Character->IsChoosingAmmo()) return;
    if (Stage != EBowStage::Ready || bArrowNocked) return;
    if (Character.IsValid() && Character->IsCastBlockingLeftHandAction()) return;
    const auto* Pawn = Character.Get();
    if (ArrowsInPouch() <= 0 && (!Pawn || !Pawn->HasInfiniteReserveAmmoFor(ArrowId)))
    {
        ShowFeedback(TEXT("箭袋里没有可用的箭"));
        return;
    }
    // Nocking is a visual reservation. Spend once at successful launch, so
    // switching weapons, saving or interruption cannot destroy an unfired arrow.
    SetStage(EBowStage::Nocking, NockSeconds);
    if (bUsesArms)
    {
        Viewmodel->CaptureCarry(FMath::Min(.07f, NockSeconds * .2f));
        PlayClip(ClipNock, 0.f, false);
    }
}

bool UBowWeaponComponent::SwitchArrow(const FString& Target)
{
    if (!IsEquipped() || !CanUse() || Stage != EBowStage::Ready) return false;
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const FString BowId = InstanceId;
    if (!Profile || !Profile->SelectBowAmmo(BowId, Target))
    {
        ShowFeedback(Profile ? Profile->ResultMessage() : TEXT("箭袋不可用"));
        return false;
    }
    RefreshEquipment(Profile);
    BeginNock();
    return true;
}

void UBowWeaponComponent::BeginPrimaryAttack()
{
    if (!IsEquipped() || !CanUse()) return;
    if (Character.IsValid() && Character->IsChoosingAmmo()) return;
    if (Character.IsValid() && Character->IsCastBlockingLeftHandAction()) return;
    switch (Stage)
    {
    case EBowStage::Ready:
    case EBowStage::Release:
    case EBowStage::Recover:
        // Release/recovery are interruptible presentation, never a fire-input lock.
        BeginDrawEntry();
        return;
    case EBowStage::DrawEntry:
    case EBowStage::Nocking:
        return;                          // 搭箭进行中不接第二下，避免抢拍
    case EBowStage::Drawing:
    case EBowStage::Holding:
        return;                          // 已经拉开：等真实释放
    default:
        return;                          // 装备／近战／缓收弓仍由原动作占用
    }
}

void UBowWeaponComponent::BeginDrawEntry()
{
    const auto* Pawn = Character.Get();
    if (!bArrowNocked && ArrowsInPouch() <= 0 && (!Pawn || !Pawn->HasInfiniteReserveAmmoFor(ArrowId)))
    {
        ShowFeedback(TEXT("箭袋里没有可用的箭"));
        return;
    }
    bChainEntry = Stage == EBowStage::Release || Stage == EBowStage::Recover;
    bEntryNeedsArrow = !bArrowNocked;
    // The matched loaded-ready pose already holds the string. Do not stop
    // there for a second entry phase after a manual nock or a let-down.
    if (bArrowNocked && bNockKeepsDrawPose)
    {
        SetStage(EBowStage::Drawing, 0.f);
        return;
    }
    // A second press may arrive before the release pose's first visible tick.
    if (bChainEntry) SampleArms();
    SetStage(EBowStage::DrawEntry, DrawEntrySeconds);
    // The new take is authored inside the same 0.2 s budget. Existing nocked
    // arrows retain the original hand-to-string entry without another pickup.
    if (bUsesArms)
    {
        const TCHAR* Entry = DrawEntryClip();
        if (Entry == ClipDraw) Viewmodel->CaptureEntry(DrawEntrySeconds);
        else Viewmodel->CaptureCarry(FMath::Min(.045f, DrawEntrySeconds * .225f));
        PlayClip(Entry, 0.f, false);
    }
}

const TCHAR* UBowWeaponComponent::DrawEntryClip() const
{
    const TCHAR* Wanted = bChainEntry ? TEXT("ChainNock") : TEXT("QuickNock");
    return bEntryNeedsArrow && ClipLength(Wanted) > 0.f ? Wanted : ClipDraw;
}

void UBowWeaponComponent::ReleasePrimaryAttack()
{
    if (!IsEquipped() || !CanUse()) { CancelAction(); return; }
    // Releasing before reaching the string cancels without firing or spending.
    if (Stage == EBowStage::DrawEntry) { CancelAction(); return; }
    if (Stage != EBowStage::Drawing && Stage != EBowStage::Holding) return;
    // 输入释放或满拉力竭发射；菜单／翻越等打断走 CancelAction，不放箭。
    ReleaseRatio = DrawFraction();
    if (ReleaseRatio < ColdSteelBow::MinimumFireDrawFraction)
    {
        CancelAction(false);
        ShowFeedback(TEXT("至少拉弓至 50% 才能射出；已收弓，箭仍在弦上"));
        return;
    }
    SampleArms();
    UpdatePoseLayers();
    UpdateBowGeometry();
    ReleasedNockCM = NockPoint();
    if (LooseArrow(ReleaseRatio))
    {
        ReleaseFeedbackAge = 0.f;
        SetStage(EBowStage::Release, ReleaseSeconds);
    }
    else SetStage(EBowStage::Ready, 0.f);
}

void UBowWeaponComponent::CancelAction(bool bImmediate)
{
    if (!bImmediate && IsDrawing() && bArrowNocked && CanUse())
    {
        LetDownPhase = Stage == EBowStage::Holding ? 1.f : FMath::Clamp(Elapsed / DrawSeconds, 0.f, 1.f);
        LetDownRatio = DrawFraction();
        bTriggerHeld = false;
        StopHandlingAudio();
        SetStage(EBowStage::LetDown, FMath::Lerp(.14f, .22f, LetDownRatio));
        Viewmodel->CaptureEntry(.035f);
        ShowFeedback(TEXT("缓收弓：箭仍在弦上"));
        return;
    }
    StopDrawAudio();
    StopHandlingAudio();
    bTriggerHeld = bSteadyHeld = false;
    ReleaseKick = ReleaseRatio = LetDownRatio = 0.f;
    ReleaseFeedbackAge = -1.f;
    if (auto* Riser = Part(SlotRiser)) Riser->ApplyStringLoad(BraceNockCM, BraceNockCM, FlexDistribution);
    if (Stage == EBowStage::Stowed) return;
    if ((Stage == EBowStage::Drawing || Stage == EBowStage::Holding) && bArrowNocked)
        ShowFeedback(TEXT("收弓：箭仍在弦上"));
    if (IsEquipped() && CanUse()) SetStage(EBowStage::Ready, 0.f);
    else { Stage = EBowStage::Stowed; Elapsed = -1.f; HoldElapsed = 0.f; }
}

FVector UBowWeaponComponent::NockPoint() const
{
    // The string attaches to the finger contact marker only while held. After
    // release it returns to brace independently of the hand's follow-through.
    if (Stage == EBowStage::Release ||
        (Stage == EBowStage::DrawEntry && bEntryNeedsArrow && ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < RingSeconds))
    {
        const float T = FMath::Clamp(ReleaseFeedbackAge / StringReturnSeconds, 0.f, 1.f);
        return FMath::Lerp(ReleasedNockCM, BraceNockCM, FMath::SmoothStep(0.f, 1.f, T))
            + FVector(.2f * ReleaseRing(), 0.f, 0.f);
    }
    const bool bEntryContact = Stage == EBowStage::DrawEntry && bEntryNeedsArrow && Elapsed >= DrawEntrySeconds * .90f;
    const bool bContacting = (Stage == EBowStage::Nocking && Elapsed >= NockSeconds * NockContactFraction) || bEntryContact;
    if (!IsDrawing() && Stage != EBowStage::LetDown && !(Stage == EBowStage::Ready && bArrowNocked) && !bContacting) return BraceNockCM;
    if (bUsesArms && bHasGripMarker && bHasNockMarker && Viewmodel && Viewmodel->IsVisible())
    {
        const FVector HandPoint = (Viewmodel->GetSocketTransform(TEXT("bow_nock"), RTS_Component)
            * Viewmodel->GetRelativeTransform()).GetLocation();
        const FVector LocalPoint = AnimatedRiserMount().InverseTransformPosition(HandPoint);
        if (bContacting)
        {
            const float Contact = bEntryContact ? 1.f : FMath::SmoothStep(0.f, 1.f,
                (Elapsed / NockSeconds - NockContactFraction) / FMath::Max(.001f, 1.f - NockContactFraction));
            return FMath::Lerp(BraceNockCM, LocalPoint, Contact);
        }
        return LocalPoint;
    }
    const float Ratio = Stage == EBowStage::LetDown
        ? LetDownRatio * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds)) : DrawFraction();
    return FMath::Lerp(BraceNockCM, DrawAnchorCM, Ratio);
}

FVector UBowWeaponComponent::ArrowTipPoint() const
{
    // 箭尾落在弦结点，箭轴穿过箭台，沿弓体局部 +X 越过握把。
    const FVector Nock = NockPoint();
    return Nock + (ArrowRestCM - Nock).GetSafeNormal() * ArrowLengthCM;
}

bool UBowWeaponComponent::LooseArrow(float Ratio)
{
    const float ChargeDamage = ColdSteelBow::DrawDamageMultiplier(Ratio);
    if (ChargeDamage <= 0.f) return false;
    auto* Pawn = Character.Get();
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Pawn || !Camera || !Profile || !bArrowNocked) return false;
    const float Clamped = FMath::Clamp(Ratio, 0.f, 1.f);
    const float Cost = FMath::Max(0.f, StaminaCost * FMath::Lerp(.4f, 1.f, Clamped));
    if (!Profile->CanSpendStamina(Cost)) { ShowFeedback(TEXT("体力不足，已收弓")); return false; }
    const float Speed = FullSpeedCM * FMath::Lerp(MinSpeedRatio, 1.f, Clamped);
    // 从实际箭尖发射并朝准星落点收敛；近墙时另做相机到箭尖的阻挡扫掠。
    auto* Riser = Part(SlotRiser);
    auto* ArrowRest = Part(SlotArrow);
    const FVector Muzzle = Riser ? Riser->GetComponentTransform().TransformPosition(ArrowTipPoint())
                                 : Camera->GetComponentLocation();
    FHitResult AimHit;
    const FVector CameraOrigin = Camera->GetComponentLocation();
    // Match firearm hip fire: independently sample camera right/up offsets.
    // Trace the scattered ray itself; tracing the centre first would silently
    // steer hip shots back onto whatever happened to be under the crosshair.
    const float Spread = ShotSpread();
    FVector AimDirection = Camera->GetForwardVector();
    if (Spread > 0.f)
        AimDirection = (AimDirection + Camera->GetRightVector() * FMath::FRandRange(-Spread, Spread)
            + Camera->GetUpVector() * FMath::FRandRange(-Spread, Spread)).GetSafeNormal();
    const FVector FarAim = CameraOrigin + AimDirection * RangeCM;
    FCollisionQueryParams AimQuery(SCENE_QUERY_STAT(BowAim), true, Pawn);
    const bool bHitAim = GetWorld()->LineTraceSingleByChannel(AimHit, CameraOrigin, FarAim, ECC_Visibility, AimQuery);
    const FVector AimPoint = bHitAim ? AimHit.ImpactPoint : FarAim;
    const FVector AimVector = AimPoint - Muzzle;
    const bool bAimAhead = FVector::DotProduct(AimVector, Camera->GetForwardVector()) > 0.f;
    FVector LaunchDirection = bAimAhead ? AimVector.GetSafeNormal() : AimDirection;
    // Keep the physical arrow and its gravity, but zero its low arc on the
    // sampled aim point. Full ADS has no random offset; moving targets still
    // require leading and nearby obstacles still block the real projectile.
    if (bAimAhead && GravityCM > KINDA_SMALL_NUMBER)
    {
        UGameplayStatics::FSuggestProjectileVelocityParameters Arc(this, Muzzle, AimPoint, Speed);
        Arc.OverrideGravityZ = -GravityCM;
        Arc.TraceOption = ESuggestProjVelocityTraceOption::DoNotTrace;
        FVector LaunchVelocity;
        if (UGameplayStatics::SuggestProjectileVelocity(Arc, LaunchVelocity))
            LaunchDirection = LaunchVelocity.GetSafeNormal();
    }
    const FRotator Direction = LaunchDirection.Rotation();
    FActorSpawnParameters Spawn;
    Spawn.Owner = Pawn;
    Spawn.Instigator = Pawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Arrow = GetWorld()->SpawnActor<ABowArrow>(Muzzle, Direction, Spawn))
    {
        FString Reason;
        bool bSpentOwnedArrow = false;
        if (!ConsumeArrowFromPouch(Reason, bSpentOwnedArrow)) { Arrow->Destroy(); bArrowNocked = false; ShowFeedback(Reason); return false; }
        // 射击瞬间的修炼／符文快照与弹道组件同源；弓自己的暴击与破韧只在配了值时覆盖。
        FColdSteelSkillShot Shot = ColdSteelSkills::Snapshot(Pawn, Profile ? Profile->ActiveBow() : nullptr, true);
        const auto* Item = Profile->ActiveBow();
        const float BaseDamage = Shot.DamagePanel.Total() > 0.f ? Shot.DamagePanel.Total() : FullDamage;
        const float Damage = BaseDamage * ChargeDamage
            * (Item ? Profile->AmmoDamageMultiplier(*Item) : 1.f);
        if (CriticalChance >= 0.f) Shot.CriticalChance = FMath::Max(Shot.CriticalChance, CriticalChance);
        if (ToughnessMultiplier > 0.f) Shot.ToughnessDamageMultiplier = ToughnessMultiplier;
        // 箭模取自 arrow 部件：已选箭种的弦上网格与飞行网格一致，箭台保持独立。
        Arrow->Configure(Damage, Speed, GravityCM, RangeCM, Shot,
                         ArrowRest ? ArrowRest->GetMesh() : nullptr,
                         ArrowHeadMesh ? ArrowHeadMesh.Get() : nullptr,
                         ArrowRadiusCM, ArrowLengthCM, ArrowId, bSpentOwnedArrow,
                         Item ? ColdSteelInventory::Number(*Item, TEXT("arrow_recovery_seconds"), 120.f) : 120.f);
        Arrow->ResolveLaunchObstruction(CameraOrigin);
    }
    else return false;
    bArrowNocked = false;
    ReleaseKick = FMath::Lerp(.25f, 1.f, Clamped);
    ShotBloom = FMath::Min(ShotSpreadStep * 3.f, ShotBloom + ShotSpreadStep * (1.f - AimAlpha()));
    StopDrawAudio();
    StopHandlingAudio();
    if (ReleaseSound) UGameplayStatics::PlaySound2D(this, ReleaseSound, .6f, bOriginalAudioSpeed ? 1.f : 1.f + .06f * Clamped);
    Profile->SpendStamina(Cost);
    return true;
}

void UBowWeaponComponent::AdvanceAimWeight(float Delta, bool bTarget)
{
    const auto BeginTravel = [this]()
    {
        AimSegmentStart = AimProgress;
        AimSegmentVelocity = AimVelocity = 0.f;
        AimSegmentElapsed = 0.f;
        bAimBraking = false;
        const float Distance = FMath::Abs((bAimBlendTarget ? 1.f : 0.f) - AimProgress);
        // A full transition keeps the catalog time. A partial return covers
        // less distance without replaying an entire raise/lower movement.
        AimSegmentDuration = (bAimBlendTarget ? AimInSeconds : AimOutSeconds) * FMath::Sqrt(Distance);
    };
    if (bTarget != bAimBlendTarget)
    {
        bAimBlendTarget = bTarget;
        AimSegmentStart = AimProgress;
        AimSegmentVelocity = AimVelocity;
        AimSegmentElapsed = 0.f;
        // Keep the old direction's velocity briefly instead of instantly
        // negating it when RMB changes midway. Stop before either endpoint.
        const float Room = AimVelocity > 0.f ? 1.f - AimProgress : AimProgress;
        AimSegmentDuration = FMath::Abs(AimVelocity) > UE_SMALL_NUMBER
            ? FMath::Min(FMath::Min(.04f, FMath::Min(AimInSeconds, AimOutSeconds) * .15f),
                1.8f * FMath::Max(0.f, Room) / FMath::Abs(AimVelocity)) : 0.f;
        bAimBraking = AimSegmentDuration > UE_SMALL_NUMBER;
        if (!bAimBraking) BeginTravel();
    }

    // One frame can finish braking and continue travelling; consume the
    // leftover delta so the path does not depend on the rendering frame rate.
    float Remaining = Delta;
    for (int32 Segment = 0; Segment < 2 && Remaining > 0.f && AimSegmentDuration > 0.f; ++Segment)
    {
        const float Step = FMath::Min(Remaining, FMath::Max(0.f, AimSegmentDuration - AimSegmentElapsed));
        AimSegmentElapsed += Step;
        Remaining -= Step;
        const float T = FMath::Clamp(AimSegmentElapsed / AimSegmentDuration, 0.f, 1.f);
        if (bAimBraking)
        {
            AimProgress = AimSegmentStart + AimSegmentVelocity * AimSegmentDuration * (T - .5f * T * T);
            AimVelocity = AimSegmentVelocity * (1.f - T);
        }
        else
        {
            // Quintic ease has zero velocity and acceleration at both ends.
            const float Ease = T * T * T * (10.f + T * (-15.f + 6.f * T));
            const float Distance = (bAimBlendTarget ? 1.f : 0.f) - AimSegmentStart;
            AimProgress = AimSegmentStart + Distance * Ease;
            AimVelocity = Distance * 30.f * T * T * FMath::Square(1.f - T) / AimSegmentDuration;
        }
        AimProgress = FMath::Clamp(AimProgress, 0.f, 1.f);
        if (AimSegmentElapsed < AimSegmentDuration) break;
        AimVelocity = 0.f;
        if (bAimBraking) BeginTravel();
        else
        {
            AimProgress = bAimBlendTarget ? 1.f : 0.f;
            AimSegmentDuration = 0.f;
        }
    }
}

void UBowWeaponComponent::AdvanceLocomotion(float Delta, bool bUsable)
{
    const auto* Pawn = Character.Get();
    const auto* Movement = Pawn ? Pawn->GetCharacterMovement() : nullptr;
    const bool bGrounded = bUsable && Movement && Movement->IsMovingOnGround();
    const float Speed = bGrounded ? float(Pawn->GetVelocity().Size2D()) : 0.f;
    const bool bCarry = bGrounded && Stage == EBowStage::Ready;
    const float MovementWeight = bCarry ? FMath::SmoothStep(8.f, 180.f, Speed) : 0.f;
    const float RunTarget = bCarry && Pawn->IsSprinting() && Speed > 80.f ? 1.f : 0.f;
    DampCarry(GaitWeight, GaitWeightVelocity, MovementWeight, 19.f, Delta);
    DampCarry(SprintBlend, SprintBlendVelocity, RunTarget, 16.f, Delta);
    DampCarry(TravelSpeed, TravelSpeedVelocity, Speed, 18.f, Delta);
    GaitWeight = FMath::Clamp(GaitWeight, 0.f, 1.f);
    SprintBlend = FMath::Clamp(SprintBlend, 0.f, 1.f);
    // Preserve phase through starts/stops and walk/run blends. No stepping in
    // mid-air; residual pose weight can still settle over the landing.
    if (bGrounded && Speed > 3.f)
        GaitPhase = FMath::Fmod(GaitPhase + Delta * FMath::Clamp(TravelSpeed, 0.f, 1000.f)
            / FMath::Lerp(430.f, 490.f, SprintBlend), 1.f);
    if (!Pawn) return;
    const float Yaw = Pawn->GetControlRotation().Yaw;
    const float TurnTarget = bUsable && bHaveViewYaw
        ? FMath::Clamp(FMath::FindDeltaAngleDegrees(PreviousViewYaw, Yaw) / Delta / 180.f, -1.f, 1.f) : 0.f;
    PreviousViewYaw = Yaw;
    bHaveViewYaw = bUsable;
    DampCarry(TurnFollow, TurnFollowVelocity, TurnTarget, 14.f, Delta);
    FVector Direction = bGrounded ? FRotator(0.f, Yaw, 0.f).UnrotateVector(Pawn->GetVelocity()) / 700.f : FVector::ZeroVector;
    Direction.Z = 0.f;
    Direction = Direction.GetClampedToMaxSize(1.f);
    DampCarry(TravelDirection, TravelDirectionVelocity, Direction, 12.f, Delta);
    const FVector Lag = (Direction - TravelDirection).GetClampedToMaxSize(.8f);
    const float Restraint = (Stage == EBowStage::Ready ? 1.f : IsDrawing() ? .15f : 0.f)
        * FMath::Lerp(1.f, .48f, CrouchProgress);
    CarryOffset = FVector(-1.4f * Lag.X, -.65f * TravelDirection.Y - .6f * Lag.Y,
        -.3f * FMath::Abs(Lag.X)) * Restraint;
    CarryRotation = FRotator(.8f * Lag.X, -.7f * TurnFollow,
        -1.3f * TravelDirection.Y - .6f * TurnFollow) * Restraint;
}

void UBowWeaponComponent::AdvanceActionBeforeCamera(float Delta)
{
    // A contact query refreshes the camera with Delta=0. Do not re-enter the action clock.
    if (!IsEquipped() || Delta <= 0.f) return;
    const bool bUsable = CanUse();
    // Aim is advanced once before the camera reads its shaped weight.
    const auto AdvanceWeight = [Delta](float& Weight, bool bTarget, float In, float Out)
    {
        Weight = FMath::Clamp(Weight + FMath::Max(0.f, Delta) * (bTarget ? 1.f / In : -1.f / Out), 0.f, 1.f);
    };
    AdvanceAimWeight(Delta, bUsable && bSteadyHeld);
    AdvanceWeight(CrouchProgress, bUsable && Character.IsValid() && Character->bIsCrouched,
        CrouchInSeconds, CrouchOutSeconds);
    AdvanceLocomotion(Delta, bUsable);
    // Keep the right/lower resting position. Rotate into the crosshair during
    // the same entry clock, retain the alignment for a nocked arrow, and let
    // it go with the existing release follow-through rather than snapping.
    const bool bFollowThrough = Stage == EBowStage::Release
        && Elapsed < (ReleaseSeconds + RecoverSeconds) * .15625f;
    const bool bAlignHip = Stage == EBowStage::DrawEntry || IsDrawing() || Stage == EBowStage::LetDown
        || (Stage == EBowStage::Ready && bArrowNocked)
        || (Stage == EBowStage::Nocking && Elapsed >= NockSeconds * NockContactFraction)
        || bFollowThrough;
    AdvanceWeight(HipAimProgress, bUsable && bAlignHip, DrawEntrySeconds,
        (ReleaseSeconds + RecoverSeconds) * .84375f);
    const auto* Pawn = Character.Get();
    const auto* Movement = Pawn ? Pawn->GetCharacterMovement() : nullptr;
    const float MoveTarget = Pawn ? FMath::Clamp(float(Pawn->GetVelocity().Size2D()) / 500.f, 0.f, 1.f) * MoveSpreadMax : 0.f;
    const float AirTarget = Movement && !Movement->IsMovingOnGround() ? AirSpreadMax : 0.f;
    MoveSpread = FMath::Lerp(MoveSpread, MoveTarget, 1.f - FMath::Exp(-6.f * FMath::Max(0.f, Delta)));
    AirSpread = FMath::Lerp(AirSpread, AirTarget, 1.f - FMath::Exp(-10.f * FMath::Max(0.f, Delta)));
    ShotBloom = FMath::Max(0.f, ShotBloom - FMath::Max(0.f, Delta) * SpreadRecovery);
    if (!bUsable)
    {
        CancelAction();
        return;
    }
    if (ReleaseFeedbackAge >= 0.f) ReleaseFeedbackAge += Delta;
    if (Stage == EBowStage::Stowed) SetStage(EBowStage::Equip, EquipSeconds);
    if (Elapsed < 0.f) return;
    if (Character.IsValid() && Character->IsSprinting() && Stage != EBowStage::Ready && Stage != EBowStage::Equip)
        CancelAction();
    Viewmodel->AdvanceEntry(Delta);
    Elapsed += Delta;
    VisualTime += Delta;
    switch (Stage)
    {
    case EBowStage::Equip:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    case EBowStage::DrawEntry:
        if (bEntryNeedsArrow && !bTakeArrowSoundPlayed && Elapsed >= DrawEntrySeconds * .30f)
        {
            bTakeArrowSoundPlayed = true;
            if (Elapsed < DrawEntrySeconds * .90f) PlayHandlingSound(TakeArrowSound, .4f);
        }
        if (bEntryNeedsArrow && !bNockSoundPlayed && Elapsed >= DrawEntrySeconds * .90f)
        {
            bNockSoundPlayed = true;
            PlayHandlingSound(NockSound, .5f);
        }
        if (Elapsed >= StageSeconds)
        {
            const float Remainder = Elapsed - StageSeconds;
            bArrowNocked = true;
            // Preserve the part of this frame beyond 0.2 s, so entry length
            // does not grow by an extra rendered frame at low frame rates.
            SetStage(EBowStage::Drawing, 0.f, Remainder);
        }
        break;
    case EBowStage::Nocking:
        if (!bTakeArrowSoundPlayed && Elapsed >= NockSeconds * TakeArrowContactFraction)
        {
            bTakeArrowSoundPlayed = true;
            // A long frame that already reached nock contact must not start
            // the earlier handling event after the arrow is on the string.
            if (Elapsed < NockSeconds * NockContactFraction)
                PlayHandlingSound(TakeArrowSound, .4f,
                    NockSeconds * NockContactFraction - Elapsed);
        }
        if (!bNockSoundPlayed && Elapsed >= NockSeconds * NockContactFraction)
        {
            bNockSoundPlayed = true;
            PlayHandlingSound(NockSound, .5f);
        }
        // 搭箭完成：左键仍按着就顺势开始拉弓，否则停在已上弦的 Ready。
        if (Elapsed >= StageSeconds)
        {
            const float Remainder = Elapsed - StageSeconds;
            bArrowNocked = true;
            if (bTriggerHeld && bNockKeepsDrawPose)
                SetStage(EBowStage::Drawing, 0.f, Remainder);
            else
            {
                SetStage(EBowStage::Ready, 0.f);
                if (bTriggerHeld) BeginDrawEntry();
            }
        }
        break;
    case EBowStage::Drawing:
        if (Elapsed >= DrawSeconds) SetStage(EBowStage::Holding, 0.f);
        break;
    case EBowStage::Holding:
        HoldElapsed += Delta;
        // 保持超时：弓臂撑不住自动撒弦，不算"完美释放"。
        if (HoldSeconds > 0.f && HoldElapsed >= HoldSeconds) ReleasePrimaryAttack();
        break;
    case EBowStage::Release:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Recover, RecoverSeconds);
        break;
    case EBowStage::Recover:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    case EBowStage::LetDown:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    default:
        break;
    }
}

float UBowWeaponComponent::ShotSpread() const
{
    const float Low = FMath::SmoothStep(0.f, 1.f, CrouchProgress);
    return (HipSpread + MoveSpread + AirSpread + ShotBloom)
        * FMath::Lerp(1.f, CrouchSpreadScale, Low) * (1.f - AimAlpha());
}

bool UBowWeaponComponent::ShouldShowCrosshair() const
{
    return IsEquipped() && CanUse() && Stage != EBowStage::Stowed && Stage != EBowStage::Equip
        && Character.IsValid() && !Character->IsSprinting();
}

float UBowWeaponComponent::ReleasePulse() const
{
    if (ReleaseFeedbackAge < 0.f || ReleaseFeedbackAge >= RingSeconds) return 0.f;
    const float T = ReleaseFeedbackAge;
    return ReleaseRatio * FeedbackScale * (1.f - FMath::Exp(-160.f * T)) * FMath::Exp(-28.f * T);
}

float UBowWeaponComponent::ReleaseRing() const
{
    if (ReleaseFeedbackAge <= StringReturnSeconds || ReleaseFeedbackAge >= RingSeconds) return 0.f;
    const float T = (ReleaseFeedbackAge - StringReturnSeconds) / (RingSeconds - StringReturnSeconds);
    return ReleaseRatio * FeedbackScale * FMath::Sin(T * 4.f * PI) * FMath::Exp(-3.5f * T) * FMath::Square(1.f - T);
}

void UBowWeaponComponent::GetCameraMotion(FVector& Location, FRotator& Rotation) const
{
    Location = FVector::ZeroVector;
    Rotation = FRotator::ZeroRotator;
    if (!IsEquipped() || Elapsed < 0.f) return;
    const float Scale = FMath::Max(0.f, CVarBowSway.GetValueOnGameThread());
    float Ratio = DrawFraction();
    if (ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < .14f)
        Ratio = FMath::Max(Ratio, ReleaseRatio * (1.f - FMath::SmoothStep(0.f, 1.f, ReleaseFeedbackAge / .14f)));
    if (Stage == EBowStage::LetDown) Ratio = LetDownRatio * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds));
    const float Kick = ReleasePulse() * FMath::Lerp(1.f, .4f, AimAlpha());
    Location += FVector(-3.2f * Ratio + .6f * Kick, 0.f, 0.f) * Scale;
    Rotation.Pitch += (-.5f * Ratio + .3f * Kick) * Scale;
    Rotation.Roll += .8f * Ratio * Scale;
    if (Stage == EBowStage::Holding)
    {
        // 满拉保持的呼吸抖动随保持时长上升；右键稳持把幅度压到配置比例。
        const float Grow = FMath::Clamp(HoldElapsed / FMath::Max(.2f, HoldSeconds), 0.f, 1.f);
        const float Amplitude = SwayAmplitudeCM * (.35f + .65f * Grow)
            * FMath::Lerp(1.f, SteadySwayScale, AimAlpha()) * Scale;
        Rotation.Yaw += (FMath::Sin(VisualTime * 1.05f) + .18f * FMath::Sin(VisualTime * 4.13f)) * Amplitude * .1f;
        Rotation.Pitch += (FMath::Sin(VisualTime * .73f + 1.1f) + .15f * FMath::Sin(VisualTime * 3.37f + .4f)) * Amplitude * .085f;
    }
}

FTransform UBowWeaponComponent::AnimatedRiserMount() const
{
    FTransform Mount = Viewmodel->GetSocketTransform(TEXT("bow_grip"), RTS_Component)
        * Viewmodel->GetRelativeTransform();
    FVector Offset = FVector::ZeroVector, RotationText = FVector::ZeroVector;
    ReadVector3Text(CVarBowLocation.GetValueOnGameThread(), Offset);
    ReadVector3Text(CVarBowRotation.GetValueOnGameThread(), RotationText);
    Mount.SetScale3D(FVector(BowScale));
    Mount.AddToTranslation(GripTrimCM + Offset);
    Mount.SetRotation((FRotator(RotationText.X, RotationText.Y, RotationText.Z).Quaternion()
        * Mount.GetRotation()).GetNormalized());
    return Mount;
}

void UBowWeaponComponent::UpdatePoseLayers()
{
    if (!Pivot) return;
    if (!bHasGripMarker || !Viewmodel->IsVisible())
    {
        Pivot->SetRelativeTransform(FTransform::Identity);
        return;
    }
    // Read the unlayered animated grip, never last frame's world-space pivot.
    const FTransform Grip = Viewmodel->GetSocketTransform(TEXT("bow_grip"), RTS_Component)
        * Viewmodel->GetRelativeTransform();
    const FVector GripLocation = Grip.GetLocation();
    const float Low = FMath::SmoothStep(0.f, 1.f, CrouchProgress);
    FQuat HipRotation(FVector::ForwardVector,
        FMath::DegreesToRadians(CrouchCantDegrees * Low));
    HipRotation = (CarryRotation.Quaternion() * HipRotation).GetNormalized();
    const float HipAlignment = FMath::SmoothStep(0.f, 1.f, HipAimProgress);
    const FVector HipGrip = GripLocation + HipOffsetCM + CrouchOffsetCM * Low + CarryOffset;
    const FTransform Mount = AnimatedRiserMount();
    const FVector Rest = Mount.TransformPosition(ArrowRestCM);
    // Release keeps its aiming plane during follow-through; only the string
    // snaps back. Otherwise the changing brace axis would yaw the entire arm.
    const FVector Tail = Mount.TransformPosition(
        Stage == EBowStage::Release || Stage == EBowStage::Recover ? ReleasedNockCM : NockPoint());
    if (HipAlignment > 0.f)
    {
        // Aim the actual nock-to-rest line, not the bow mesh's nominal X axis.
        // Solve around the grip so the latest right/lower framing and every
        // finger/string contact stay together. The target lies on the same
        // camera-centre ray used by the crosshair, before shot randomisation.
        const FVector Axis = HipRotation.RotateVector((Rest - Tail).GetSafeNormal());
        const FVector TailFromGrip = HipRotation.RotateVector(Tail - GripLocation);
        const FVector TargetFromGrip = FVector(FMath::Max(200.f, RangeCM), 0.f, 0.f) - HipGrip;
        const double Along = FVector::DotProduct(TailFromGrip, Axis);
        const double Discriminant = FMath::Square(Along) + TargetFromGrip.SizeSquared()
            - TailFromGrip.SizeSquared();
        if (!Axis.IsNearlyZero() && Discriminant > 0.)
        {
            // A point on the arrow's extended ray at the target's radius can
            // be rotated exactly onto it while keeping the grip stationary.
            const FVector RayPoint = TailFromGrip + Axis * (-Along + FMath::Sqrt(Discriminant));
            const FQuat Correction = FQuat::FindBetweenNormals(RayPoint.GetSafeNormal(), TargetFromGrip.GetSafeNormal());
            const float Weight = FMath::SmoothStep(0.f, 1.f, HipAlignment);
            HipRotation = (FQuat::Slerp(FQuat::Identity, Correction, Weight) * HipRotation).GetNormalized();
        }
    }

    // Keep the ADS assembly forward/right/below the sight line, so the drawing
    // palm and forearm do not fill the centre of the zoomed view. Orient the
    // actual arrow axis back to the reticle instead of putting its near nock
    // directly in front of the eye. All contacts share the same rigid delta.
    const float Kick = ReleasePulse() * .4f;
    const FVector AimAnchor = bHasAimSight ? AimSightPointCM : ArrowRestCM;
    const FVector TargetAnchor = (bHasAimSight ? FVector(AimSightDistanceCM, 0.f, 0.f) : AimRestLocationCM)
        + FVector(-.45f * Kick, 0.f, -.1f * Kick);
    const FVector ArrowAxis = (ArrowRestCM - Mount.InverseTransformPosition(Tail)).GetSafeNormal();
    FQuat TargetRotation = AimBowRotation.Quaternion();
    const FVector Axis = TargetRotation.RotateVector(ArrowAxis);
    const FVector RestFromAnchor = TargetRotation.RotateVector((ArrowRestCM - AimAnchor) * BowScale);
    const FVector TargetFromAnchor = FVector(FMath::Max(200.f, RangeCM), 0.f, 0.f) - TargetAnchor;
    const double Along = FVector::DotProduct(RestFromAnchor, Axis);
    const double Discriminant = FMath::Square(Along) + TargetFromAnchor.SizeSquared() - RestFromAnchor.SizeSquared();
    if (!Axis.IsNearlyZero() && Discriminant > 0.)
    {
        // Keep the physical pin on screen centre while the real arrow axis
        // converges on the same aiming ray. Moving only a HUD dot is insufficient.
        const FVector RayPoint = RestFromAnchor + Axis * (-Along + FMath::Sqrt(Discriminant));
        TargetRotation = (FQuat::FindBetweenNormals(RayPoint.GetSafeNormal(), TargetFromAnchor.GetSafeNormal())
            * TargetRotation).GetNormalized();
    }
    // Keep the short release kick after the aiming correction.
    TargetRotation = (FRotator(.3f * Kick, .06f * Kick, 0.f).Quaternion() * TargetRotation).GetNormalized();
    const FQuat AimRotation = (TargetRotation * Mount.GetRotation().Inverse()).GetNormalized();
    const FVector TargetGrip = TargetAnchor - TargetRotation.RotateVector(AimAnchor * BowScale);
    const FVector AimLocation = TargetGrip - AimRotation.RotateVector(Mount.GetLocation());
    const float Aim = AimAlpha();
    const FQuat Rotation = FQuat::Slerp(HipRotation, AimRotation, Aim).GetNormalized();
    // Interpolate the grip position as well as orientation, so the transition
    // rotates around the held bow instead of swinging it around the camera.
    const FVector AimGrip = AimRotation.RotateVector(GripLocation) + AimLocation;
    const FVector Location = FMath::Lerp(HipGrip, AimGrip, Aim) - Rotation.RotateVector(GripLocation);
    Pivot->SetRelativeTransform(FTransform(Rotation, Location));
}

void UBowWeaponComponent::UpdateBowGeometry()
{
    // 弓体部件是挂点：它的局部空间就是锚点空间，弦与弦上箭作为子部件自动跟随。
    auto* Riser = Part(SlotRiser);
    if (Riser)
    {
        if (bHasGripMarker && Viewmodel->IsVisible())
        {
            Riser->SetRelativeTransform(AnimatedRiserMount());
        }
        else
        {
            // 数据表是基准，两个 cvar 只做实机叠加对点（默认 0），不写回 JSON。
            FVector Offset = FVector::ZeroVector, RotationText = FVector::ZeroVector;
            ReadVector3Text(CVarBowLocation.GetValueOnGameThread(), Offset);
            ReadVector3Text(CVarBowRotation.GetValueOnGameThread(), RotationText);
            const FRotator RotationOffset(RotationText.X, RotationText.Y, RotationText.Z);
            Riser->SetMount(BowLocationCM + GripTrimCM + Offset, (BowRotation + RotationOffset).Clamp(), BowScale);
        }
        Riser->SetPartVisible(Riser->HasMesh());
    }
    for (const FName& Slot : SlotOrder)
        if (Slot != SlotRiser && Slot != SlotString && Slot != SlotArrow)
            if (auto* Attachment = Part(Slot)) Attachment->SetPartVisible(Attachment->HasMesh());
    const FVector Nock = NockPoint();
    FVector Upper = UpperTipCM, Lower = LowerTipCM;
    if (Riser)
    {
        const bool Loaded = IsDrawing() || Stage == EBowStage::LetDown || Stage == EBowStage::Release
            || (Stage == EBowStage::DrawEntry && bEntryNeedsArrow && ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < RingSeconds);
        Riser->ApplyStringLoad(Loaded ? Nock : BraceNockCM, BraceNockCM, FlexDistribution, .4f * ReleaseRing());
        Riser->FlexTips(Upper, Lower);
    }
    if (auto* BowString = Part(SlotString))
    {
        BowString->SetPartVisible(true);
        BowString->StretchRod(RodFor(SlotString, 0), Upper, Nock, StringRadiusCM);
        BowString->StretchRod(RodFor(SlotString, 1), Lower, Nock, StringRadiusCM);
    }
    if (auto* ArrowRest = Part(SlotArrow))
    {
        const bool bEntryNock = Stage == EBowStage::DrawEntry && bEntryNeedsArrow;
        const float TakePhase = bEntryNock ? Elapsed / DrawEntrySeconds : Elapsed / NockSeconds;
        const bool bTakingArrow = (Stage == EBowStage::Nocking || bEntryNock) && TakePhase >= .34f;
        const bool bVisibleArrow = (bArrowNocked || bTakingArrow);
        ArrowRest->SetPartVisible(bVisibleArrow);
        if (bVisibleArrow)
        {
            FVector Tail = Nock;
            FVector Axis = (ArrowRestCM - Tail).GetSafeNormal();
            if (bTakingArrow && bHasNockMarker && Viewmodel->IsVisible())
            {
                const FTransform Hand = Viewmodel->GetSocketTransform(TEXT("bow_nock"), RTS_Component) * Viewmodel->GetRelativeTransform();
                const FTransform Mount = AnimatedRiserMount();
                const FVector CarryTail = Mount.InverseTransformPosition(Hand.GetLocation());
                const bool bOrientedMarker = bEntryNock ? DrawEntryClip() != ClipDraw : bNockHasCarryAxis;
                const FVector CarryAxis = bOrientedMarker
                    ? Mount.InverseTransformVectorNoScale(Hand.GetRotation().GetForwardVector()).GetSafeNormal()
                    : (ArrowRestCM - CarryTail).GetSafeNormal();
                const float SeatPhase = bEntryNock ? .90f : NockContactFraction;
                const float Seat = FMath::SmoothStep(0.f, 1.f, (TakePhase - SeatPhase) / FMath::Max(.001f, 1.f - SeatPhase));
                Tail = FMath::Lerp(CarryTail, Nock, Seat);
                Axis = FMath::Lerp(CarryAxis, (ArrowRestCM - Tail).GetSafeNormal(), Seat).GetSafeNormal();
            }
            const FVector Tip = Tail + Axis * ArrowLengthCM;
            ArrowRest->StretchRod(RodFor(SlotArrow, 0), Tail, Tip, ArrowRadiusCM);
        }
    }
}

void UBowWeaponComponent::PlayClip(const TCHAR* Name, float Position, bool bLoop)
{
    UAnimSequence* Sequence = Animations.FindRef(FName(Name));
    if (!Sequence || !Viewmodel->GetSkeletalMeshAsset())
    {
        Viewmodel->SetVisibility(false);
        return;
    }
    const bool bLoadedCarry = bArrowNocked && bNockKeepsDrawPose;
    const bool bCarry = Stage == EBowStage::Ready;
    const float CarryWeight = bCarry ? GaitWeight * FMath::Lerp(1.f, .48f, CrouchProgress)
        * FMath::Lerp(1.f, .12f, AimAlpha()) : 0.f;
    Viewmodel->SetLocomotion(
        Animations.FindRef(bLoadedCarry ? TEXT("LoadedWalk") : TEXT("Walk")),
        Animations.FindRef(bLoadedCarry ? TEXT("LoadedRun") : TEXT("Run")),
        GaitPhase, CarryWeight, SprintBlend, bCarry && bLoadedCarry, BraceNockCM);
    // 与采集工具同一口径：只 PlayAnimation 一次，之后置零播放速率手动采样，
    // 否则每帧重新起播会让手臂停在片段开头。
    if (CurrentClip != Name)
    {
        // DrawEntry captured the exact start pose before its clock advanced.
        // Re-capturing here would restart the blend and miss the 0.2 s deadline.
        const bool bFromNockEntry = (Stage == EBowStage::Drawing || (Stage == EBowStage::Ready && bArrowNocked && bNockKeepsDrawPose)) &&
            (CurrentClip == TEXT("QuickNock") || CurrentClip == TEXT("ChainNock") || (CurrentClip == ClipNock && bNockKeepsDrawPose));
        if (!CurrentClip.IsNone() && !bFromNockEntry && Stage != EBowStage::DrawEntry && Stage != EBowStage::Nocking && Stage != EBowStage::LetDown)
        {
            if (Stage == EBowStage::Release)
            {
                Viewmodel->CaptureRelease(ReleaseSeconds + RecoverSeconds);
                Viewmodel->AdvanceEntry(Elapsed);
            }
            else if (Stage == EBowStage::Drawing && CurrentClip == TEXT("LoadedIdle"))
                Viewmodel->CaptureCarry(.10f);
            else Viewmodel->CaptureEntry(.12f);
        }
        Viewmodel->PlayAnimation(Sequence, false);
        Viewmodel->SetPlayRate(0.f);
        CurrentClip = Name;
        if (Stage == EBowStage::Release)
        {
            Viewmodel->SetPosition(0.f, false);
            Viewmodel->TickAnimation(0.f, false);
            Viewmodel->RefreshBoneTransforms();
        }
    }
    const float Length = Sequence->GetPlayLength();
    if (Length <= KINDA_SMALL_NUMBER) { Viewmodel->SetVisibility(false); return; }
    Viewmodel->SetPosition(bLoop ? FMath::Fmod(Position, Length) : FMath::Clamp(Position, 0.f, Length), false);
    Viewmodel->TickAnimation(0.f, false);
    Viewmodel->RefreshBoneTransforms();
    Viewmodel->SetVisibility(true);
}

float UBowWeaponComponent::ClipLength(const TCHAR* Name) const
{
    const UAnimSequence* Sequence = Animations.FindRef(FName(Name));
    return Sequence ? Sequence->GetPlayLength() : 0.f;
}

void UBowWeaponComponent::SampleArms()
{
    if (!bUsesArms) { Viewmodel->SetVisibility(false); return; }
    const auto Phase = [this](const TCHAR* Clip, float Fraction)
    { PlayClip(Clip, FMath::Clamp(Fraction, 0.f, 1.f) * ClipLength(Clip), false); };
    switch (Stage)
    {
    case EBowStage::Equip:
        Phase(TEXT("Equip"), Elapsed / EquipSeconds); break;
    case EBowStage::Nocking:
        Phase(ClipNock, Elapsed / NockSeconds); break;
    case EBowStage::DrawEntry:
        if (const TCHAR* Entry = DrawEntryClip(); Entry != ClipDraw) Phase(Entry, Elapsed / DrawEntrySeconds);
        else Phase(ClipDraw, 0.f);
        break;
    case EBowStage::Drawing:
        Phase(ClipDraw, Elapsed / DrawSeconds); break;
    case EBowStage::LetDown:
        Phase(ClipDraw, LetDownPhase * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds))); break;
    case EBowStage::Holding:
        if (ClipLength(ClipHold) > 0.f) PlayClip(ClipHold, HoldElapsed, true);
        else Phase(ClipDraw, 1.f);
        break;
    case EBowStage::Release:
        Phase(ClipRelease, Elapsed / (ReleaseSeconds + RecoverSeconds)); break;
    case EBowStage::Recover:
        Phase(ClipRelease, (ReleaseSeconds + Elapsed) / (ReleaseSeconds + RecoverSeconds)); break;
    default:
        if (bArrowNocked && bNockKeepsDrawPose)
        {
            if (ClipLength(TEXT("LoadedIdle")) > 0.f) PlayClip(TEXT("LoadedIdle"), VisualTime, true);
            else Phase(ClipDraw, 0.f);
        }
        else if (ClipLength(TEXT("Walk")) <= 0.f && !bArrowNocked && Character.IsValid() && Character->IsSprinting())
            PlayClip(TEXT("Run"), VisualTime, true);
        else PlayClip(bArrowNocked ? TEXT("Ready") : ClipIdle, VisualTime, true);
        break;
    }
}

void UBowWeaponComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    const bool Usable = IsEquipped() && CanUse();
    if (!Usable)
    {
        if (Stage != EBowStage::Stowed) CancelAction();
        for (auto& Pair : Parts) if (Pair.Value) Pair.Value->SetPartVisible(false);
        Viewmodel->SetVisibility(false);
    }
    else
    {
        // Publish this frame's arms before querying grip/nock sockets. The
        // equip lift belongs to Equip, never to every newly entered stage.
        SampleArms();
        UpdatePoseLayers();
        UpdateBowGeometry();
    }
    FeedbackSeconds = FMath::Max(0.f, FeedbackSeconds - Delta);
    HintCountdown -= Delta;
    if (HintCountdown <= 0.f)
    {
        HintCountdown = .15f;
        UpdateHint();
    }
}

FString UBowWeaponComponent::StatusLine() const
{
    const UEnum* Enum = StaticEnum<EBowStage>();
    return FString::Printf(TEXT("%s · 拉距 %d%% · 弦上 %s · 箭袋 %d · %s"),
        *DisplayName,
        FMath::FloorToInt(DrawFraction() * 100.f),
        bArrowNocked ? TEXT("有箭") : TEXT("空"),
        ArrowsInPouch(),
        Enum ? *Enum->GetNameStringByValue(static_cast<int64>(Stage)) : TEXT("?"));
}

void UBowWeaponComponent::ShowFeedback(const FString& Message)
{
    Feedback = Message;
    FeedbackSeconds = 2.5f;
}

void UBowWeaponComponent::UpdateHint()
{
    const auto* Pawn = Character.Get();
    auto* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    if (!PC) return;
    if (!Prompt)
    {
        Prompt = CreateWidget<UColdSteelPickupPrompt>(PC, UColdSteelPickupPrompt::StaticClass());
        Prompt->AddToViewport(25);
        Prompt->SetAlignmentInViewport(FVector2D(.5f, .5f));
    }
    const bool Show = IsEquipped() && CanUse() && FeedbackSeconds > 0.f;
    Prompt->SetVisibility(Show ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    if (!Show) return;
    int32 X = 0, Y = 0;
    PC->GetViewportSize(X, Y);
    Prompt->SetPositionInViewport(FVector2D(X * .5f, Y * .74f), true);
    Prompt->SetCaption(FeedbackSeconds > 0.f ? Feedback : StatusLine());
}
