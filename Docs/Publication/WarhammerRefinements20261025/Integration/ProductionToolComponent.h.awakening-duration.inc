// Source/FPSGAME/Production/ProductionToolComponent.h
// Duration is private replicated state; RecordStormDriveHit belongs in public hit API.
    UPROPERTY(Replicated) float RuneboundActivationSeconds=20.f;
    void RecordStormDriveHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit);
