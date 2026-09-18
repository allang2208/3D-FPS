#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelDoor.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/**
 * 本工程自己的门（单扇平开＋门框），用于建造面板与关卡里的可交互门。
 *
 * 为什么不直接用 Fab Door System 的交互门：那套门的 OnInteraction 参数与 Tick 都写死了它自己的
 * 第三人称角色（`GetPlayerCharacter → Cast To BP_ThirdPersonCharacter`），换成我们的角色后会
 * Cast 失败并每帧刷 "读取 Player Ref 结果为无"，门也不会动（2026-09-17 实测日志）。
 *
 * 交互入口 `ToggleDoor` / `OpenDoor` / `CloseDoor` 无参，正好落在
 * `UColdSteelDoorInteraction` 的入口表里，所以玩家按 E 就能开关；门板沿用包里的 SM_Door，
 * 门框用本工程缩放进深后的 `Props/SingleDoor20260918/SM_SingleDoorFrame_D40`（40 × 114 × 212，
 * 进深 40 ＝ 2 格体素，2026-09-18 与双开门统一），后续可换成我们自己的门网格，
 * 也可以在这里接第一人称推门动作。
 */
UCLASS()
class FPSGAME_API AColdSteelDoor : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelDoor();
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Door") void ToggleDoor();
    UFUNCTION(BlueprintCallable, Category="Door") void OpenDoor();
    UFUNCTION(BlueprintCallable, Category="Door") void CloseDoor();
    UFUNCTION(BlueprintPure, Category="Door") bool IsDoorOpen() const {return bOpen;}
    /** 放置时由建造系统写入材质（不改变几何）。 */
    void Configure(UMaterialInterface* Surface);

protected:
    virtual void BeginPlay() override;
private:
    void ApplyAngle(float DeltaSeconds);
    /** 按包围盒摆放门框与门板：网格 pivot 不在中心时也能贴地并对齐（StarterContent 的 pivot 在底边／角上）。 */
    void AlignGeometry();
    /** 缓存门板包围盒，用于开门前的摆动空间检测。 */
    void CacheLeafBounds();
    /**
     * 门板朝 DirectionSign 侧扫过去是否被实体挡住。
     * 检测用门板碰撞盒在 25%／50%／75%／100% 开合角上做重叠查询；只查询世界实体
     * （WorldStatic／WorldDynamic／Destructible：地形、体素、构件、残骸），**玩家与其它 Pawn 不参与判定**。
     */
    bool IsSwingBlocked(float DirectionSign) const;
    /** 摆动检测用的碰撞盒（比门板略缩，避免与地面／门框贴合面产生假阻塞）。 */
    FVector LeafTestExtent() const;
    /** 门板当前位置是否与某个 Pawn 重叠（关到位时用它决定能不能恢复“挡住玩家”）。 */
    bool LeafOverlapsPawn() const;
    /**
     * 玩家碰撞口径：只有“关着且已经静止”的门板才挡住 Pawn；
     * 开门／关门过程中（以及开着时）门板对 Pawn 为 Ignore，所以门可以从玩家身上扫过去。
     * 若关到位时玩家仍在门板里，则先保持 Ignore，等他离开再恢复阻挡，避免把人挤住。
     */
    void UpdateLeafPawnCollision();
    /** 玩家站在门的哪一侧（门的本地 X 轴，+1／−1）；没有本地玩家时返回 false。 */
    bool TryGetPlayerSideSign(float& OutSign) const;
    /** 把“世界侧（+X／−X）”换算成开合角符号：铰链在 +Y 时同号，在 −Y 时反号。 */
    float AngleSignForWorldSide(float WorldSideSign) const;
    /** 一次性自检日志：打印门框/门板的世界包围盒，便于确认贴地与对齐。 */
    void LogGeometryOnce();
    /** 铰链：门板绕它旋转；位置在门洞一侧。 */
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Hinge;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Leaf;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Frame;
    /** 开门角度（度，正负决定内外开）。 */
    UPROPERTY(EditAnywhere, Category="Door") float OpenAngleDegrees=92.f;
    /**
     * 铰链装在哪一侧：true = 铰链在本地 +Y，门从 −Y 侧（把手那一侧）开始开。
     * 2026-09-17 用户要求“从把手这一侧开始打开”，所以默认 true；做左右手门时把它设为 false。
     */
    UPROPERTY(EditAnywhere, Category="Door") bool bHingeOnPositiveY=true;
    /** 开合时长（秒）。 */
    UPROPERTY(EditAnywhere, Category="Door") float OpenSeconds=.55f;
    /** 打开后自动关闭的秒数；<=0 表示保持打开。 */
    UPROPERTY(EditAnywhere, Category="Door") float AutoCloseSeconds=6.f;
    bool bOpen=false;
    float CurrentAngle=0.f;
    float TargetAngle=0.f;
    float AutoCloseRemaining=0.f;
    /** 门板包围盒（cm）：半尺寸与中心相对组件原点的偏移。 */
    FVector LeafExtentCm=FVector::ZeroVector;
    FVector LeafOriginCm=FVector::ZeroVector;
    /** 最近一次开门选定的方向（+1／−1）与是否因阻挡而反向。 */
    float OpenDirection=1.f;
    bool bOpenFlipped=false;
    /** 铰链侧符号（+1／−1），由 bHingeOnPositiveY 决定，AlignGeometry 时写入。 */
    float HingeSign=1.f;
};
