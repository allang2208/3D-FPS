// Source/FPSGAME/Production/ProductionToolComponent.h
// Merge public APIs after TryBeginSprintAttack; requires existing blunt authority declarations.
    bool GetCommittedSprintMovement(uint32 AttackId,FVector& Direction,float& DistanceCM,float& LimitCM,float& RecoverySeconds) const;
    bool IsSprintMovementPending(uint32 AttackId) const {return AttackId&&int32(AttackId-BluntLastServerRequestId)>0;}
