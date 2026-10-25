// Source/FPSGAME/Production/ProductionToolComponent.h
// Include WarhammerRiftState.h and merge private pooled trail fields.
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> WarhammerRiftMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WarhammerRiftMIDs;
    WarhammerRift::FTrail WarhammerRiftTrails[WarhammerRift::PoolSize];
    TWeakObjectPtr<UStaticMeshComponent> WarhammerRiftHead;
    TWeakObjectPtr<UAnimSequence> WarhammerRiftPreviousMotion;
    FTransform WarhammerRiftPreviousFrame;
    float WarhammerRiftPreviousSeconds=-1.f,WarhammerRiftHeadRefresh=0.f;
    int32 WarhammerRiftActive=INDEX_NONE,WarhammerRiftNext=0,WarhammerRiftKey=INDEX_NONE;
    void FeedWarhammerRift(FName Clip,float SourceSeconds);
    void TickWarhammerRifts(float Delta,bool Present);
    void ClearWarhammerRifts(bool Destroy=false);
