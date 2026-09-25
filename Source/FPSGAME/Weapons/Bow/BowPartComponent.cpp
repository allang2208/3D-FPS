#include "BowPartComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

namespace
{
    /** 视模通用口径：不碰撞、不投影、只本人可见。 */
    void ConfigureViewmodelPiece(UStaticMeshComponent* Piece, UStaticMesh* Mesh)
    {
        Piece->SetStaticMesh(Mesh);
        Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Piece->SetCanEverAffectNavigation(false);
        Piece->SetCastShadow(false);
        Piece->SetOnlyOwnerSee(true);
        Piece->SetVisibility(false);
    }

    /**
     * 细杆摆放：占位圆柱（轴向 +Z、长 100、半径 50）按半径与长度拉伸；
     * 正式网格按自身包围盒取轴与长度，粗细保持作者尺寸，
     * 否则 76 cm 的箭会被压成拉距的一半。
     */
    void PlaceRod(UStaticMeshComponent* Rod, UStaticMesh* Placeholder, const FVector& From, const FVector& To, float RadiusCM)
    {
        const FVector Delta = To - From;
        const float Length = Delta.Size();
        if (Length <= KINDA_SMALL_NUMBER)
        {
            Rod->SetVisibility(false);
            return;
        }
        UStaticMesh* Mesh = Rod->GetStaticMesh();
        const bool bPlaceholder = !Mesh || Mesh == Placeholder;
        const bool bAlongX = !bPlaceholder && Mesh->GetBounds().BoxExtent.X > Mesh->GetBounds().BoxExtent.Z;
        const FVector Axis = bAlongX ? FVector::XAxisVector : FVector::ZAxisVector;
        const float Authored = bPlaceholder ? 100.f
            : (bAlongX ? Mesh->GetBounds().BoxExtent.X : Mesh->GetBounds().BoxExtent.Z) * 2.f;
        const float Thickness = bPlaceholder ? FMath::Max(.01f, RadiusCM) / 50.f : 1.f;
        const float LongScale = Authored > KINDA_SMALL_NUMBER ? Length / Authored : Length / 100.f;
        const FVector Scale = bAlongX ? FVector(LongScale, Thickness, Thickness)
                                     : FVector(Thickness, Thickness, LongScale);
        const FQuat Rotation = FQuat::FindBetweenNormals(Axis, Delta.GetSafeNormal());
        // Preserve the authored shaft axis: asymmetric fletching must not shift
        // the nock away from the string merely because its bounds are off-centre.
        const FVector Centre = Mesh ? Axis * FVector::DotProduct(Mesh->GetBounds().Origin, Axis) : FVector::ZeroVector;
        Rod->SetRelativeLocation((From + To) * .5f - Rotation.RotateVector(Centre * Scale));
        Rod->SetRelativeRotation(Rotation);
        Rod->SetRelativeScale3D(Scale);
        Rod->SetVisibility(true);
    }
}

void UBowPartComponent::InitializeAsPart(AActor* Owner, const FName& InSlot, USceneComponent* Parent)
{
    if (!Owner)
    {
        UE_LOG(LogTemp, Warning, TEXT("弓部件 %s 初始化时缺 Owner"), *InSlot.ToString());
        return;
    }
    SlotName = InSlot;
    Owner->AddInstanceComponent(this);
    if (Parent) SetupAttachment(Parent);
    RodMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    // 先注册挂点，再建实体子件：子件挂在已注册的父件上才拿得到正确的世界变换。
    RegisterComponent();
    if (!Visual)
    {
        Visual = NewObject<UStaticMeshComponent>(Owner,
            *FString::Printf(TEXT("%sMesh"), *InSlot.ToString()));
        Owner->AddInstanceComponent(Visual);
        Visual->SetupAttachment(this);
        Visual->RegisterComponent();
    }
    ConfigureViewmodelPiece(Visual, RodMesh);
    SetPartVisible(false);
}

void UBowPartComponent::SetMesh(UStaticMesh* Mesh)
{
    PartMesh = Mesh;
    if (Visual)
    {
        Visual->EmptyOverrideMaterials();
        Visual->SetStaticMesh(Mesh);
        Visual->SetVisibility(bPartVisible && Mesh && Rods.IsEmpty());
    }
    for (const auto& Rod : Rods) if (Rod) Rod->EmptyOverrideMaterials();
}

int32 UBowPartComponent::AddRod(const TCHAR* Label)
{
    AActor* Owner = GetOwner();
    if (!Owner) return INDEX_NONE;
    auto* Rod = NewObject<UStaticMeshComponent>(Owner, Label);
    Owner->AddInstanceComponent(Rod);
    Rod->SetupAttachment(this);
    ConfigureViewmodelPiece(Rod, RodMesh);
    Rod->RegisterComponent();
    if (Visual) Visual->SetVisibility(false);
    return Rods.Add(Rod);
}

void UBowPartComponent::StretchRod(int32 Index, const FVector& From, const FVector& To, float RadiusCM)
{
    auto* Rod = Rods.IsValidIndex(Index) ? Rods[Index].Get() : nullptr;
    if (!Rod) return;
    if (!bPartVisible)
    {
        Rod->SetVisibility(false);
        return;
    }
    // 一个槽只有一个网格来源：细杆用本部件的网格，没给就退回占位圆柱。
    UStaticMesh* Wanted = PartMesh ? PartMesh.Get() : RodMesh.Get();
    if (Rod->GetStaticMesh() != Wanted) Rod->SetStaticMesh(Wanted);
    PlaceRod(Rod, RodMesh, From, To, RadiusCM);
}

void UBowPartComponent::SetPartVisible(bool bInVisible)
{
    bPartVisible = bInVisible;
    // 子件跟着父挂点走：这里只切部件本身，细杆的可见性由 StretchRod 自己按长度判定。
    SetVisibility(bInVisible);
    if (Visual) Visual->SetVisibility(bInVisible && PartMesh && Rods.IsEmpty());
    if (!bInVisible) for (const auto& Rod : Rods) if (Rod) Rod->SetVisibility(false);
}

void UBowPartComponent::SetMount(const FVector& Location, const FRotator& Rotation, float Scale)
{
    SetRelativeLocation(Location);
    SetRelativeRotation(Rotation.Clamp());
    SetRelativeScale3D(FVector(Scale));
}

int32 UBowPartComponent::FindMaterialSlot(const FString& InSlotName) const
{
    UStaticMesh* Mesh = GetMesh();
    if (InSlotName.IsEmpty()) return 0;
    if (!Mesh) return INDEX_NONE;
    if (InSlotName.IsNumeric()) return FCString::Atoi(*InSlotName);
    return Mesh->GetMaterialIndex(FName(*InSlotName));
}

bool UBowPartComponent::SetMaterialOverride(const FString& InSlotName, UMaterialInterface* Material)
{
    if (!Visual || !Material) return false;
    const int32 Index = FindMaterialSlot(InSlotName);
    if (Index == INDEX_NONE) return false;
    Visual->SetMaterial(Index, Material);
    for (const auto& Rod : Rods) if (Rod) Rod->SetMaterial(Index, Material);
    return true;
}
