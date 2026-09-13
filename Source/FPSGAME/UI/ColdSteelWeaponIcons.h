#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "PreviewScene.h"
#include "ColdSteelInventoryTypes.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelWeaponIcons.generated.h"

DECLARE_MULTICAST_DELEGATE(FColdSteelWeaponIconReady);
/** Presentation-only studio. Never equips a player or changes a profile to render an item. */
UCLASS()
class FPSGAME_API UColdSteelWeaponIcons : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override {return !IsTemplate()&&!Queue.IsEmpty();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UColdSteelWeaponIcons,STATGROUP_Tickables);}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    bool Supports(const FColdSteelItem& Item) const;
    FString Key(const FColdSteelItem& Item) const;
    void Request(const FColdSteelItem& Item);
    const FSlateBrush* Find(const FColdSteelItem& Item) const;
    FColdSteelWeaponIconReady OnReady;
    int32 RenderCount() const {return Completed;}
    bool IsIdle() const {return Queue.IsEmpty();}
#if WITH_EDITOR
    /** Author a base catalog PNG with the same assembly and materials as live inventory icons. */
    bool ExportCatalogIcon(const FString& Definition,const FString& Filename);
#endif
private:
    struct FJob {FColdSteelItem Item;FString Key;};
    struct FEntry {FSlateBrush Brush;uint64 Use=0;};
    TArray<FJob> Queue;
    TSet<FString> Pending,Failed;
    mutable TMap<FString,FEntry> Cache;
    mutable uint64 Serial=0;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class UTexture2D>> Textures;
    UPROPERTY(Transient) TObjectPtr<class AFPSGAMECharacter> Rig;
    UPROPERTY(Transient) TObjectPtr<class USceneCaptureComponent2D> Capture;
    UPROPERTY(Transient) TObjectPtr<class UTextureRenderTarget2D> Target;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMeshComponent>> CaptureMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMaterialInterface>> CaptureMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture>> CaptureTextures;
    TUniquePtr<FPreviewScene> Studio;
    FString RigDefinition;
    TSharedPtr<TAtomic<bool>,ESPMode::ThreadSafe> CaptureMaterialsReady;
    float Warmup=0,JobSeconds=0;
    int32 Stage=0,Completed=0;
    bool bCatalogExport=false;
    bool Prepare(const FColdSteelItem& Item);
    bool Readback(const FString& Key);
    void FinishJob(bool bSuccess);
};
