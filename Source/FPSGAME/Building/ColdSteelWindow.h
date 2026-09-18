#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelWindow.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/**
 * 本工程自己的双开平开窗（100×100 洞口＋两扇对开窗扇，每扇靠中缝一侧带一个圆形把手），
 * 口径照 `AColdSteelDoor` 复制：包围盒对齐、E 键开关、玩家不参与阻塞判定、开门过程不挡玩家、整体换材质。
 *
 * 与门不同的两点：
 *  1. **两只铰链固定在外侧**（左扇铰在洞口左边、右扇铰在右边），两扇同时向同一侧开；
 *  2. **铰链贴面随开向走**：向外开时铰链贴窗框外面、向内开时贴内面。铰链若固定在框中间，
 *     窗扇转到 90° 时靠铰链的那半厚度会切进窗框（门的框薄、开角小，没暴露这个问题）。
 *
 * 交互入口 `ToggleWindow` / `OpenWindow` / `CloseWindow` 已登记在
 * `UColdSteelDoorInteraction` 的入口表里，所以玩家按 E 就能开关（与门同一套按键路径）。
 */
UCLASS()
class FPSGAME_API AColdSteelWindow : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelWindow();
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Window") void ToggleWindow();
    UFUNCTION(BlueprintCallable, Category="Window") void OpenWindow();
    UFUNCTION(BlueprintCallable, Category="Window") void CloseWindow();
    UFUNCTION(BlueprintPure, Category="Window") bool IsWindowOpen() const {return bOpen;}
    /** 放置时由建造系统写入材质（不改变几何）：窗框与两扇窗扇的全部材质槽一起替换。 */
    void Configure(UMaterialInterface* Surface);

protected:
    virtual void BeginPlay() override;
    /** 窗框边梃宽（cm）：洞口半宽 = 窗框半宽 − 边梃宽。子类（双开门）在构造函数里覆盖。 */
    float FrameMemberCm=6.f;
    /**
     * 窗扇**板厚的一半**（cm）。不能用窗扇包围盒的 X 半宽：窗扇中间那对圆形把手会往外凸，
     * 包围盒会跟着变大；铰链要贴着扇板外侧面，所以这里用名义板厚（与网格脚本的 LEAF_T 一致）。
     */
    float LeafHalfThicknessCm=2.f;
    /** 开合角（度，绝对值；方向由 SwingSign 决定）。85° 而不是 90°：窗扇中间那对圆形把手是贯通的、
        两面各凸出 2 cm，转到接近全开时**摆向那一侧**的把手尖会扫进窗框边梃（88° 时约 0.7 cm），
        85° 留出余量。真实窗的执手也只在摆动反侧，这里要两面都能看，所以靠收角度解决。 */
    UPROPERTY(EditAnywhere, Category="Window") float OpenAngleDegrees=85.f;
    /** 开合时长（秒）。 */
    UPROPERTY(EditAnywhere, Category="Window") float OpenSeconds=.6f;
    /** 打开后自动关闭的秒数；<=0 表示保持打开（窗默认不自动关，要门那套把它设成 6 即可）。 */
    UPROPERTY(EditAnywhere, Category="Window") float AutoCloseSeconds=0.f;
    // 三个网格组件留给子类换外观（双开门用另一套网格）。
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> HingeLeft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> HingeRight;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LeafLeft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LeafRight;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Frame;
private:
    void ApplyAngle(float DeltaSeconds);
    /** 按包围盒摆放窗框与两扇窗扇：网格 pivot 不在中心时也能贴地、居中并对上洞口。 */
    void AlignGeometry();
    /** 铰链贴窗框的哪一面（外面／内面）以及窗扇落在铰链的内侧：由当前开向 SwingSign 决定。 */
    void ApplyHingeDepth();
    /** 缓存窗扇包围盒，用于开窗前的摆动空间检测。 */
    void CacheLeafBounds();
    /**
     * 两扇窗扇按 SwingSign 侧（+1／−1）扫过去是否被实体挡住。
     * 检测用窗扇碰撞盒在 25%／50%／75%／100% 开合角上做重叠查询；只查世界实体
     * （WorldStatic／WorldDynamic／Destructible：地形、体素、构件、残骸），玩家与其它 Pawn 不参与判定。
     */
    bool IsSwingBlocked(float SwingSign) const;
    /** 摆动检测用的碰撞盒（比窗扇略缩，避免与窗框、临格体素贴合面产生假阻塞）。 */
    FVector LeafTestExtent() const;
    /** 任一扇窗扇当前位置是否与某个 Pawn 重叠（关到位时用它决定能不能恢复“挡住玩家”）。 */
    bool LeavesOverlapPawn() const;
    /**
     * 玩家碰撞口径与门一致：只有“关着且已经静止”的窗扇才挡住 Pawn；
     * 开窗／关窗过程中（以及开着时）窗扇对 Pawn 为 Ignore，可以从玩家身上扫过去。
     * 若关到位时玩家仍在窗扇里，则先保持 Ignore，等他离开再恢复阻挡。
     */
    void UpdateLeafPawnCollision();
    void SetLeavesPawnBlocking(bool bBlock);
    /** 玩家站在窗的哪一侧（窗的本地 X 轴，+1／−1）；没有本地玩家时返回 false。 */
    bool TryGetPlayerSideSign(float& OutSign) const;
    /** 一次性自检日志：打印窗框与两扇窗扇的世界包围盒，便于确认贴地、居中与洞口对齐。 */
    void LogGeometryOnce();

    bool bOpen=false;
    float CurrentAngle=0.f;
    /** 目标张开角（度，取绝对值；摆向由 SwingSign 决定，窗扇转角 = ±SwingSign×该值）。 */
    float TargetAngle=0.f;
    float AutoCloseRemaining=0.f;
    /** 两扇窗扇在本地 X 上的摆动方向（+1／−1）：+1 表示铰链贴外面、两扇摆向 +X（玩家在 −X 侧时）。 */
    float SwingSign=1.f;
    bool bOpenFlipped=false;
    /** 窗扇包围盒（cm）：半尺寸与中心相对组件原点的偏移。注意窗扇的 X 半宽含把手凸出，
        铰链深度与扫掠检测盒改用名义板厚（本类的 LeafHalfThicknessCm 成员）。 */
    FVector LeafExtentCm=FVector::ZeroVector;
    FVector LeafOriginCm=FVector::ZeroVector;
    /** 窗框包围盒半尺寸（cm）：铰链的深度与洞口宽度都由它推出来。 */
    FVector FrameExtentCm=FVector::ZeroVector;
    FVector FrameOriginCm=FVector::ZeroVector;
};
