#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelDoorNetState.h"
#include "ColdSteelRevolvingDoor.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/**
 * 旋转门（三扇，绕中柱轮转）：E 键或玩家走进门口即旋转 120°，让出一个通道口。
 * 叶扇在转动中对 Pawn 放行（可以跟着门走进去），停稳后重新挡人——转动由门口触发盒在
 * 服务器上判定（含远端玩家）。开合角复用 FColdSteelDoorNetState（From/To/Speed/StartedAt）。
 * E 键走门组件的服务器权威链路（与平开门同一入口表 ToggleDoor）。
 */
UCLASS()
class FPSGAME_API AColdSteelRevolvingDoor : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelRevolvingDoor();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    /** 旋转一步（120°，方向随操作者所在侧）：E 键入口。 */
    void ToggleDoorFrom(const APawn* InstigatorPawn);
    UFUNCTION(BlueprintCallable, Category="Door") void ToggleDoor() { ToggleDoorFrom(nullptr); }
    UFUNCTION(BlueprintPure, Category="Door") bool IsDoorOpen() const { return false; }
    /** 放置时由建造系统写入材质（中柱与三扇一起换）。 */
    void Configure(UMaterialInterface* Surface);
    void PrepareBuildPreview() { AlignGeometry(); }

protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION()
    void HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void ApplyAngle(float DeltaSeconds);
    /** 三扇按包围盒挂到转轴：各自 120° 方位、内缘贴中柱、底面贴地。 */
    void AlignGeometry();
    void UpdateLeafPawnCollision();
    bool LeavesOverlapPawn() const;
    /** 玩家在门的哪一侧（本地 X 符号）决定旋转方向；拿不到时用 +1。 */
    float RotateDirectionFor(const APawn* InstigatorPawn) const;
    UFUNCTION() void OnRep_Swing();
    UFUNCTION() void OnRep_Setup();

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> DoorRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Pivot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> CenterPost;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Leaves[3];
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> ContactZone;
    /** 每步旋转角（度）：三扇均布，120° 正好转出一个通道口。 */
    UPROPERTY(EditAnywhere, Category="Door") int32 StepDegrees=120;
    /** 每步旋转时长（秒）。 */
    UPROPERTY(EditAnywhere, Category="Door") float StepSeconds=.9f;

    float CurrentAngle=0.f;
    float TargetAngle=0.f;
    float LeafRadiusCm=23.f;
    FVector LeafHalfCm=FVector::ZeroVector;
    FVector LeafOriginCm=FVector::ZeroVector;
    /** 旋转音效（服务器组播，与门开声同源）。 */
    UPROPERTY(EditAnywhere, Category="Door|Audio") TObjectPtr<class USoundBase> RotateSound;
    UFUNCTION(NetMulticast, Reliable)
    void MulticastRotateSound();
    UPROPERTY(ReplicatedUsing=OnRep_Swing) FColdSteelDoorNetState NetSwing;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) TObjectPtr<UMaterialInterface> NetSurface;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) FVector NetScale=FVector::OneVector;
};
