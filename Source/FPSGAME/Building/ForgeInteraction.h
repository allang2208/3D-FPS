#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ForgeInteraction.generated.h"

class UColdSteelHUDWidget;
class UColdSteelForgingSystem;
class UCameraComponent;
class UForgeArmsMeshComponent;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UColdSteelForgeActionWidget;
class UPointLightComponent;
class AVoxelBuildPrefabActor;
class UStaticMesh;
class USoundBase;
struct FStreamableHandle;
struct FInputKeyEventArgs;

/** Local, station-anchored presentation. ForgingSystem remains the inventory/quality authority. */
UCLASS()
class FPSGAME_API AForgeInteraction : public AActor
{
    GENERATED_BODY()
public:
    AForgeInteraction();
    void Prepare(APlayerController* Player,AVoxelBuildPrefabActor* Station,UColdSteelHUDWidget* InHUD);
    bool Ready(FString& Reason) const;
    bool Start(FName Recipe,FString& Reason);
    void Enter();
    bool IsRunning() const {return bRunning;}
    bool HandleInput(const FInputKeyEventArgs& Event);
    void Stop(bool bReturnPanel);
    virtual void Tick(float DeltaTime) override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void AssetsLoaded();
    bool LoadGrip();
    void PoseArms(const FTransform& RightTool,const FTransform& LeftTool);
    void SolveArm(bool Right,const FTransform& Hand);
    void Present(float DeltaTime);
    void Contact();
    void Sparks(float DeltaTime);
    void EmitHotImpact(const FVector& Surface);
    void UpdateThermalEffects(float DeltaTime,float Heat,const FTransform& Work,double Now);
    void PresentQuench(float Age,FTransform& Work,FTransform& Tool);
    void UpdateQuenchContact(const FTransform& Work,double Now);
    void RestoreQuenchWater();
    FVector Point(const FVector2D& UV) const;
    FTransform HammerFrame(const FVector& Hit,double Age) const;
    FTransform TongFrame(const FTransform& BlankTransform) const;
    void RestorePlayer();
    void MoveAim(const FInputKeyEventArgs& Event);
    struct FHand
    {
        int32 Clavicle=INDEX_NONE,Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE;
        FTransform Grip;
        TArray<int32> Bones;
    };
    struct FStrokeKey {float Time,Angle;FVector Offset;};
    struct FSpark
    {
        FVector Position,Velocity;
        float Age=1,Lifetime=.7f,Size=1,Roll=0,Spin=0;
        bool bScale=false,bBounced=false;
    };
    struct FFume
    {
        FVector Position,Velocity;
        float Age=2,Lifetime=1.5f,Seed=0,Opacity=0,Size=12;
        bool bSteam=false;
    };
    FHand Hands[2];
    TArray<FTransform> Reference,LocalReference,Pose;
    TArray<int32> ArmBoundsBones;
    TMap<int32,FQuat> Fingers;
    TArray<FStrokeKey> Stroke;
    TArray<FSpark> SparkPool;
    TSharedPtr<FStreamableHandle> Load;
    TWeakObjectPtr<APlayerController> PC;
    TWeakObjectPtr<AVoxelBuildPrefabActor> Station;
    TWeakObjectPtr<AActor> PreviousView;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    FVector2D Aim=FVector2D(.5,.375),StrikeAim;
    FVector SparkOrigin;
    FString LoadError;
    double StrikeAt=-100,FinishAt=-1,LastFeedback=-100;
    float DisplayClock=0,ContactSeconds=.34f,StrokeSeconds=.82f;
    FVector HammerContact=FVector(6.8,0,21);
    FVector ImpactAxis=FVector(.45,.893,0),TongAxis=FVector(-.30,.954,0);
    FVector BodyOrigin=FVector(29,-34,146);
    FVector QuenchOrigin=FVector(56,-30,73);
    FVector ElbowPole=FVector(32,-10,-29);
    float WorkYaw=180,QuenchPitch=-62;
    int32 StrikeIndex=INDEX_NONE,BlankStage=INDEX_NONE;
    bool bReady=false,bRunning=false,bContact=false,bHeldInput=false,bHidPawn=false,bLastHit=false,bReturning=false;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgingSystem> System;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UForgeArmsMeshComponent> Arms;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Hammer;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Tongs;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Blank;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> HeatRing;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> AimRing;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> ScaleSparks;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BlankMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HeatMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> AimMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> Blanks;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgeActionWidget> Prompt;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> HeatVeil;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> HeatFumes;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> HotLight;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> VeilMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FumeMaterial;
    TArray<FFume> FumePool;
    FRandomStream VisualRandom;
    double LastHotImpact=-100;
    float FumeSpawnClock=0;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> QuenchWaterMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> PreviousWaterMaterial;
    FVector QuenchSurface=FVector(42,-30,46),SteamOrigin=FVector(42,-30,46);
    double QuenchContactAt=-1;
    float QuenchImmersion=0;
    int32 QuenchWaterSlot=INDEX_NONE;
};
