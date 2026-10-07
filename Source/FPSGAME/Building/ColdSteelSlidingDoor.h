#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelDoorNetState.h"
#include "ColdSteelSlidingDoor.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/**
 * 滑动门（双扇对滑）：门扇沿门框平面向两侧滑开，不开出摆动空间也能过——适合走廊/窄房。
 * 复用 AColdSteelDoor 的交互入口（ToggleDoor/OpenDoor/CloseDoor）与 NetSwing 复制口径
 * （From/To 存滑动偏移 cm，Speed 为 cm/s），E 键经门组件服务器权威开关；6 秒自动关。
 * 滑动路径被实体挡住时拒绝开门（与门“两侧皆堵不开”同一口径，2026-10-04 用户拍板）。
 */
UCLASS()
class FPSGAME_API AColdSteelSlidingDoor : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelSlidingDoor();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    /** 尝试开门：返回 false 表示被拒（滑动路径被实体挡住）。 */
    bool OpenDoorFrom(const APawn* InstigatorPawn);
    void ToggleDoorFrom(const APawn* InstigatorPawn);

    UFUNCTION(BlueprintCallable, Category="Door") void ToggleDoor() { ToggleDoorFrom(nullptr); }
    UFUNCTION(BlueprintCallable, Category="Door") void OpenDoor() { OpenDoorFrom(nullptr); }
    UFUNCTION(BlueprintCallable, Category="Door") void CloseDoor();
    UFUNCTION(BlueprintPure, Category="Door") bool IsDoorOpen() const { return bOpen; }
    /** 放置时由建造系统写入材质（门框与两扇一起换）。 */
    void Configure(UMaterialInterface* Surface);
    void PrepareBuildPreview() { AlignGeometry(); }

protected:
    virtual void BeginPlay() override;
private:
    void ApplyOffset();
    /** 按包围盒摆放门框与两扇：门扇各缩为洞口半宽，底面贴地、居中于各自半侧。 */
    void AlignGeometry();
    /** 两扇滑到全开位置是否被实体挡住（WorldStatic/Dynamic/Destructible，Pawn 不算）。 */
    bool IsSlideBlocked() const;
    /** 关着且静止的门扇是否与 Pawn 重叠（决定能否恢复挡人）。 */
    bool LeavesOverlapPawn() const;
    void UpdateLeafPawnCollision();

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> DoorRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Frame;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LeafLeft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LeafRight;
    /** 两扇的闭位相对坐标（AlignGeometry 写入）：开合按“闭位 ± 当前偏移”绝对定位。 */
    FVector ClosedLeftLoc=FVector::ZeroVector;
    FVector ClosedRightLoc=FVector::ZeroVector;
    /** 滑开距离（cm）：一块门扇的洞口半宽，滑开后完全让出通道。 */
    UPROPERTY(EditAnywhere, Category="Door") float SlideDistanceCm=52.f;
    /** 滑动速度（cm/s）。 */
    UPROPERTY(EditAnywhere, Category="Door") float SlideSpeedCm=52.f;
    /** 打开后自动关闭的秒数；<=0 表示保持打开。 */
    UPROPERTY(EditAnywhere, Category="Door") float AutoCloseSeconds=6.f;

    bool bOpen=false;
    float CurrentOffset=0.f;
    float AutoCloseRemaining=0.f;
    /** 开/关门音效（服务器组播）。 */
    UPROPERTY(EditAnywhere, Category="Door|Audio") TObjectPtr<class USoundBase> OpenSound;
    UPROPERTY(EditAnywhere, Category="Door|Audio") TObjectPtr<class USoundBase> CloseSound;
    UFUNCTION(NetMulticast, Reliable)
    void MulticastDoorSound(bool bOpening);
    FVector LeafHalfCm=FVector::ZeroVector;
    FVector LeafOriginCm=FVector::ZeroVector;
    UFUNCTION() void OnRep_Swing();
    UFUNCTION() void OnRep_Setup();
    UPROPERTY(ReplicatedUsing=OnRep_Swing) FColdSteelDoorNetState NetSwing;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) TObjectPtr<UMaterialInterface> NetSurface;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) FVector NetScale=FVector::OneVector;
};
