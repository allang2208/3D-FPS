// Source/FPSGAME/Production/ProductionToolComponent.h
// Merge private VFX declarations beside Runebound presentation state.
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FinalTollLightningMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FinalTollLightningMID;
    TWeakObjectPtr<UStaticMeshComponent> FinalTollLightningHead;
    float FinalTollLightningRefresh=0.f;
    void UpdateFinalTollLightning(float Delta,bool Equipped);
    void UpdateStormDriveLightning(float Delta);
    void ClearStormDriveLightning();
    UFUNCTION(NetMulticast,Unreliable) void MulticastStormDriveImpact(AActor* Target,FVector Point,FVector Normal,uint32 Seed,double ServerAt);
    struct FStormDriveBurst
    {
        TWeakObjectPtr<AActor> Target;
        FVector LocalPoint=FVector::ZeroVector,WorldPoint=FVector::ZeroVector,Normal=FVector::UpVector;
        double ServerAt=-100.;
        uint32 Seed=0;
    };
    FStormDriveBurst StormDriveBursts[4];
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> StormDriveMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> StormDriveMIDs;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> StormDriveMaterial;
    TWeakObjectPtr<UStaticMeshComponent> StormDriveSeat;
    TSharedPtr<FStreamableHandle> StormDriveLoad;
    float StormDriveSeatRefresh=0.f,StormDriveShapeRefresh=0.f;
