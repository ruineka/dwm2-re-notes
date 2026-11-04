# 9. Key worlds: procedural magic-key maps

Reimplementation reference. ROM addresses are `$BB:AAAA` (bank:CPU); the image is MBC5, so a ROM address's file offset is `bank*0x4000 + (addr - 0x4000)`. RAM is `$Cxxx`/`$FFxx`, save offsets are absolute SRAM file offsets. Anything the sources leave open is marked unknown.

## 1. What a key world is

A magic key is one 4-byte entry of `wKeyList` (`$C707`, SRAM `0x3C0A`, 32 entries, byte 0 = `$FF` ends the list). Using it loads no MapTable record: it creates or resumes a generated map whose entire state lives in SRAM.

Using a key: `PauseMenu_Plan_Keys_UseKey` (`$03`) writes `wDataBankSave = keyIndex | $80`; `RunFieldReturnPhase_RunReturnAction` (`$02`) copies it to `wCurrentKeyIndex` (`$C833`) and sets `wMapToggleFlag` (`$C914`) = `$80`; `WarpEffect_Warp` (`$02`, file `0xAE25`) takes the key path. Story keys (byte 3 bit 7) are not worlds: byte 3 `& $3F` indexes `KeyListMapDestinationTable` (`$02:$7006`, 13 x 8 B), reading only map id, screen x/y and player x/y. Generated keys (byte 3 bit 7 clear) either load slot `byte0 & $3F` (byte 0 bit 7 set) or run `WarpEffect_Warp_StartNewKeyWorld` (`$60:$4001`) -> `GenerateKeyWorld` (`$60:$4035`, file `0x180035`), then save. `hMapId` is never written on this path: identity is `wMapType` (`$CC44`) bit 7, and `wMapType & 7` picks the sub-screen type.

| `wMapType` | meaning | loader |
|---|---|---|
| `$80` (0) | open generated floor, 4x4 or 8x8 screens | `LoadMapScreen_Type0` `$61:$5443` |
| `$81`/`$82` | floor after an area exit / after the back-half toggle | same; `wKeyWorldFloor` bit 7 selects special map `$61` or `$62` |
| `$83` (3) | 1-4 screen "room" from `SpecialMapTable`, id = `state[floor].byte0 & $7F` | `LoadMapHeaderByMapType_Type3` `$61:$43B9` |
| `$84` (4) | event room entered from a special map's position warp; crossing into screen row 1 returns to the `$83` map | `WarpToScreen01Event83` `$61:$5807` |
| `$85` (5) | generated 4x4 room (behind stairs) | `LoadMapType5TilesetAndHeader` `$61:$4261` |
| `$86` (6) | room after the last room, special map `$50 + (floor-info byte 1 & 1)` | `$61:$422B` |
| `$87` (7) | goal room / arrival screen, special map `$66` | type-3 style |

Entry ends with `wMapType = $80`, then one transition frame `wMapType = $87` with the player at pixel `($40,$40)`.

## 2. Key entry and seed

`wKeyList` entry: byte 0 state, byte 1 prefix word slot, byte 2 suffix word slot, byte 3 level.

| byte | contents |
|---|---|
| 0 | `$FF` empty; `$FE` generated but not appraised; after appraisal the low bits are the display kind and bit 7 = "world exists" with the SRAM slot 0-19 in the low 6 bits (`$80..$93`); bit 6 = boss defeated |
| 1 | prefix word 0-15 |
| 2 | suffix word 0-55 |
| 3 | level 1-99 (= `wPartyStrength` at creation); bit 7 set = story key |

Example `$FE $06 $25 $0D` = appraised "WhiteMtn" at level 13. Seeds: `wKeySeeds`, 32 x 2 bytes little-endian at SRAM `0x3C8A`-`0x3CC9`, written when the key is made (`GenerateNewKeyEntry`, `$12`) and read by `WarpEffect_Warp_StartNewKeyWorld`. A used key therefore stores both its seed and its finished world record: regenerate from the seed or resume from the slot.

## 3. Key-name generation (creation time, not world generation)

`WriteKeyEntryTemp0` (`$12:7029`) writes byte 0; for kind `$FE` it far-calls `ComputePartyStrengthForKey` and `RollKeyContentsForLevelTemp0` (`$60:$4914`) and then writes bytes 1-3. Any other kind only gets byte 3 = `$80`. `GenerateNewKeyEntry` (`$12:6862`) takes a free slot, writes kind `$FE`, re-rolls to avoid a duplicate key (same byte 2 always re-rolls when byte 1 also matches, otherwise while `wKeyRetryCount < 20`), stores the seed, and returns `hTemp0 = 1` (0 = list full).

`RollKeyContentsForLevelTemp0`: `tier = level/10`; `roll = RandomBelow100()`; prefix slot = the first byte of `KeyContentsKindChanceRows[16*tier .. +15]` with `byte != 0 and byte >= roll` (a zero is a disabled slot and is skipped); suffix slot = the same scan of `KeyContentsChanceRows[60*tier .. +59]` **with no zero-skip**. Rows are cumulative thresholds out of 100, so slot i has probability `(row[i] - row[i-1])/100`.

Prefix rows (`$60:$6969`, file `0x182969`):

```
tier0  14 28 37 46 50 5A 5F 64 00 00 00 00 00 00 00 00
tier1  0F 1E 2D 3C 4B 55 5A 5F 64 00 00 00 00 00 00 00
tier2  00 0A 19 28 37 46 50 5A 5F 64 00 00 00 00 00 00
tier3  00 00 0F 1E 2D 3C 4B 55 5A 5F 64 00 00 00 00 00
tier4  00 00 05 0F 19 28 37 46 50 5A 5F 64 00 00 00 00
tier5  00 00 03 08 12 21 30 44 4E 58 5D 62 64 00 00 00
tier6  00 00 03 08 12 1C 26 35 44 53 58 5D 62 64 00 00
tier7  00 00 00 02 05 0F 19 28 37 46 50 5A 5F 62 64 00
tier8  00 00 00 00 03 08 0D 12 21 30 3F 49 53 5D 62 64
tier9  00 00 00 00 00 05 0A 0F 19 23 2D 37 46 55 5F 64
```

Suffix rows (`$60:$6A09`, file `0x182A09`, 10 x 60 B): tiers 0-2 identical (40 enabled slots; disabled 1,6,7,10,15-17,24,29,32,38,45,46,48,51,56-59); tiers 3-4 identical (55 enabled, only slot 10 disabled); tiers 5-7 identical (55 enabled, slot 10 disabled); tiers 8 and 9 have 39 enabled slots each (tier 8 disables 12,18-21,23,26,27,30,31,33,37,41,43,49,53,54,56-59; tier 9 differs from tier 8 only in slots 4-9). Slots 56-59 have no word in any tier and roll 99 reaches slot 55 at most. Slot 10 is the "Lord" family and appears only on level-80+ keys; slot 12 ("Isle") is off at tiers 8-9.

Names come from `$09:$4078` (file `0x24078`), 73 `$F0`-terminated strings: the list screen concatenates `word[byte1 + 1]` and `word[byte2 + $11]` with no separator (ROM spellings `Bsmt`, `Mtn`, `Mound`). A separate 236-string pool with a 756-entry u16 pointer table exists at `$88:461C`/`0x220018`; whether a display path uses it is not established.

## 4. The RNG

`NextRandomSeed` (`$00:$09F3`) is `seed = (seed*5 + 11) & $FFFF`, little-endian at `$CD03`/`$CD04`, returning the high byte; the low byte is readable and is used as a list index once. `RandomBelow100` (`$60`) steps until `wKeyRandomHi & $7F < 100`; `RandomBelowC` (`$84:$43AC`) steps until `wKeyRandomHi & $0F < C` with C in 1-16 (C = 0 loops forever). This is not the table RNG `NextTableByte` (`$00:$095B`, `wRandomLo/Hi`) used by sprite effects. The seed word is shared with field object/trigger placement: seeded once per generated world, then advanced by every later field draw.

## 5. What the key's bytes select

| source | table | effect |
|---|---|---|
| byte 1 | `KeyWorldBandAdjustTable` `$60:$43C7`, file `0x1803C7`, 16 signed bytes `$FE,$FF,$00..$0D` | `wKeyWorldBandAdjust` (`$CD02`) = -2..+13 |
| byte 2 | `KeyWorldBandRows` `$60:$43D7`, file `0x1803D7`, 56 x 8 B | bytes 0-5 = `$FF`-terminated monster **family** list -> `wKeyWorldMonsterBands` (`$CCF7`); byte 6 adds to the band adjust (sum clamped `>= 0`); byte 7 unused |
| byte 2 | `KeyWorldGoalKindRows` `$60:$4CC1`, file `0x180CC1`, 56 x 4 B | `value = row[rand & 3]`, redraw while 0; `wKeyWorldGoalKind` (`$CD0B`) = value - 1 (0-9) |
| byte 3 | `KeyWorldLevelTable` `$60:$47C5`, file `0x1807C5`, 100 x 8 B | triple (base, area, monster) -> `$C969`/`$C96A`/`$C96B` |
| byte 3 | `KeyWorldSizeByStrength` `$60:$4BF4`, file `0x180BF4`, 100 B | width/height |
| byte 3 | `KeyWorldLayout_Start_Data` `$60:$4C58`, file `0x180C58`, 10 pairs | `wKeyWorldAreaCount` = base + (rand & mask) |
| goal kind | `KeyWorldTilesetTable` `$61:$5728`, file `0x185728`, 10 x 6 B | tileset dfar + palette dfar, one theme per world |

Level record = `(base, area, monster, $64, $64, $64, 0, 0)`; only the first three bytes are read and record 0 is all zero. Samples (strength = base/area/monster): 1 = 14/18/19, 10 = 23/27/29, 35 = 35/39/42, 50 = 49/51/57, 99 = 86/96/99; base <= area <= monster, with plateaus. Consumers: the 32 normal monsters get `min(base + ((strength+10)*n / 150) / 2, 99)` with n = 0..31; the 8 boss entries use n = 15; the encounter table uses `area + 2*areaNo`; scripted foe levels use `max(monster,5) - 4`.

Size: index = `(strength - strength/10) + k` with k uniform 0-9 (`hi & $0F` retried while `>= 10`); the byte's high nibble is width, low nibble height, a 0 nibble meaning 10. Only `$44` (4x4, strength < 10) and `$88` (8x8) occur. Layout index = `2*(strength/10)` into the 10 pairs `{0,$0F},{8,$0F},{8,$0F},{$10,$1F}x7`, giving `wKeyWorldAreaCount` 0..15 / 8..23 / 16..47; that byte is an index into the 48-entry `KeyWorldAreaLayoutTable` (`$84:$4CCB`), not an area count (the real count 1-4 comes from `FillChunkSlots`).

Theme table (goal kind: tileset dfar, palette dfar): 0 `$90:4001`/`$90:448F`; 1 `$63:4001`/`$63:4468`; 2 `$64:4001`/`$90:44CF`; 3 `$66:4001`/`$65:4001`; 4 `$62:4B38`/`$62:508E`; 5 `$63:4C6B`/`$63:5170`; 6 `$64:4C61`/`$64:50E8`; 7 `$65:47D8`/`$65:4C79`; 8 `$62:5852`/`$62:5D2D`; 9 `$63:5907`/`$63:5DAD`. `LoadKeyWorldTilesetAndHeader` (`$61:$43CF`) loads 128 tiles at `vTiles2` (`$9000`), copies the 64-byte palette (8 BG palettes, CGB only), and sets `wMaxBlockingTile = $3D`, `wFieldEventKind = 2` (0 for goal kind 4), `wEncounterRate = $A2`, `wMapMoveType = 4` for goal kinds 1/7 (else 0), and `wMapSpriteKind` from file `0x184468` (10 B).

## 6. Generation pipeline and RNG order

| # | routine | draws |
|---|---|---|
| 1 | `KeyWorldLayout_Start` `$60:$4AE5`: clear flags + 8 visited bytes, goal kind, size, layout index, clear slots | goal kind >= 1; 1 size (retry while `hi&$0F >= 10`); 1 layout |
| 2 | `GenerateKeyWorld_FillChunkSlots` `$60:$4DA1`: place 1-4 chunk groups | 1 pattern + 1 list index per attempt; a bad fit redraws the pattern |
| 3 | `GenerateKeyWorld_ShuffleAreaNumbers` `$60:$4E0A` (skipped with 1 area) | 2 per area (+2 on a non-distinct pair) |
| 4 | `GenerateKeyWorld_MergeAreaInfo` `$60:$4DF6` | 0 |
| 5 | `KeyWorldLayout_PlaceAreaExits` `$60:$4F7C` | 2 per exit cell; the pair restarts on a closed or repeated cell |
| 6 | `GenerateKeyWorld_EmptyStep` `$60:$50E4` (`ret`) | 0 |
| 7 | `KeyWorldLayout_NumberCellsAndPlaceEntrances` `$60:$51B7`: flatten cell ordinals, place 3-8 doors | 2 per door attempt; returns 1 after 100 refusals, and `GenerateKeyWorld` then jumps back to step 1 |
| 8 | `KeyWorldLayout_FillEntrances` `$84:$4001`: one 16-byte state block per door | 0-3 per kind 4/5 door plus the rooms |
| 9 | `KeyWorldLayout_SetEntranceFlags` `$60:$50E5` | 1 `RandomBelow100` per kind 4/5 door |
| 10 | `GenerateKeyWorld_PlaceObjects` `$60:$5373` | see section 11 |
| 11 | `GenerateKeyWorld_RollMonsters` `$60:$4074` | see section 11 |
| 12 | `KeyWorldLayout_PlaceGoal` `$60:$5E42` | 0 |
| 13 | key byte 0 = `(byte0 & $BF) \| $80` | 0 |

A step-7 restart keeps the LCG stream (the seed is loaded once, before step 1). Step 2: for each of the four chunk slots while empty, draw `hi & $0F` and take the pattern from the fixed dispatch `S,T,W,B,W,T,S,T,W,B,W,T,S,T,W,B` (`$60:$5EEA`); single always fits, tall needs slot < 2 and slot+2 not `$FE`, wide needs an even slot with slot+1 `$FF`, 2x2 needs slot 0 with slot1 `$FF` and slots 2/3 not `$FE`. On success one draw picks the chunk list entry (`& $1F`; the single pattern uses `wKeyRandomLo & $1F`), the placement's area number is the pre-increment `hTemp7`, and `hTemp7` then increments. Step 3: `a1 = hi & 3` redrawn while `>= area count`, then `a2` likewise; distinct values swap the two area numbers in all slots, then a no-draw pass for b = 0..count-2 links area b to b+1 (largest-cell-index slot of area b tested up, left, down, right — the up test is dead code for slots 0-3 — and the first neighbour holding area b+1 with a non-zero cell index is exchanged with the first `(area<<4)|0` byte).

Kind 4/5 floors generate rooms inside step 8: `1 + ((count - 2) & $FF)` rooms (count 0 -> 255, 1 -> 256, 3 -> 2, 9 -> 8). Each room after the first costs one `RandomBelowC(10)` row lookup, one `RandomBelowC(8)`, and exit picks (2 draws each, retried while equal to the previous pick).

## 7. World layout data model

`wKeyWorldChunks` (`$CD60`) is 4 slots x `{addr lo, addr hi, bank, sub}`; screen (x,y) -> slot `2*(y>>2) + (x>>2)`, slot s covering `x = 4*(s&1)+0..3`, `y = 4*(s>>1)+0..3`, and slots outside the world are `$FE` (slots 1 and 3 for a 4-wide world, 2 and 3 for 4-tall), so a 4x4 world uses slot 0 only. A chunk group is `n` sub-chunks of `$60` B — 32 dfars: 16 screen tilemaps in `4*(y&3)+(x&3)` order, then 16 attribute maps — followed by `n` order bytes at `group + $60*n` (a permutation of 0..n-1, copied as the per-slot cell index). Cell record = `group + $60*sub + 3*(4*(y&3) + (x&3))`; its tilemap stream starts 8 bytes after that dfar, its attribute stream at the dfar `$30` bytes later.

`wKeyWorldAreas` (`$CD70`) is 4 bytes, one per slot: `(area << 4) | cell index`, `$FF` empty, `$FE` outside; `wKeyWorldAreaInfo` (`$CD74`) keeps the high nibbles, and step 7 rewrites the low nibbles to a flat global cell ordinal 0..slots-1 (doors look slots up by that ordinal). `wKeyWorldAreaExits` (`$CD78`) is 4 x 4 B indexed by area: `+0` cell in this area, `+1` cell in the next, `+2` flag (0 here), `+3` = `$FF` on the last entry; `wKeyWorldObjects` (`$CD7B`) is `+3` of the same list, not a second table. Exits use open cells only, where a cell is open iff its screen record's byte 0 is not `$FF` (`CheckKeyWorldCellIsOpen`, `$60:$5075`) — per record, not geometric.

`wKeyWorldFloorInfo` (`$CD88`) is 9 x 4 B per door: `+0` packed screen `(x<<4)|y`, `+1` door kind 0-6, `+2` never written, `+3` = 0 with `$FF` on the entry after the last (`$FF` is pre-stored at `$CD8B`); walks always step by 4 and stop on `$FF`. `wKeyWorldFloorState` (`$CDAC`) is 8 blocks x 16 B, one per door (section 9).

## 8. Rendering a floor screen

64 chunk groups sit in bank `$67` (`$67:4001`-`$67:750D`): 16 single (stride `$61`), 16 tall (`$C2`), 16 wide (`$C2`, overlapping), 16 four-sub (`$184`). The 2304 cell references resolve to 210 distinct screen records in banks `$62`-`$66` (142 open, 68 with byte 0 = `$FF`; closed records still carry a real tilemap and are drawn). `LoadMapScreen_Type0` (`$61:$5443`) looks up the slot and record dfar, skips 8 header bytes, LZSS-decompresses the tilemap into `wScreenTileBuffer` (`$C198`, 20 x 18 bytes, stride 20), then the attribute stream into `wScreenAttrBuffer` (`$D000`, WRAM bank 2) with `rSVBK = 2`. Tilemap byte n addresses `$9000 + 16*n`; the attribute byte selects one of 8 palettes; bits 4-7 are 0 in the chunk data except 84 cells in four records that set bit 3 (VRAM bank 1): `$62:406A`, `$62:41C9`, `$62:423A`, `$62:4365`. No key-world code writes `rVBK`/bank 1, so that bit is hardware-undefined here. Compression is Enix LZSS with a 3-byte header (u16 size low/high, u8 marker): a marker introduces `lo` and `b2`, length = `(b2 & 15) + 4` (plus `$13` if the length byte is `$13`), offset = `((b2 >> 4) << 8) | lo` from the destination start; a source at/past the write pointer is moved back `$1000`, one before the start reads 0.

Overlays are written into `$C198` after decompression, so they collide like real tiles: goal marker `$46/$47` over `$56/$57` (`DrawKeyWorldGoalAtScreen` `$61:$54EC`); door markers at cell (4,4) (`DrawKeyWorldFloorInfo3ObjectTilesForScreen` `$61:$562F`: kind 1/6 `$68..$6F` 4x2, kind 2 `$4C..$5F`, kind 3 `$60..$67` 4x2, kind 4 `$4A/$4B/$5A/$5B`, kind 5 `$48/$49/$58/$59`, attribute 5 or 6 on CGB); area-exit tiles `$46/$47` or the bent `$70..$73` (`$61:$55AF`); room-exit tiles (`$61:$474C`, `tile = $46 + 2*(kind-4)` / `$48 - 2*(kind-4)` at cell (4,4)).

## 9. Rooms, doors, entrance and close-up screens

| kind | handler (`$84`) | effect | draws |
|---|---|---|---|
| 0 | `_Blank` `$406D` | nothing written (state stays stale) | 0 |
| 1 | `$4072` | `state[0] = Kind1_Data[goal]`, `state[2..15] = block[1..14]` | 0 |
| 2 | `$4091` | `state[0] = Kind2_Data[goal] + $20`, state bit 7 from a draw | 1 |
| 3 | `$40C2` | as kind 2 but `+ $40` | 1 |
| 4 | `$40F3` | `state[0] = block[1]` (room count), `state[1] = wKeyWorldGenRoom`, `state[2] = Kind4_Data[4*goal + (draw&3)]` | 1 + 0-2 + rooms |
| 5 | `$4156` | `state[2] = Kind5_Data[draw & 7]`, then rooms | 1 + 0-2 + rooms |
| 6 | `$406E` | `state[0] = $54` only | 0 |

`Kind1_Data` `$84:$41AE` = `00 00 03 01 00 00 04 05 02 00`; `Kind2_Data` `$84:$41B8` = `00 06 03 01 07 08 04 05 02 09`; `Kind5_Data` `$84:$41C2` = `05 06 07 08 09 05 07 09`; `Kind4_Data` `$84:$41CA` = 10 rows x 4 (`00 0B 00 0B`, `00 02 00 02`, ..., `01 00 0B 00 0B`). Kinds 1/2/3/6 use `state[0] & $7F` as the special-map id; kinds 4/5 use state[0]/state[2] as room tileset indices and state[1] as the first room number.

Room entries are 2 bytes `{room id, (exit left << 4) | exit entered}` (`$F` = none), appended to `wKeyWorldRoomTable` (`$CE2C`) from the rotating `wKeyWorldGenRoom` (`$CC46`). First room: kind 5 `$A0 + 8*(hi&3) + RandomBelowC(5)`, kind 4 `8*RandomBelowC(9) + RandomBelowC(8)`; then `KeyWorldNextRoomRows[16*(lastExit & $F) + RandomBelowC(10)] + RandomBelowC(8)` with the six rows at `$84:$42C7`:

```
0  00 08 10 18 20 28 30 38 40 48 00 00 00 00 00 00
1  00 08 10 18 50 58 60 68 70 78 00 00 00 00 00 00
2  00 20 28 30 50 58 60 80 88 90 00 00 00 00 00 00
3  08 20 38 40 50 68 70 80 88 98 00 00 00 00 00 00
4  10 28 38 48 58 68 78 80 90 98 00 00 00 00 00 00
5  18 30 40 48 60 70 78 88 90 98 00 00 00 00 00 00
```

Room ids index `KeyWorldRoomPointers` (`$72:$4001`, 192 words; non-zero = `$4181 + $63*n`); ids 165-167, 173-175, 181-183, 189-191 have no record. A record is 99 B: exit ids 0-5 at `+0..+2`, 16 tilemap dfars at `+3 + 12*y + 3*x`, 16 attribute dfars at `+$30`. Exit ids index `CheckWarpsByMapType_RoomExits_Data` (`$61:$5BB5` = `00 30 11 22 03 33` = screens (0,0) (3,0) (1,1) (2,2) (0,3) (3,3)). Room screens are 4x4 with `wMaxBlockingTile $3F`, `wEncounterRate $A3`, and one of 12 tilesets (`MapType5TilesetTable` `$61:$42DD`, 12 x 6 B, banks `$6D-$70`).

Doors on the open floor warp to 1-4 screen special-map records (`SpecialMapTable` `$61:$60D8`, 128 words; 35 records of 26 B at `$61:$61D8`): `+0..2` tileset, `+3..5` raw palette, `+6` width, `+7` height, `+8` blocking tile, `+9` header byte, `+10` event kind, `+$0C` entry A (screen x, screen y, pixel x, pixel y = cell (4,4)), `+$10` entry B (cell (5,4)), `+$14`/`+$17` screen/attribute dfar arrays indexed `3*(y*width + x)`. Ids 0-5 are 1x2, `$20-$29` 2x2, `$40-$49` 2x1, `$50-$54` 1x1, `$61-$66` 1x1; entry A = `(0,1,$40,$80)` except 1x1 records (`(0,0,0,0)`); entry B differs only for id `$54` (FixedState record 30: `(0,0,$50,$80)`), which is why cell (5,4) exists. Leaving such a map is done by walking off the grid: `CheckKeyWorldWarpTable` (`$61:$58BC`) walks 9-byte entries of `KeyWorldWarpListTable` (`$61:$6566`, six lists) against the transient screen index (`$FF` off the left/top edge, `wMapWidthScreens`/`wMapHeightScreens` off the right/bottom) and on a hit restores `wMapType = $80` at the door's screen with `wWarpDestFacing = $F0`.

`wKeyWorldFloor` (`$CC45`) = area in the low 7 bits plus bit 7, the "back half" toggle set at the floor-flip cell (4,3) by `CheckWarpsByMapType_FloorToggle` (`$61:$5BBB`); bit 7 selects which of the two special-map records loads and which end of the exit portal is used, so it must be saved. An area exit fires only on the top screen row (`hMapScreenY == 1`) via `WarpByKeyWorldAreaExitsEntryAtScreenRow1` (`$61:$585A`), using `cell_next` when bit 7 is set and `cell_this` otherwise, destination pixel `($40,$40)`.

Arrival: `wKeyWorldGoalScreen` = packed screen of `wKeyWorldFloorInfo[0].byte0` (the first door's screen); the arrival pixel comes from `PlaceGoal_Data` (`$60:$5ED1`, eight pairs `10 10 / 10 60 / 40 20 / 40 60 / 50 20 / 50 60 / 70 30 / 80 70`) indexed by that screen record's byte 0. The Twig goal (`ItemUsable_LogTwig_KeyWorld`, `$84:$48A9`) stores `wKeyWorldGoal`/`GoalCell`/`Key` (`$C88F`-`$C891`); `CheckWarpsByMapType_KeyWorldGoalWarp` (`$61:$5E8D`) accepts either goal.

Close-up (Select world map, `$A1`): `wMapType & 7` 1-7 opens the close-up (`wWorldMapState = 3`), 0 the key-world overview (not modelled in the notes). The window shows 20x18 cells (5x5 cells per screen, up to 4x4 screens); the player's cell lands on BG cell (9,8). A cell takes one tile from `AutomapBlocks` (`$5E:$43A0`, 281 blocks of 5x5 tile ids, `25*(id-1) + 5*cellRow + cellCol`) where the id is the little-endian word at screen-record byte 6; unvisited screens (`IsMapScreenAVisited`, `$A1:$58BA`) stay tile `$57`. Markers: the player blinks 32 frames on / 32 off at 4 OAM entries; floor/area-exit and object markers are 8x8 dots at `40*dx + 16 - 8*cell` (skip unless the cell is 0..4 inside the window), object positions coming from the 16-entry nibble table `$A1:$4D94`; the goal marker uses its own tile offset. No attribute writes and no scrolling.

## 10. The 405-byte SRAM record

20 slots of `0x195` B: SRAM bank 2 at `0x4000 + 0x195*slot`, backup in bank 3 at `0x6000 + 0x195*slot`. Byte 0 = marker `slot + $50`; bytes 1-404 (`$194`) are the block at `wKeyWorldFlags` (`$CD07`):

| off | size | RAM | meaning |
|---|---|---|---|
| `0x000` | 1 | `$CD07` | `wKeyWorldFlags`, bit 7 = boss cleared (cleared on generation) |
| `0x001` | 1 | `$CD08` | goal screen `(x<<4)\|y` |
| `0x002` | 1 | `$CD09` | goal pixel x |
| `0x003` | 1 | `$CD0A` | goal pixel y |
| `0x004` | 1 | `$CD0B` | goal kind / theme 0-9 |
| `0x005` | 1 | `$CD0C` | layout index 0-47 |
| `0x006` | 1 | `$CD0D` | width in screens (4 or 8) |
| `0x007` | 1 | `$CD0E` | height in screens (4 or 8) |
| `0x008` | 1 | `$CD0F` | object band 0-15 |
| `0x009` | `$40` | `$CD10` | `wKeyWorldMonsters`: 32 x `{id, 2*level ORed in}` |
| `0x049` | `$10` | `$CD50` | reserved, not written by the generator |
| `0x059` | `$10` | `$CD60` | `wKeyWorldChunks`, 4 slots x 4 B |
| `0x069` | 4 | `$CD70` | `wKeyWorldAreas` (flat cell ordinals after generation) |
| `0x06D` | 4 | `$CD74` | `wKeyWorldAreaInfo` |
| `0x071` | `$10` | `$CD78` | `wKeyWorldAreaExits`, 4 x 4 B |
| `0x081` | `$24` | `$CD88` | `wKeyWorldFloorInfo`, 9 door entries |
| `0x0A5` | `$80` | `$CDAC` | `wKeyWorldFloorState`, 8 x 16 B |
| `0x125` | `$46` | `$CE2C` | `wKeyWorldRoomTable`, 2 B per room index (35 slots before `$CE72`; no bounds check) |
| `0x16B` | 9 | `$CE72` | `wKeyWorldEncounter`, three foes |
| `0x174` | `$10` | `$CE7B` | `wKeyWorldEncounterTable`, 4 entries x 4 B |
| `0x184` | 4 | `$CE8B` | menu flags from `SetEntranceFlags` |
| `0x188` | 4 | `$CE8F` | unnamed |
| `0x18C` | 8 | `$CE93` | `wVisitedScreens` bitmap |
| `0x194` | - | `$CE9B` | end of the record |

Live state just below the block is saved by the ordinary save: `wKeyWorldSlot` `$CC42`, `wKeyWorldArea` `$CC43`, `wMapType` `$CC44`, `wKeyWorldFloor` `$CC45`, `wKeyWorldGenRoom` `$CC46`; save block `0x3E0B` holds `0xB5` bytes from `$CC42` (by size also covering `wMapObjects` at `$CC48`).

Save/load (`$60:$6C95` / `$60:$6CD1`) both refuse `wKeyWorldSlot >= 20`, compute `$A000 + $195*slot` with `Multiply8By16`, and switch SRAM bank 2 via `rRAMB = 2`, `rRAMG = $0A`. Save writes the marker then copies `$194` bytes; load compares the marker and copies only on a match. `FindSRAMSlotMarkerIndex` (`$60:$6C61`) scans the 20 markers in order against `$50 + index` and returns the first free index, or `$FF` when all are used. Checksums: the bank-3 copy ends at `0x7FFE` with `~sum(0x6000..0x7FFD) + 0x1234`; bank 1 has a record checksum at `0x3A73` = `~sum(0x206F..0x3A72) + 0x4321` and a saved-block checksum at `0x3F98` = `sum(0x3B01..0x3EBF) + 0x9753`. The boot gate verifies banks 1 and 3 only; the 20 bank-2 slots are covered by no checksum, and the trigger for restoring from bank 3 is not established.

## 11. Encounters and treasures

Normal monsters: for each of the 32 words take the next family from `wKeyWorldMonsterBands` (a `$FF` restarts at the head), draw `KeyWorldBossBandPickRows[8*min(adjust,16) + (hi & $0F)]` (4-bit mask, so 8-15 read into the next 8-byte row), then `KeyWorldBandSpeciesTable[16*family + 2*band]` (`$60:$6D6D`, a u16 pointer to a count byte plus count 2-byte ids), and draw `hi & 7` until it is below the count (count 1 uses no draw), retrying on ids `$00A4`, `$00A5`, `$0174`; an empty list moves to the next family. The 8 boss words at `wKeyWorldMonsters + $40` use family 9 ("Lord").

`RollEncounterFoes`: band = `BandFromStrength(strength)`; then `wKeyRandomLo & 7` == 0 leaves foes 2 and 3 empty, otherwise both are the same species from band `max(band-2,0)`; foe levels = `max(wKeyWorldLevelMonster,5) - 4` in `wKeyWorldEncounter + 2/+5/+8`. `RollEncounterTable`: 16 bytes; per area (walking the exit list) `{monster word, level, 0}` with level = `wKeyWorldLevelArea + 2*areaNo` and species from band `max(BandFromStrength(strength)-2,0)`. `BandFromStrength`: < 20 -> 2, < 40 -> 3, < 60 -> 4, < 80 -> 5, < 95 -> 6, else 7 (duplicate compares at 70/80 and 90/95 change nothing).

Treasures: `GenerateKeyWorld_PlaceObjects` places 10/15/20 objects (counts at file `0x1813B3`), band = `SetKeyWorldBandForA(strength)`: < 11 -> 0, >= 80 -> 15, else `(strength-10)/5 + 1` (masked to 4 bits). Kind/contents come from 16 rows x 64 cumulative bytes at file `0x18156F` (first non-zero threshold `>= RandomBelow100`): slot 0 = gold, slot >= 2 = item id `slot - 2`, slot 1 = kind 3 (never used here); gold amount = `max(1, (r1 + r2)*band/10)` with `r1 = RandomBelow100` and `r2 < 10`. The 8-byte entry at `wMapObjects` (`$CC48`) is `{kind, contents, 0, 0, screen byte, cell/index byte, 0, 0}`; in a key world the last byte is copied from the screen record's bytes 1-4 (`rand & 3`, redraw on `$FF`) and the close-up treats it as an index into the 16-entry nibble table `$A1:$4D94`. A failed placement truncates the count; objects are placed again on re-entry (`RefreshKeyWorldObjectsOnEntry`), and field skill 18 reveals their close-up markers.

Boss: scripts `$85` / `$9E` read `wKeyWorldEncounter` (one foe when bytes 3 and 4 are both 0, else three) and `wKeyWorldEncounterTable[(floor & $7F)*4]`; clearing sets `wKeyWorldFlags` bit 7, byte 3 of all four encounter-table entries, and bit 6 of the key entry. The per-step wild-encounter cadence driven by `wEncounterRate` (`$A2` open floor, `$A3` rooms) and the rule that picks one of the 32 monster entries are not established in the notes.

## 12. What a reimplementation must match

1. LCG exactly: `seed = (seed*5 + 11) & $FFFF`, one step per draw, high byte used unless stated; `RandomBelow100` / `RandomBelowC` are rejection loops that consume steps.
2. The draw order above, including goal kind before size, redraws on bad pattern fits, the `$FF`-restart of the family list, and the whole-world retry from step 1 without reseeding.
3. Table indexing: `16*tier` prefix rows, `60*tier` suffix rows (no zero-skip), `16*family + 2*band` species pointers, `8*min(adjust,16) + (rand & $0F)` band picks, `(strength - strength/10) + k` size, `2*(strength/10)` layout pairs.
4. Bounds and sentinels: `wKeyWorldSlot < 20`; 4 `wKeyWorldAreas` bytes; 9 floor-info entries; `$FF`/`$FE`; a closed screen is a record whose byte 0 is `$FF`; a door whose flat ordinal matches no slot is silently dropped but still counted.
5. Blocking: a tile is solid iff `tile <= wMaxBlockingTile` (`$3D` open floor, `$3F` rooms), so overlays written into `$C198` also block (a room exit block is walkable, the exit-room door block is a wall); a press moves 16 px, the box is 16x16, and crossings wrap the screen index.
6. Persistence: record at `0x4000 + 0x195*slot`, marker `$50 + slot`, marker-checked load, bank-3 copy and its `0x7FFE` checksum.

## 13. Unknown / unconfirmed

* Meaning of screen-record header bytes 1-7 (byte 6 takes ~200 values, byte 7 is 0/1; the close-up reads bytes 6/7 as an AutomapBlocks id).
* The 84 cells that set attribute bit 3 (VRAM bank 1): no `rVBK`/bank-1 write exists.
* The 16 reserved bytes at `$CD50-$CD5F`, the four at `$CE8F-$CE92`, and the menu flag's full extent.
* Whether the 236-string name pool (`$88:461C`) is used by any display path.
* The wild-encounter step counter and entry-selection rule; per-step `wEncounterRate` semantics.
* What restores bank 2 from bank 3, since only bank 3 is checksummed.

## Sources

`re/notes/key_gen_algorithm.md`, `key_generation.md`, `keygen_module.md`, `keyworld_loop.md`, `keyworld_rooms.md`, `keyworld_tables.md`, `keyworld_levels.md`, `keyworld_exits.md`, `kwmap.md`, `kw_rooms.md`, `kw_entrance.md`, `kw_closeup.md`, `submap.md`, `submap_move.md`, `object_placement.md`, `save_format.md`; disassembly `bank60_key_worlds.asm`, `bank61_special_maps.asm`, `bank02_field.asm`, `bank12_field_objects.asm`, `bank84_key_world_debug.asm`, `src/ram.asm` (symbol addresses).
