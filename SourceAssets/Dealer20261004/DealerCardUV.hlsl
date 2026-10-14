// Card faces: 13 columns x 4 suits; result badge: 9 columns x 1 row.
float index = floor(clamp(CardIndex, 0.0, Columns * Rows - 1.0));
float2 cell = float2(fmod(index, Columns), floor(index / Columns));
// Keep sampling inside the selected tile when the thin card is viewed obliquely.
return (cell + clamp(UV, 0.005, 0.995)) / float2(Columns, Rows);
