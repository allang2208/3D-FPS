#include "BowWeaponComponent.h"
#include "BowArrow.h"
#include "BowArmsMeshComponent.h"
#include "BowPartComponent.h"
#include "../WeaponStatEvaluation.h"
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
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Sound/SoundBase.h"

namespace
{
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
const TCHAR* UBowWeaponComponent::SlotArrowRest = TEXT("arrow_rest");

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
        if (Slots.IsEmpty()) Slots = { FName(TEXT("riser")), FName(TEXT("string")), FName(TEXT("arrow_rest")) };
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
    MakePart(SlotArrowRest, Riser, 1);

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
    const uint32 DataHash = Item ? GetTypeHash(Item->Data) : 0u;
    if (NewId == InstanceId && DataHash == EquippedDataHash) return;
    // 同一实例、资源集合没变（只改数值或部件参数）：保留已加载视模，只重算，手上不闪帧。
    // 改造系统换的是部件网格时签名会变，才走下面的重新加载。
    const FString NewSignature = Item ? PresentationSignature(Item) : FString();
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
    CurrentClip = NAME_None;
    bUsesArms = false;
    bPresentationReady = false;
    bHasGripMarker = bHasNockMarker = false;
    bHasRightHandBone = false;
    bArrowNocked = false;
    VisualTime = 0.f;
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
    ArrowId = ColdSteelInventory::Text(*Item, TEXT("arrow_ammo"));
    if (ArrowId.IsEmpty()) ArrowId = TEXT("arrow_wood");

    // 部件表先定下来（槽名、细杆条数、半径），再收集各槽资源做一次异步加载。
    ApplyParts(Item);
    const FSoftObjectPath ArmsPath(ColdSteelInventory::Text(*Item, TEXT("bow_viewmodel")));
    const FSoftObjectPath HeadPath(ColdSteelInventory::Text(*Item, TEXT("arrow_head_mesh")));
    const FString Prefix = ColdSteelInventory::Text(*Item, TEXT("bow_animation_prefix"));
    bUsesArms = !ArmsPath.IsNull();
    TArray<FSoftObjectPath> Paths;
    for (const auto& Pair : PendingPartMeshes) if (!Pair.Value.IsNull()) Paths.Add(Pair.Value);
    for (const auto& Pair : PendingPartMaterials) if (!Pair.Value.IsNull()) Paths.Add(Pair.Value);
    if (bUsesArms)
    {
        Paths.Add(ArmsPath);
        for (const TCHAR* Clip : { ClipIdle, ClipDraw, ClipHold, ClipRelease, ClipNock, TEXT("Ready"), TEXT("Equip"), TEXT("Run") })
            Paths.Add(BowAssetPath(Prefix, Clip));
    }
    if (!HeadPath.IsNull()) Paths.Add(HeadPath);
    for (const TCHAR* Key : { TEXT("bow_draw_sound"), TEXT("bow_release_sound"), TEXT("bow_nock_sound") })
    {
        const FSoftObjectPath Sound(ColdSteelInventory::Text(*Item, Key));
        if (!Sound.IsNull()) Paths.Add(Sound);
    }
    LoadHandle = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this, [this, Prefix, ArmsPath, HeadPath, NewId, NewSignature]()
        {
            auto* LiveProfile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            const auto* Item = LiveProfile ? LiveProfile->ActiveBow() : nullptr;
            if (!Item || Item->InstanceId != NewId || InstanceId != NewId || EquippedSignature != NewSignature) return;
            // 每个部件自己认领网格与材质覆盖：换弓臂／换弦／换箭台都只是改数据键。
            for (const auto& Pair : Parts)
            {
                UBowPartComponent* Component = Pair.Value;
                if (!Component) continue;
                Component->SetMesh(Cast<UStaticMesh>(PendingPartMeshes.FindRef(Pair.Key).ResolveObject()));
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
            }
            DrawSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_draw_sound"))).ResolveObject());
            ReleaseSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_release_sound"))).ResolveObject());
            NockSound = Cast<USoundBase>(FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("bow_nock_sound"))).ResolveObject());
            auto* Riser = Part(SlotRiser);
            const bool bReady = Riser && Riser->GetMesh() && (!bUsesArms ||
                (Viewmodel->GetSkeletalMeshAsset() && Animations.FindRef(ClipIdle) && Animations.FindRef(ClipDraw)
                 && Animations.FindRef(ClipNock) && Animations.FindRef(ClipRelease)));
            bPresentationReady = bReady;
            Feedback = bReady ? TEXT("弓 · 左键搭箭并拉开，松手发射 · 右键稳持 · G／滚轮切换武器")
                              : TEXT("弓模型未加载完成，重新装备试试");
            FeedbackSeconds = 3.f;
            if (bReady) SetStage(EBowStage::Equip, EquipSeconds);
        }));
}

void UBowWeaponComponent::ApplyNumbers(const FColdSteelItem* Item)
{
    auto Number = [&](const TCHAR* Key, float Default)
    { return static_cast<float>(ColdSteelInventory::Number(*Item, Key, Default)); };
    NockSeconds = FMath::Max(.12f, Number(TEXT("nock_seconds"), .68f));
    const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    DrawSeconds = FMath::Max(.3f, float(ColdSteelWeaponStats::Interval(Item, Profile, Number(TEXT("draw_seconds"), 1.4f))));
    HoldSeconds = FMath::Max(0.f, Number(TEXT("hold_seconds"), 2.2f));
    ReleaseSeconds = FMath::Max(.08f, Number(TEXT("release_seconds"), .3f));
    RecoverSeconds = FMath::Max(.08f, Number(TEXT("recover_seconds"), .34f));
    EquipSeconds = FMath::Max(.1f, Number(TEXT("equip_seconds"), .45f));
    NockContactFraction = FMath::Clamp(Number(TEXT("nock_contact_fraction"), .82f), 0.f, 1.f);
    DrawCurve.Reset();
    TArray<FString> CurveText;
    ColdSteelInventory::Text(*Item, TEXT("draw_curve")).ParseIntoArray(CurveText, TEXT(","), true);
    for (const FString& Value : CurveText) DrawCurve.Add(FMath::Clamp(FCString::Atof(*Value), 0.f, 1.f));
    FullDamage = Number(TEXT("full_damage"), 46.f);
    MinDamageRatio = FMath::Clamp(Number(TEXT("min_damage_ratio"), .25f), 0.f, 1.f);
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
    SwayAmplitudeCM = Number(TEXT("sway_amplitude_cm"), SwayAmplitudeCM);
    SteadySwayScale = FMath::Clamp(Number(TEXT("steady_sway_scale"), SteadySwayScale), 0.f, 1.f);
    ReadVector3(Item, TEXT("nock_upper_cm"), UpperTipCM);
    ReadVector3(Item, TEXT("nock_lower_cm"), LowerTipCM);
    ReadVector3(Item, TEXT("brace_nock_cm"), BraceNockCM);
    ReadVector3(Item, TEXT("draw_anchor_cm"), DrawAnchorCM);
    ReadVector3(Item, TEXT("arrow_rest_cm"), ArrowRestCM);
    ReadVector3(Item, TEXT("bow_location_cm"), BowLocationCM);
    ReadVector3(Item, TEXT("bow_grip_trim_cm"), GripTrimCM);
    FVector Rotation;
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

FString UBowWeaponComponent::PresentationSignature(const FColdSteelItem* Item) const
{
    FString Text = ColdSteelInventory::Text(*Item, TEXT("bow_viewmodel")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("bow_animation_prefix")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_head_mesh")) + TEXT("|")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_ammo")) + TEXT("|");
    for (const FName& Slot : BowSlotNames(ColdSteelInventory::Text(*Item, TEXT("bow_part_slots"))))
    {
        Text += Slot.ToString() + TEXT("=") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("mesh")))
            + TEXT("/") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("material")))
            + TEXT("/") + ColdSteelInventory::Text(*Item, *PartKey(Slot, TEXT("hide_slot"))) + TEXT(";");
    }
    // 旧平铺键也进签名：还没写部件键的表，改 `bow_mesh` 同样能触发表现代码的重载。
    Text += ColdSteelInventory::Text(*Item, TEXT("bow_mesh")) + TEXT("/")
        + ColdSteelInventory::Text(*Item, TEXT("arrow_mesh"));
    for (const TCHAR* Key : { TEXT("bow_draw_sound"), TEXT("bow_release_sound"), TEXT("bow_nock_sound"), TEXT("bow_string_hidden_material") })
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
            else if (Slot == SlotArrowRest) Mesh = FSoftObjectPath(ColdSteelInventory::Text(*Item, TEXT("arrow_mesh")));
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
            Slot == SlotString ? 2.f : Slot == SlotArrowRest ? 1.f : 0.f)));
        while (Component->RodCount() < Rods) RodFor(Slot, Component->RodCount());
    }
    // 细杆粗细同样两键并存：新键优先，旧平铺键兜底。
    StringRadiusCM = Number(*PartKey(SlotString, TEXT("radius_cm")), StringRadiusCM);
    ArrowRadiusCM = Number(*PartKey(SlotArrowRest, TEXT("radius_cm")), ArrowRadiusCM);
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

bool UBowWeaponComponent::ConsumeArrowFromPouch(FString& Reason)
{
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return false;
    auto* Pawn = Character.Get();
    // 开发面板的"无限备弹"按弹种生效：arrow_wood 在 ammo_types.json 里允许无限，
    // 于是发射不扣箭袋，与枪械无限备弹同一口径。
    if (Pawn && Pawn->HasInfiniteReserveAmmoFor(ArrowId)) return true;
    if (Profile->PouchCount(ArrowId) > 0 && Profile->SpendAmmo(ArrowId, 1)) return true;
    // 旧存档或开发发放可能把箭记成普通物品：同一 id 再走一次物品消耗，不重复扣。
    FString ItemReason;
    if (Profile->ConsumeItem(ArrowId, 1, ItemReason)) return true;
    Reason = FString::Printf(TEXT("箭袋里没有%s"), *Profile->AmmoLabel(ArrowId));
    return false;
}

void UBowWeaponComponent::SetStage(EBowStage Next, float Seconds)
{
    if (Next == EBowStage::Drawing)
        if (const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            if (const auto* Item = Profile->ActiveBow())
                DrawSeconds = FMath::Max(.3f, float(ColdSteelWeaponStats::Interval(Item, Profile,
                    ColdSteelInventory::Number(*Item, TEXT("draw_seconds"), 1.4))));
    Stage = Next;
    StageSeconds = Seconds;
    Elapsed = 0.f;
    HoldElapsed = 0.f;
    bDrawSoundPlayed = false;
    bNockSoundPlayed = false;
}

void UBowWeaponComponent::BeginNock()
{
    if (!IsEquipped() || !CanUse()) return;
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
}

void UBowWeaponComponent::BeginPrimaryAttack()
{
    if (!IsEquipped() || !CanUse()) return;
    if (Character.IsValid() && Character->IsCastBlockingLeftHandAction()) return;
    switch (Stage)
    {
    case EBowStage::Ready:
        // 左键按住时"搭箭→拉开"是一次动作：Nocking 走完由 bTriggerHeld 决定是否续上拉弓。
        if (bArrowNocked) SetStage(EBowStage::Drawing, 0.f);
        else BeginNock();
        return;
    case EBowStage::Nocking:
        return;                          // 搭箭进行中不接第二下，避免抢拍
    case EBowStage::Drawing:
    case EBowStage::Holding:
        return;                          // 已经拉开：等真实释放
    default:
        return;                          // 装备／放弦／回收期间吞掉输入
    }
}

void UBowWeaponComponent::ReleasePrimaryAttack()
{
    if (!IsEquipped() || !CanUse()) { CancelAction(); return; }
    if (Stage != EBowStage::Drawing && Stage != EBowStage::Holding) return;
    // 输入释放或满拉力竭发射；菜单／翻越等打断走 CancelAction，不放箭。
    ReleaseRatio = DrawFraction();
    SampleArms();
    UpdateBowGeometry();
    ReleasedNockCM = NockPoint();
    if (LooseArrow(ReleaseRatio)) SetStage(EBowStage::Release, ReleaseSeconds);
    else SetStage(EBowStage::Ready, 0.f);
}

void UBowWeaponComponent::CancelAction()
{
    bTriggerHeld = bSteadyHeld = false;
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
    auto* Riser = Part(SlotRiser);
    if (Stage == EBowStage::Release)
    {
        const float T = FMath::Clamp(Elapsed / .075f, 0.f, 1.f);
        return FMath::Lerp(ReleasedNockCM, BraceNockCM, FMath::SmoothStep(0.f, 1.f, T));
    }
    if (!IsDrawing() && !(Stage == EBowStage::Ready && bArrowNocked)) return BraceNockCM;
    if (bUsesArms && bHasNockMarker && Viewmodel && Viewmodel->IsVisible() && Riser)
        return Riser->GetComponentTransform().InverseTransformPosition(Viewmodel->GetSocketLocation(TEXT("bow_nock")));
    return FMath::Lerp(BraceNockCM, DrawAnchorCM, DrawFraction());
}

FVector UBowWeaponComponent::ArrowTipPoint() const
{
    // 箭尾落在弦结点，箭轴穿过箭台，沿弓体局部 +X 越过握把。
    const FVector Nock = NockPoint();
    return Nock + (ArrowRestCM - Nock).GetSafeNormal() * ArrowLengthCM;
}

bool UBowWeaponComponent::LooseArrow(float Ratio)
{
    auto* Pawn = Character.Get();
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Pawn || !Camera || !Profile || !bArrowNocked) return false;
    const float Clamped = FMath::Clamp(Ratio, 0.f, 1.f);
    const float Cost = FMath::Max(0.f, StaminaCost * FMath::Lerp(.4f, 1.f, Clamped));
    if (!Profile->CanSpendStamina(Cost)) { ShowFeedback(TEXT("体力不足，已收弓")); return false; }
    const float Speed = FullSpeedCM * FMath::Lerp(MinSpeedRatio, 1.f, Clamped);
    // 从实际箭尖发射并朝准星落点收敛；近墙时另做相机到箭尖的阻挡扫掠。
    auto* Riser = Part(SlotRiser);
    auto* ArrowRest = Part(SlotArrowRest);
    const FVector Muzzle = Riser ? Riser->GetComponentTransform().TransformPosition(ArrowTipPoint())
                                 : Camera->GetComponentLocation();
    FHitResult AimHit;
    const FVector CameraOrigin = Camera->GetComponentLocation();
    const FVector FarAim = CameraOrigin + Camera->GetForwardVector() * RangeCM;
    FCollisionQueryParams AimQuery(SCENE_QUERY_STAT(BowAim), true, Pawn);
    const bool bHitAim = GetWorld()->LineTraceSingleByChannel(AimHit, CameraOrigin, FarAim, ECC_Visibility, AimQuery);
    const FVector AimPoint = bHitAim ? AimHit.ImpactPoint : FarAim;
    const FVector AimVector = AimPoint - Muzzle;
    const FRotator Direction = (FVector::DotProduct(AimVector, Camera->GetForwardVector()) > 0.f
        ? AimVector : Camera->GetForwardVector()).Rotation();
    FActorSpawnParameters Spawn;
    Spawn.Owner = Pawn;
    Spawn.Instigator = Pawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Arrow = GetWorld()->SpawnActor<ABowArrow>(Muzzle, Direction, Spawn))
    {
        FString Reason;
        if (!ConsumeArrowFromPouch(Reason)) { Arrow->Destroy(); bArrowNocked = false; ShowFeedback(Reason); return false; }
        // 射击瞬间的修炼／符文快照与弹道组件同源；弓自己的暴击与破韧只在配了值时覆盖。
        FColdSteelSkillShot Shot = ColdSteelSkills::Snapshot(Pawn, Profile ? Profile->ActiveBow() : nullptr, true);
        const auto* Item = Profile->ActiveBow();
        const float BaseDamage = Shot.DamagePanel.Total() > 0.f ? Shot.DamagePanel.Total() : FullDamage;
        const float Damage = BaseDamage * FMath::Lerp(MinDamageRatio, 1.f, Clamped)
            * (Item ? Profile->AmmoDamageMultiplier(*Item) : 1.f);
        if (CriticalChance >= 0.f) Shot.CriticalChance = FMath::Max(Shot.CriticalChance, CriticalChance);
        if (ToughnessMultiplier > 0.f) Shot.ToughnessDamageMultiplier = ToughnessMultiplier;
        // 箭模取自 arrow_rest 部件：改造系统换箭台／箭杆网格，弦上与飞行中的箭一起跟着变。
        Arrow->Configure(Damage, Speed, GravityCM, RangeCM, Shot,
                         ArrowRest ? ArrowRest->GetMesh() : nullptr,
                         ArrowHeadMesh ? ArrowHeadMesh.Get() : nullptr,
                         ArrowRadiusCM, ArrowLengthCM, ArrowId);
        Arrow->ResolveLaunchObstruction(CameraOrigin);
    }
    else return false;
    bArrowNocked = false;
    ReleaseKick = FMath::Lerp(.25f, 1.f, Clamped);
    if (ReleaseSound) UGameplayStatics::PlaySound2D(this, ReleaseSound, .6f, 1.f + .06f * Clamped);
    Profile->SpendStamina(Cost);
    return true;
}

void UBowWeaponComponent::AdvanceActionBeforeCamera(float Delta)
{
    if (!IsEquipped()) return;
    if (!CanUse())
    {
        CancelAction();
        return;
    }
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
    case EBowStage::Nocking:
        if (!bNockSoundPlayed && Elapsed >= NockSeconds * NockContactFraction)
        {
            bNockSoundPlayed = true;
            if (NockSound) UGameplayStatics::PlaySound2D(this, NockSound, .5f);
        }
        // 搭箭完成：左键仍按着就顺势开始拉弓，否则停在已上弦的 Ready。
        if (Elapsed >= StageSeconds)
        {
            bArrowNocked = true;
            SetStage(EBowStage::Ready, 0.f);
            if (bTriggerHeld) SetStage(EBowStage::Drawing, 0.f);
        }
        break;
    case EBowStage::Drawing:
        if (!bDrawSoundPlayed && Elapsed > .08f)
        {
            bDrawSoundPlayed = true;
            if (DrawSound) UGameplayStatics::PlaySound2D(this, DrawSound, .42f);
        }
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
    default:
        break;
    }
}

void UBowWeaponComponent::GetCameraMotion(FVector& Location, FRotator& Rotation) const
{
    Location = FVector::ZeroVector;
    Rotation = FRotator::ZeroRotator;
    if (!IsEquipped() || Elapsed < 0.f) return;
    const float Scale = FMath::Max(0.f, CVarBowSway.GetValueOnGameThread());
    const float Ratio = DrawFraction();
    // 拉弓把手上的弓往后带：位移沿相机 -X，与拉距同步；释放瞬间给一次小幅回弹。
    const float Kick = Stage == EBowStage::Release ? ReleaseKick * FMath::Exp(-18.f * Elapsed) : 0.f;
    Location += FVector(-3.2f * Ratio + 1.6f * Kick, 0.f, 0.f) * Scale;
    Rotation.Pitch += (-.5f * Ratio + 1.1f * Kick) * Scale;
    Rotation.Roll += .8f * Ratio * Scale;
    if (Stage == EBowStage::Holding)
    {
        // 满拉保持的呼吸抖动随保持时长上升；右键稳持把幅度压到配置比例。
        const float Grow = FMath::Clamp(HoldElapsed / FMath::Max(.2f, HoldSeconds), 0.f, 1.f);
        const float Amplitude = SwayAmplitudeCM * (.35f + .65f * Grow)
            * (bSteadyHeld ? SteadySwayScale : 1.f) * Scale;
        Rotation.Yaw += FMath::Sin(VisualTime * 1.05f) * Amplitude * .12f;
        Rotation.Pitch += FMath::Sin(VisualTime * .73f + 1.1f) * Amplitude * .1f;
    }
}

void UBowWeaponComponent::UpdateBowGeometry()
{
    // 数据表是基准，两个 cvar 只做实机叠加对点（默认 0），不写回 JSON。
    FVector Offset = FVector::ZeroVector;
    ReadVector3Text(CVarBowLocation.GetValueOnGameThread(), Offset);
    FVector RotationText;
    FRotator RotationOffset = FRotator::ZeroRotator;
    if (ReadVector3Text(CVarBowRotation.GetValueOnGameThread(), RotationText))
        RotationOffset = FRotator(RotationText.X, RotationText.Y, RotationText.Z);
    // 弓体部件是挂点：它的局部空间就是锚点空间，弦与弦上箭作为子部件自动跟随。
    auto* Riser = Part(SlotRiser);
    if (Riser)
    {
        if (bHasGripMarker && Viewmodel->IsVisible())
        {
            FTransform Mount = Viewmodel->GetSocketTransform(TEXT("bow_grip"), RTS_World).GetRelativeTransform(Pivot->GetComponentTransform());
            Mount.SetScale3D(FVector(BowScale));
            Mount.AddToTranslation(GripTrimCM + Offset);
            Mount.SetRotation((RotationOffset.Quaternion() * Mount.GetRotation()).GetNormalized());
            Riser->SetRelativeTransform(Mount);
        }
        else Riser->SetMount(BowLocationCM + GripTrimCM + Offset, (BowRotation + RotationOffset).Clamp(), BowScale);
        Riser->SetPartVisible(Riser->GetMesh() != nullptr);
    }
    const FVector Nock = NockPoint();
    if (auto* BowString = Part(SlotString))
    {
        BowString->SetPartVisible(true);
        BowString->StretchRod(RodFor(SlotString, 0), UpperTipCM, Nock, StringRadiusCM);
        BowString->StretchRod(RodFor(SlotString, 1), LowerTipCM, Nock, StringRadiusCM);
    }
    if (auto* ArrowRest = Part(SlotArrowRest))
    {
        const bool bTakingArrow = Stage == EBowStage::Nocking && Elapsed >= NockSeconds * .34f;
        const bool bVisibleArrow = bArrowNocked || bTakingArrow;
        ArrowRest->SetPartVisible(bVisibleArrow);
        if (bVisibleArrow)
        {
            FVector Tail = Nock;
            if (bTakingArrow && bHasNockMarker && Viewmodel->IsVisible() && Riser)
                Tail = Riser->GetComponentTransform().InverseTransformPosition(Viewmodel->GetSocketLocation(TEXT("bow_nock")));
            const FVector Tip = Tail + (ArrowRestCM - Tail).GetSafeNormal() * ArrowLengthCM;
            ArrowRest->StretchRod(RodFor(SlotArrowRest, 0), Tail, Tip, ArrowRadiusCM);
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
    // 与采集工具同一口径：只 PlayAnimation 一次，之后置零播放速率手动采样，
    // 否则每帧重新起播会让手臂停在片段开头。
    if (CurrentClip != Name)
    {
        if (!CurrentClip.IsNone()) Viewmodel->CaptureEntry(Stage == EBowStage::Release ? .10f : .12f);
        Viewmodel->PlayAnimation(Sequence, false);
        Viewmodel->SetPlayRate(0.f);
        CurrentClip = Name;
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
    case EBowStage::Drawing:
        Phase(ClipDraw, Elapsed / DrawSeconds); break;
    case EBowStage::Holding:
        if (ClipLength(ClipHold) > 0.f) PlayClip(ClipHold, HoldElapsed, true);
        else Phase(ClipDraw, 1.f);
        break;
    case EBowStage::Release:
        Phase(ClipRelease, Elapsed / (ReleaseSeconds + RecoverSeconds)); break;
    case EBowStage::Recover:
        Phase(ClipRelease, (ReleaseSeconds + Elapsed) / (ReleaseSeconds + RecoverSeconds)); break;
    default:
        if (!bArrowNocked && Character.IsValid() && Character->IsSprinting()) PlayClip(TEXT("Run"), VisualTime, true);
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
    return FString::Printf(TEXT("%s · 拉距 %.0f%% · 弦上 %s · 箭袋 %d · %s"),
        *DisplayName,
        DrawFraction() * 100.f,
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
