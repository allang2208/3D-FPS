// Add to the existing UHillsNightRaidSubsystem; not a standalone class.
    bool HasAssetPreparationFailed() const {return bAssetPreparationFailed;}
    UPROPERTY() TObjectPtr<class UHillsNightRaidSave> PendingSave;
    FString SaveSlot;
    bool bClockRestored=false,bSessionReady=false,bRestorePending=false,bSaveWritable=true;
    int32 RestoreIndex=0;
    double NextCheckpoint=0.;
    TMap<TWeakObjectPtr<APlayerController>,TWeakObjectPtr<AHillsNightReplicationGate>> ReplicationGates;
    TWeakPtr<FNetGUIDCache> PreparedNetCache;
    uint8 PreviousNetLoadMode=0;
    int32 AssetLoadFailures=0;
    bool bAssetPreparationFailed=false;
