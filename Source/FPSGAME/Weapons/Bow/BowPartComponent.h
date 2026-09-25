// 弓的一个可替换部件：一个挂点 + 一个实体网格 + 若干条程序化细杆。
// 拆出来的目的是给改造系统留口：按槽名换网格／换材质／调可见性，
// 不需要动 `UBowWeaponComponent` 的状态机、弹道与输入。
#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "BowPartComponent.generated.h"

class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * 部件的挂点就是它自己（`USceneComponent`），实体网格与细杆都是它的子件。
 * 因此"弓的局部坐标"＝ `Riser` 部件的坐标空间：锚点跟着部件走，
 * 换网格、换缩放都不会让锚点跑偏。
 *
 * 三种用法（同一类，靠数据区分，改造系统只认槽名）：
 *   riser      —— 只有实体网格（`SetMesh`），弓体本身；
 *   string     —— 两条细杆（上／下弓梢到弦结点），本包的弦是烘进网格的直线，
 *                 运行时得自己张合；换成真正的弦模型时只填 `SetMesh` 即可；
 *   arrow_rest —— 一条细杆当弦上箭，正式箭模同样走 `SetMesh`。
 */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UBowPartComponent : public USceneComponent
{
    GENERATED_BODY()

public:
    /** 槽名（riser / string / arrow_rest …），改造系统按它寻址；与 bows.json 的部件表同名。 */
    UPROPERTY(EditAnywhere, Category="Bow")
    FName SlotName;

    /** 由宿主组件创建后调用：登记到 Owner、挂到父件、建好实体子件并注册。 */
    void InitializeAsPart(AActor* Owner, const FName& InSlot, USceneComponent* Parent);

    /**
     * 部件的网格，一个槽只有一个网格来源：
     * 细杆数为 0 时它挂在实体子件上（弓体、真正的弦模型）；
     * 有细杆时它同时是细杆的素材（弦上箭），为空则回落引擎圆柱占位。
     */
    void SetMesh(UStaticMesh* Mesh);
    UStaticMesh* GetMesh() const { return PartMesh; }

    /** 加一条程序化细杆，返回句柄（`StretchRod` 用）。条数由数据表 `bow_part_<槽名>_rods` 决定。 */
    int32 AddRod(const TCHAR* Label);
    /** 把第 Index 条细杆从 From 拉到 To（部件局部坐标，cm）。 */
    void StretchRod(int32 Index, const FVector& From, const FVector& To, float RadiusCM);

    void SetPartVisible(bool bInVisible);
    bool IsPartVisible() const { return bPartVisible; }
    void SetMount(const FVector& Location, const FRotator& Rotation, float Scale);

    /** 按材质槽名覆盖材质：把烘进网格的弦换成隐形材质就靠它，不改资产本身。 */
    bool SetMaterialOverride(const FString& InSlotName, UMaterialInterface* Material);
    int32 FindMaterialSlot(const FString& InSlotName) const;

    /** 实体网格子件；特殊用法（挂 socket、加特效）直接拿它。 */
    UStaticMeshComponent* GetVisual() const { return Visual; }
    int32 RodCount() const { return Rods.Num(); }

private:
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Rods;
    /** 本部件的网格（数据表给的路径解析结果；空＝用占位细杆素材）。 */
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> PartMesh;
    /** 占位细杆素材（引擎圆柱：高 100 cm、半径 50 cm）。 */
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> RodMesh;
    bool bPartVisible = false;
};
