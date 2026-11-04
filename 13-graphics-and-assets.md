# 13. Graphics and assets

Tiles, palettes, background composition, the field-sprite system, meta-sprites/OAM, fonts, the world-map atlas, monster art and the asset banks, as needed by a from-scratch port or static recompilation. ROM = `$BB:AAAA` (bank:CPU address), `file = bank*0x4000 + (addr & $3FFF)`; RAM = `$Cxxx`/`$FFxx`; VRAM = `$8000`-`$9FFF`. "Gfx id" is an index into `FieldSpriteGraphicsTable`, not a ROM address. Readings the notes mark as open or unconfirmed are flagged in §12.

## 1. Tile and palette primitives

| item | value |
|---|---|
| tile | 8×8, 2bpp, **16 bytes**; row `r` = byte `2r` (plane 0) then byte `2r+1` (plane 1); bit 7 = leftmost pixel |
| pixel | colour bit 0 = bit `(7-x)` of the plane-0 byte, colour bit 1 = bit `(7-x)` of the plane-1 byte |
| CGB palette | 4 × 2-byte LE **BGR555** (`$0BBBBBGGGGGRRRRR`) entries, 8 palettes = 64 B; transparent `$0000`, unused `$7FFF` |
| 8-bit expand | `R=(w&$1F)*255/31`, `G=((w>>5)&$1F)*255/31`, `B=((w>>10)&$1F)*255/31` |

VRAM as used by the verified screens (per-screen evidence, not a hardware map): `$8000` player sheet (tiles `$00-$0F`); `$8100-$83FF` follower sheets, one `$100` block each; `$8300/$8400/$8700` scene-object sheets (loader-dependent); `$8400-$87FF` NPC sheets, one page per map record; `$8800-$8FFF` dialogue glyph staging (`$8800 + $10*pos`); `$9000-$97FF` BG tile atlases (title and world map `vTiles2`); `$9800` BG map 0 (32×32); `$9C00` scene save area (360 B, never displayed). `graphics.md` also says "`$8800-$97FF` = OBJ tiles"; that contradicts these placements and is unverified.

All tile data, screen tilemaps and foe pictures are **Enix LZSS**: `u16 LE output_size | u8 marker | body`; a body byte `!= marker` is a literal; `marker, lo, b2` copies `length = (b2 & $0F) + 4` (if `== $13`, one extra byte gives `byte + $13`) from `offset = ((b2 >> 4) << 8) | lo`; a source at/after the output end wraps `-$1000`, a source before the start reads 0; decoding stops after `output_size` bytes (no terminator). Cartridge path: `$00:$0CF5` (spin on `$FFD6`, claim it, save `$4000`) → `$00:$0DA8` (B = data bank, DE = 3-byte header, HL = VRAM dest; sets `$FFBC/$FFBD` and `$FFC3/$FFC4` = base, `$FFC1/$FFC2` = base+size, `$FFBB` = marker) → row writer `$00:$0D04` (STAT mode-1 paced, `[hl+]`, ±`$1000` window); `$00:$0DA0` restores the bank and clears the mutex. Earlier notes interpreted this arithmetic as "row deduplication" (`$FFBB` = "terminator", match offset = "row start"); that reading is superseded.

Screen palettes (title/attract): `$E1:$1A2F` 8 BG palettes, `$E1:$1A6F` byte-identical duplicate (fade target), `$E1:$1AAF` 8 OBJ palettes. BG `540f 7fff 131f 04aa` (pal 0), `540f 7fff 131f 09d5` (pal 1), `7fff ×4` (pal 7); OBJ `7c20 7fff 14a8 0000` (pal 0), `7c20 7fff 0435 0000` (pal 1), `c611 cd5a 5ac8 44c9` (pal 2), `f05d feb1 d027 d4f0` (pal 3). `$540F` is magenta — Tara's pink UI theme; `$E1:$182D-$E1:$3B4E` is the known Tara/Cobi diff block. Palette code: `$02:$4028` fade fill, `$02:$42C0` copies into WRAM `$C49F` (offset `C<<3`), `$3A:$534F` per-frame fade steps (table `$3A:$575E`, index `$C5E9 & 3`), `$24:$4D3B` writes BCPS `$B8` then the bytes at `$24:$6CA4`. Palettes are generally not stored raw in ROM (naive BGR555 scanning yields ~90K false positives).

## 2. Background composition

BG map cell = tile id + (VRAM bank 1) attribute byte: bits 0-2 BG palette, 3 tile VRAM bank, 4 unused, 5 X flip, 6 Y flip, 7 BG-over-OBJ priority. Tilemaps are 32 bytes per row; on text screens the tile id equals the character code (`$2F` = `/`, `$41` = `A`). Recurring ids: `$0E` BG filler, `$C3` window/text fill, `$B0-$B7` window frame, `$7E/$7F/$40` frame corners, `$02` title background. Dialogue box frame: `b0/b1`…`b1/b2` top, `b6`…`b7` sides, `b3/b4`…`b4/b5` bottom, `c3` text rows, 18 characters per row. Captured menu and title attribute maps are all zero.

Cutscene/title/world-map screens compose into 20×18 buffers:

| symbol | address | meaning |
|---|---|---|
| `wScreenTileBuffer` | `$C198` | 20×18 tiles, **stride 20**, tile ids that mostly match the BG map; the buffer is not a plain copy of the map (a measurement of one field screen found 260 of 360 entries equal) |
| `wScreenAttrBuffer` | `$D000` (WRAM bank 2) | 20×18 attributes; only bits 0-2 reach VRAM bank 1 |
| `wSavedScreenAttrs` | `$D2D0` | 360-byte attribute save |
| `wScreenSavedFlag` | `$CB7E` | saved `wSpriteSlotCount` (`$CB7D`) |

Draw rules (`$00:$1E29` for 20×18, `$00:$1EA5` for 20×13):

```
origin = $9800 + (hScrollY >> 3) * 32 + (hScrollX >> 3)     ; H &= $9B
row step: HL += $20 ; then H &= $9B
per cell: write tile, then if (L & $1F) == 0: HL -= $20      ; 20-wide rect inside 32-wide rows
bc = $1412 (20x18) or $140D (20x13); text window ($C8CB bit 7): source += $64, map += $A0
attr source = tile source + $0E68, values written & $07
```

`$5F:$6DDB`, `$85:$4555` and `$02:$5EEE`/`$02:$5F22` (save/restore) reuse this arithmetic. Pixel collision `$02:$59CD` samples the 2×2 tiles at `(X>>3, Y>>3)`: normal mode blocks when **any** tile is `<= wMaxBlockingTile` (`$C192`, the cutoff itself blocks); "tall" mode (`hPlayerStateFlags $FF8C` bit 3) examines only the top two tiles and **inverts** the test (blocks when `> wMapTallTileMin`, `$C196`). Fades: `StartPaletteFade $00:$0DF2`, A bit 7 = direction (in) and bits 6-0 = delay; CGB changes the level 0→`$1F` in steps of 5 (7 changes), `frames = 7*(delay+1)`, `delay = state>>2` out / `(~state)>>2` in. States used: `$04`→14 frames, `$0F`→28, `$10`→35, `$3F`→112, `$01`→7, `$FC/$FD/$FE`→7, `$F8`→14. A fade-in pre-fills all 32 BG and 32 OBJ colours with `$7FFF` (`$0000` when `wFadeMode $C56D` bit 7, fade through black).

## 3. Field sprite graphics — `FieldSpriteGraphicsTable`

`$04:$43AC` (file `0x103AC`): 98 little-endian word pointers, gfx ids 0..97, monotonic inside each bank segment. Ids 0..`$4F` → bank `$7D` (`$4001`..`$7F07`); ids `$50`..`$61` → bank `$7E` (`$4001`..`$4AD7`); the bank is chosen from the **low** id byte (`$04:$434B`: `CP $50 / INC B`). Entries 0-7: `01 40`→`$4001`, `fa 40`→`$40FA`, `e1 41`→`$41E1`, `bd 42`→`$42BD`, `8e 43`→`$438E`, `58 44`→`$4458`, `1e 45`→`$451E`, `c2 45`→`$45C2`.

| id | owner | sheet | tiles | palette |
|---|---|---|---|---|
| 0 | Cobi (blue hero) | `$7D:$4001` | 16 (256 B) | 18 |
| 1 | Tara (green hero; the player here) | `$7D:$40FA` | 16 (256 B) | 19 |
| 2-97 | NPCs / field objects | `$7D:$41E1`.. or `$7E:$4001`.. | varies | `FieldSpritePaletteIndex[id]` |
| 5 | barn person (worked example) | `$7D:$4458` | 14 (224 B) | 1 |

Tara is id 1 because a Tara new game sets story flag 0 (`hPlayerSpriteVariant $FF8A`) at `SetGameBegun $07:$68C1`; Cobi stays the companion. Palette bytes confirm the pairing (`7DA0` = blue → id 0, `2E0A` = green → id 1). Sheet sizes over the 98 objects: 14 tiles ×55, 16 ×15, 12 ×7, 4 ×7, 15 ×7, up to 32; a sheet composes as 2×2 blocks in **TL, TR, BL, BR** order. Example id 5 at `$7D:$4458`: header `e0 00 01` (224 B = 14 tiles, marker `$01`), tile 0 = `00 00 0e 0f 1f 1f 3f 3f 3f 3e 7f 7c 7f 74 7f 74`, a 16×16 person.

Loader `DecompressGraphicsTemp0ToTemp4 $04:$431F`: 16-bit id = `(hTemp1<<8)|hTemp0`; `hTemp2` chooses the path (`0` = monster → `MonsterSpriteTable $04:$4EAA`, non-zero = field); `hTemp3` = destination OBJ palette slot; `hTemp4/hTemp5` = VRAM page. Map-object records (11 B, bank `$69`, loaded by `LoadMapObjectsForScreen $69:$4001`, per-record copy at `$69:$40FC`) carry `[0]` VRAM page, `[1]` gfx table (`0` monster / `!=0` field), `[2]` gfx number = low id (also the palette index), `[3]` high id, `[4]` behaviour type, `[5]` X, `[6]` Y, `[7]` palette slot, `[8]` facing, `[9]` tile offset, `[10]` talk byte. The sheet is decompressed to `page:00`; part tile indices address it directly, and the VRAM tile base is `record[9] = (page - $80) * 16` (verified for 556/557 objects, pages `$84-$87` → `$40`/`$50`/`$60`/`$70`; the exception is `page $FE / group 0 / table $FF`). Scene sheets arrive by field command instead (`vTiles0+$400` = tile `$40`, or `vTiles0+$300` = tile `$30`).

Per-id palette indirection: `FieldSpritePaletteIndex $04:$4A46` = 98 B mapping gfx id → palette number 0..20 (first 8 = `18,19,6,7,2,1,4,7`); `FieldSpritePalettes $7E:$4B15` = 21 palettes × 4 BGR555 words. Record byte `[7]` picks which **hardware OBJ slot** (0-7) receives the 8 bytes, while the colours are keyed by the gfx id (the player uses slot 0). That is why there are 21 palettes and not 8.

```
p0  0000 6bff 663f 0800   p7  0000 6bff 027f 0800   p14 0000 3afd 0533 0800
p1  0000 6bff 001f 0800   p8  0000 6bff 662c 0800   p15 0000 4f5d 1415 0000
p2  0000 6bff 0553 0800   p9  0000 6bff 031d 0800   p16 0000 5efd 39b2 0000
p3  0000 6bff 7000 0800   p10 0000 037f 0340 0800   p17 0000 6bff 6b2a 0800
p4  0000 6bff 03e0 0800   p11 0000 7f1f 027f 0800   p18 0000 6bff 7da0 0000  Cobi
p5  0000 6bff 5ab4 0800   p12 0000 035f 026e 0800   p19 0000 6bff 2e0a 0000  Tara
p6  0000 6bff 6017 0800   p13 0000 767f 3d58 0800   p20 0000 6bff 7ec5 0800
```

`field_palettes.md` annotates 18 as "Tara" and 19 as "Cobi"; the later palette-byte correction above supersedes that.

## 4. Meta-sprites, OAM and the scene object

`wObject5` `$CBCF`, 8 bytes, immediately after the five 16-byte slots (`$CB7F-$CBCE`) and before the story flags `$CBD7`: +0 bit 7 shown / bit 6 special-map marker gate; +1 tile offset added to every part tile (8-bit); +2 bits 0-6 set index into `$7F:$7011`, bit 7 animate; +3 attribute XOR (bits 0-2 = OBJ palette); +4/+5 X/Y, origins `scroll + ((X+8)&$FF)` / `((Y+$10)&$FF)`; +6 animation hold counter; +7 animation step. Draw chain: `DrawFieldSprites $12:$6EC6` (`ld de,$CBCF` at `$12:$6ECC`) → `$7F:$700A` (`ld de,$7011 / call $7065`) → `$7F:$7065`; animator `$12:$6F17` (helpers `$12:$6F96`, `$12:$6FBE`; tables `$12:$6FF2-$12:$704A`). `DrawFieldSprites` is far-called from `$02:$4B44/$4B7C/$4B98/$4BB7/$4BCD/$4D6D`, `$24:$5687`, `$F1:$5B9E`, `$F2:$43C9`.

Sets and frames: 42 word pointers at `$7F:$7011`, ending where `DrawMetaSpriteAt` starts (`$7065`); scene set index 0-41. `set_ptr + 2*subindex` → the frame's word pointer; a frame is 4-byte parts `{y signed, x signed, tile, attribute}` closed by **one** `$80` byte. Totals: 130 frames, 2004 parts, data `$7F:$72E3-$7F:$7B95`. Frame counts: 25 sets have 1 frame; `$01 $16 $1A` 2; `$17` 3; `$12 $13 $1E` 4; `$23 $24 $25` 5; `$18 $19 $1B $1C $29` 6; `$20` 7; `$1F` 32 (only frames 0-6 reachable).

Animated sets, one hold count per step (`$FF` wraps to step 0): `$13` `08 08 08 08 ff`; `$1A` `08 08 ff`; `$17` `07 07 09 ff`; `$1E` `04 07 07 04 ff`; `$18` `20 20 ff`; `$1F` `0e 0e 0e 0e 0e 0e 0e 36 0e 0e 0e 40 ff` with remap `$700E` = `00 01 02 01 02 01 02 00 03 04 05 06`; `$20` pairs `00 1e, 00 05, 01 04, 02 05, 01 04, 00 05, 01 04, 02 05, 03 04, 04 05, 03 04, 02 05, 05 04, 06 05, 05 04, 02 05, 01 04, 00 05` then `ff ff` (holds the last). Exactly these seven sets animate; field commands select them with `$93 $97 $98 $9A $9E $9F $A0`.

OAM builder `$7F:$7065`: refuses once `hOamNextEntry ($FFB1) >= $27`, stops at 40 entries (`$28`), and adds `$FFD4/$FFD5` to Y and `$FFD2/$FFD3` to X — no writer for those words exists in the ROM, so the addend is always 0.

```
y = originY + signed part[0]   drop if the high byte != 0 or the low byte >= $A8
x = originX + signed part[1]   drop if the high byte != 0 or the low byte >= $B8
entry = (y & $FF, x & $FF, part[2] + wObject5[1], part[3] ^ wObject5[3])
```

If the x test fires after y was already stored, y is zeroed and the pointer backed up, so the entry is reused. Paths: plain `$70C1`; flipped `$7137` (`x = (origin_x-8) - part.x`); clipped `$71AF` (y cull moves to `$B8`; window mode 1 drops `y < $34`, mode 2 drops `y >= $71`, other modes keep all; then the hide test); clipped+flipped `$7230`. Hide test (`$7F:$4312`, `$25:$43E4`, 54 B): `by = (entry_y+hScrollY-$0C)&$F8`, `bx = (entry_x+hScrollX-$04)&$F8`, tile = `[$9800+by*4+(bx>>3)]`, part dropped when `>= hSpriteHideTile $FFBA`. The same 582-byte rule set exists at `$25:$419E`, `$26:$419E`, `$27:$419C`, `$7F:$40CC`.

OAM entry = 4 bytes `(y, x, tile, attribute)`; attribute bits 0-2 OBJ palette, 3 tile VRAM bank, 5 X flip (`$20`), 6 Y flip (`$40`), 7 OBJ-over-BG priority (captured values `$01` and `$33`). The x/y bytes are **raw OAM**, so the top-left appears at `(x-8, y-16)`; the ROM's arithmetic ends at OAM = `OBJ_X+$10` / `OBJ_Y+$20` at scroll 0, i.e. the record X/Y is a **bottom-centre** anchor covering `OBJ_X-8..+8` and `OBJ_Y-$10..OBJ_Y`. Flipping mirrors part positions *and* pixels. On GBC the **lower OAM index wins**, so a renderer must paint the highest index first.

Field-command graphics: `FieldCommandSpriteTable $12:$4B04C`, 88 B = 22 records of 4 bytes `{gfx word, set/palette selector, unused}`; `SharedOBJPalettes $7E:$4BBD` (file `0x1F8BBD`), 304 B = 38 CGB OBJ palettes × 8 B; loader `$12:$6E0B` (dest `vTiles0+$400` = tile `$40`, attr `$04`, palette slot `$C4FF`) and `$12:$6E61` (dest `vTiles0+$300` = tile `$30`, attr `$03`, slot `$C4F7`). Command decompressed sizes, ids 0-21: 64, 64, 64, 64, 64, 64, 256, 128, 64, 64, 64, 128, 192, 512, 512, 64, 64, 96, 80, 64, 512, 512. Command 1 = `$7E:$4F22` (`40 00 02 …`, 64 B = 4 tiles `$40-$43`); the Homecoming example draws OAM `($30,$68) ($30,$70) ($38,$68) ($38,$70)`, tiles `$40-$43`, attribute `$04` = 16×16 at `(96,32)` in palette 4 (`SharedOBJPalettes[8*$0A]` = `00 00 5d 4f b0 2d 00 00`).

## 5. Sprite slots (map NPCs)

`wSpriteSlots` `$CB7F` holds five 16-byte records, count `wSpriteSlotCount $CB7D`, slot 4 ends `$CBCE`; scripts call slot *N* `wObjectN` (`$CB8F..$CBBF` for 1-4). Fields: +0 type (0-5), +1 `OBJ_SET_MODE`, +2/+3 `OBJ_SPRITE_ID` low/high, +4/+5 home X / record Y, +6 `OBJ_ATTR` (palette), +7 `OBJ_STATE` (facing); record bytes `[7]` and `[8]` map to `OBJ_ATTR` and `OBJ_STATE`, and byte `[8]` doubles as the graphics loader's palette slot, +8 `OBJ_TILE_OFFSET`, +9 `OBJ_ANIM_COUNTER`, +A move byte, +B/+C `OBJ_X`/`OBJ_Y`, +D `OBJ_FLAGS` (bit 1 stop counter, bit 2 frame from counter), +E `OBJ_SUBINDEX` (bit 7 = X flip → attr bit 5), +F talk byte.

Behaviour (`UpdateSpriteSlots $04:$456D`, dispatch words at `$04:$4576`): 0 still `$4592`, 1 none `$4704`, 2 wander L/R ±`$20` around home X `$4606`, 3 wander four-way `$4705`, 4 frame loop table `$48D6` `$4863`, 5 frame loop table `$48FA` `$486E`. Frame picker `$04:$45A7`: `c = (flags & 4) ? (counter>>3)&1 : (counter>>5)&1`; `OBJ_SUBINDEX = (state == 3) ? $82 + c : 2*state + c`. Draw `$04:$44CE` sets `hTemp0 = OBJ_SET_MODE`, `hSpriteAttrXor = OBJ_ATTR & 7`, `hSpriteTileOffset = OBJ_TILE_OFFSET`, origin `OBJ_X+8+hScrollX` / `OBJ_Y+$10+hScrollY`, and `hSpriteSubIndex = OBJ_SUBINDEX` (bit 7 → attr XOR `$20`, byte `& $7F`).

| condition | set table | index |
|---|---|---|
| `OBJ_SET_MODE != 0` | `$7F:$4008` (98 words) | full low byte |
| high byte non-zero | `$27:$401E` (127 words + attrs `$411C`) | low `& $7F` |
| low bit 7 set | `$26:$401E` (128 words + attrs `$411E`) | low `& $7F` |
| else | `$25:$401E` (128 words + attrs `$411E`) | low `& $7F` |

Banks `$25-$27` have 6 frames per set; the 98-set table has 3 for sets 71/72, 8 for set 84, else 6; `$27` sets 117-123 and 127 are empty, `$25` sets 0 and 1 share a frame list. Example frame: `f0 f8 00 00 | f0 00 01 00 | f8 f8 02 00 | f8 00 03 00 | 80`. Talking (`CheckMapInteractionOnA $87:$42A0`, scan `$87:$4709`): talk byte `$FF`→index 8; `$FE`→9/group 0; `$FC`→9/2; `$FB`→9/3; `$FA`→9/8; otherwise group = byte and the index comes from `hMapId` (`<$20`→1, `<$30`→2, `<$48`→3, `<$70`→4, `<$A0`→5, `<$A8`→6, else 7), dispatched by `$13:$405C`.

## 6. Player and followers

Player (`LoadPlayerSpriteGraphics $04:$4B2D`; override via `hPlayerSpriteOverride $FF93` bit 7): id = story flag 0 (`hPlayerSpriteVariant $FF8A`) → 0 Cobi / 1 Tara (this edition: 1); destination `$8000`, 16 tiles = 256 B, tiles `$00-$0F`, palette slot 0; drawer `DrawPlayerSprite $04:$4C96` (body ends `$4D43`); `sub = selector*2 + bit5(hPlayerAnimCounter)`, facing 3 → pair 1 plus attr XOR `$20`. Frames live in `MetaSprites7FTable $7F:$4008` (set 0 Cobi `$7F:$4348`, set 1 Tara `$7F:$43BA`), one `(y,x,tile,attr)` per 4-byte group, `80` = end:

```
f0  f0 f8 00 00 | f0 00 01 00 | f8 f8 02 00 | f8 00 03 00 | 80
f1  f1 f8 00 00 | f1 00 01 00 | f9 ff 02 20 | f9 f7 03 20 | 80
f2  f0 f8 04 00 | f0 00 05 00 | f8 f8 06 00 | f8 00 07 00 | 80
f3  f1 f8 04 00 | f1 00 05 00 | f9 f8 08 00 | f9 00 09 00 | 80
f4  f0 f8 0a 00 | f0 00 0b 00 | f8 f8 0c 00 | f8 00 0d 00 | 80
f5  f1 f8 0a 00 | f1 00 0b 00 | f9 f8 0e 00 | f9 00 0f 00 | 80
```

Tiles are `TL, TR, BL, BR`. Frames 0 and 1 share tiles `0,1,2,3`: the walk step is an OAM X flip (`attr $20`) plus a one-pixel left shift (`x = $FF/$F7`) of the leg tiles, never new tile art. f2/f3 = side `4,5,6,7` / `4,5,8,9`; f4/f5 = up `10,11,12,13` / `10,11,14,15`. Frame 5 has parts at y `-15`/`-7` (17 rows tall). Direction map (inferred): 0 down → 0,1; 1 left → 2,3; 2 up → 4,5; 3 right → 2,3 flipped.

Followers: mode 0 draws `DrawPlayerAndFollowers $04:$4BCF` = `DrawPlayerSprite $04:$4C96` + `DrawPartyFollowerSprites $04:$4D43`. **The player is 4 OAM entries and each follower is 4** (up to 3 members). Skip a member when `hFieldDrawFlags` bit `0x02 << member` is set; palette `hSpriteAttrXor = (3-b)+1 = 4-count+member` (a full party uses slots 1,2,3); tile offset `$10`, plus `$10` per member (`$10`/`$20`/`$30`); pose `UseSpecialSpritePoseAtPosition` forces pair 2, else facing 3 → pair 1 + `attr |= $20`, else pair = facing byte (0 down, 1 right, 2 up); frame `pair*2 + bit5(hPlayerAnimCounter)`; origin `X = rec[1]+$08+hScrollX`, `Y = rec[2]+$10+hScrollY`, giving OAM `rec X+$10` / `rec Y+$20`.

**Sheet rule** (`LoadPlayerAndFollowerSpriteGraphics_Followers`, bank `$00`): read the species word and `MON_STATUS` from SRAM (`rRAMG = $0A`). Alive → `MonsterSpriteTable[species]` `$04:$4EAA`, 16 tiles = 256 B → `vTiles0+$100+i*$100` (`$8100`/`$8200`/`$8300`), palette `$27:$7328 + species*8` → slot `4-count+i`. Dead (`MON_STATUS` bit 7) → `$FFFF` in the list, sheet `FallenFollowerCoffinTiles $7E:$545E`, palette `SharedOBJPalettes[25]`. The frame **set** is separate from the sheet: low `& $7F` of the sprite-id word at `wPartyList+3+2*member`, dispatched `high != 0` → bank `$27`, low bit 7 → `$26`, else `$25`; a high byte of `$FF` selects scene set `$19` through the 42-set table with the coffin tiles. Verified OAM for a 3-member party: player `(17,104,0a,00) (17,112,0b,00) (25,104,0e,00) (25,112,0f,00)`, then `(41,112,1b,21) …`, `(57,112,2b,02) …`, `(64,104,30,03) …` (coffin) — the cartridge's first 16 entries exactly. Field OAM order: player, followers, sprite slots, trigger marker, bit-6 scene marker, all sharing one `hOamNextEntry` capped at `$28`.

## 7. Fonts

| item | value |
|---|---|
| grid | `$1F:$4010`-`$1F:$500F`, ROM file `0x7C010` |
| size | 4096 B = **256 glyphs × 16 B** (2bpp 8×8) |
| layout | `glyph(c) = $4010 + (c>>4)*$100 + (c&$0F)*$10` (identity: `code*16`); each row is `db $FF, $xx` |

Each row is plane 0 = constant `$FF` (paper) and plane 1 = ink mask, so `shade = 1` paper and `3` ink; decoding plane 1 alone reads the glyph, and nothing is transparent (the whole cell is painted). Example: code 13 `'D'` = `ff f8 ff 84 ff 82 ff 82 ff 82 ff 84 ff f8 ff 00`. Charset: `$00-$09` `0-9`; `$0A-$23` `A-Z`; `$24-$3D` `a-z`; `$3E-$44` contractions; `$45` `*:`, `$46` `(`, `$47` `)`; `$48-$4F` solid; `$50-$5E` pictograms `[1]-[15]`; `$5F-$8C` solid `$FF`; `$8D/$8E` combining top marks (overstrike: cursor back one tile, `$00:$0B46`, clear bit 1 of the 4th byte); `$8F-$9F` symbols; `$A0-$AF` arrows/symbols (star `$AC`); `$B0-$B8` symbols (ball `$B8`); `$B9-$FF` empty. Additional font facts: 126 of 256 cells blank, codes above `$B8` are interface tile ids, `$48-$8F` unused. Controls: `$F0` end, `$F1` newline (`d7c5:c6 = $0120`), `$F7` wait, `$F9xx` variable (`00` = player name).

Dialogue renderer `$24:$7045`-`$24:$7155`: code → `HL = $4010` grid address (via `SWAP A`), destination `$8800 + d7c5:d7c6`, `B = $1F`, `C = $10`, `CALL $00:$0B2B` (bank-switched 16-byte copy), then `d7c3:c4 += 1` and the VRAM cursor `+= $10`. Tile ids are **positional** — there is no static code→tile table. The base is `$80` in `text_classifier.md` (`$C919 = $80` at `$24:$64C2`, not byte-verified), but a live copy trace saw copies landing on tiles `$D0-$D4` (`$8D00 + $10*pos`), and the two readings are not reconciled. `graphics.md`'s claim that the font is ASCII-ordered at VRAM tiles `$20-$7E` belongs to the **debug/viewer** loader (`$01:$6A0C`+, writers `$01:$6A7E/6A98/6AB2` = nibble+`$10`, destination table `$01:$6A72`), not to dialogue; the "character sheet" seen in the hidden tile viewer (`300:S:12,1900:A:12`) is retracted — those tiles are title-screen gradient decorations. At title time VRAM `$8000-$8FFF` holds 256 2bpp tiles (122 non-empty; tile `$02` = background filler, `$9B` = window edge). Bank `$01:$4AA4` copies an 8-byte stub (`$01:$4ACC` = `20 05 f0 92 b7 28 ef 3e 04`) to `$C49F` and executes it from WRAM.

## 8. World map screens and atlas

Assets live in banks `$5D`/`$5E` and `$A1`, **not** `$E1` (an earlier world-map hint in the notes said `$E1`; that is wrong). The BG map uses **signed (`$8800`) tile addressing**: tilemap byte `t` → `$9000+16t` for `$00-$7F`, `$8800+16*(t-$80)` for `$80-$FF`.

| asset | location | form | destination |
|---|---|---|---|
| overview land tiles | `$5D:$4001` | LZSS 312→1024 (64 tiles) | `vTiles2` `$00-$3F` |
| overview frame tiles | `$5E:$4001` | LZSS 558→768 (48 tiles) | `vTiles2+$500` = `$9500`, `$50-$7F` |
| close-up terrain | `$5D:$43AE` | LZSS 439→2048 (128 tiles) | `vTiles2` `$00-$7F` |
| overview palettes | `$5D:$4139` | 128 B raw (16 palettes, only 0 copied) | `wBGPaletteBuffer` = `$318c $7fff $5294 $0000` |
| BG palette 1 | `$5E:$422F` | 8 B raw | `wBGPaletteBuffer+8` = `$014d $6bff $2a55 $0000` |
| overview tile rect | `$5E:$4238` | 360 B raw (20×18) | `vBGMap0` |
| 12×12 centre fill | `$A1:$5808` | 144 B, all `$34` | `vBGMap0+$64` |
| view table / silhouettes | `$A1:$533C` (11×8 B) / `$5D:$41B9-$43AC` | raw | 12×12 centre |
| cell table / grids | `$A1:$497C` (11×4 B) / `$5D:$45A5-$7660` (12525 B) | raw | 5×5 blocks per screen |
| Automap blocks | `$5E:$43A0` | 7025 B (281 × 5×5) | key-world close-up |
| close-up palettes | `$5D:$4565` | 8 × 64 B | pal 0 `$014d $6bff $2a55 $0000`, pal 1-7 `$294a $7fff $4a52 $0000` |

`WorldMapViewTable` entries are `{dw rect ptr ($5D); rows, width; band_start, 0,0,0}`. Regions (rows×cols / band): 0 8×8/`$20`, 1 8×8/`$30`, 2 12×12/`$48`, 3 12×12/`$70`, 4 3×4/`$A0`, 5 6×6/`$A8`, 6 2×3/`$B0`, 7 5×5/`$B8`, 8 2×1/`$C8`, 9 2×1/`$D1`, 10 1×2/`$DA`.

Attributes are **generated**, not stored (`$A1:$57BE`): all 1024 bytes `$01` except rows 3-14 × columns 4-15 = `$00`; the visible 20×18 slice is 216 × `$01` + 144 × `$00`; no flips and no bank switching. Geometry (`$A1:$5765`, B = cols, C = rows): `wCursorCellY = 9-rows/2`, `wCursorCellX = 10-cols/2`, `HL = $9800 + 32*Y + X`; inside the 12×12 box the block origin is `(6-cols/2, 6-rows/2)` — **not** `(12-dim)/2`, which is off by one cell for the odd regions 4-10. Close-up (`$A1:$1061`) is a static screen (no scroll, no cursor): it fills `vBGMap0` with tile `$57`, clears all attributes, and writes one cell per grid tile (5×5 per screen, left-to-right then top-to-bottom, `$57` outside the region). `SetUpCloseUp $A1:$1635` computes `cell_col = hPlayerX/32+1`, `cell_row = hPlayerY/32+2`, `screen_col = hMapScreenX-2`, `screen_row = hMapScreenY-2` (the biases carry), so the player's own cell always lands on BG cell (9,8).

Runtime: `TryOpenWorldMap $A1:$4427` needs no fade, no text window, no field action and an idle player; a key world always opens, otherwise `hMapId >= $20`. Bands `$20-$2F`→0, `$30-$47`→1, `$48-$6F`→2, `$70-$9F`→3, `$A0-$A7`→4, `$A8-$AF`→5, `$B0-$B7`→6, `$B8-$C7`→7, `$C8-$D0`→8, `$D1-$D9`→9, `$DA+`→10. States (`$A1:$1046`, on `wWorldMapState & 7`): 0 BlankPalettes, 1 DrawOverview, 2 OverviewInput, 3 BlankPalettes, 4 DrawCloseUp, 5 CloseUpInput, 6 ReturnToField. RAM: `wModeState $C5DC`, `wWorldMapState $C5DD`, `wWorldMapRegion $C944`, `hMapId $FF90`. Overview: B whites out to the field, Select opens the close-up; close-up: B or Select closes (there is no way back).

Ribbon (`$A1:$3381`): `hMapId + $0A` indexes `StringTable_System` category 0; it pre-clears 11 tiles at `vTiles1` to `($FF,$00)`, centres in 13 cells (`pad = ($0D-c)/2`), and writes 11 tile ids `$80-$8A` to `vBGMap0+$204` (row 16, columns 4-14). Row 16's attribute is `$01`, i.e. BG palette 1 (cream `$6BFF`, ink `$0000`); glyphs come from the `$1F:$4010` grid with glyph number = character code.

Markers (OAM through `MetaSprites7FTable_2`), drawn in this order: player (`$A1:$5479`), locations (`$A1:$565F`), key-world objects, goal (`$A1:$4A6B`). Player = set `$08`, 16×16, four entries, blinking on `wFrameCounterLo` bit 5 (32 on / 32 off), top-left `x = 8*(wCursorCellX+screenX)+6-8`, `y = 8*(wCursorCellY+screenY)+6-16` (oracle `(62,46)`). Goal = set `$26`, 8×8, tile `$10`, attr `$01`, at `8*cellX+8*(byte>>4)` / `8*cellY+8*(byte&$0F)`; `$A1:$59D6` byte 0 per region = `00 76 b4 b4 10 00 01 44 01 00 00`, byte 1 always `$44` (oracle `(48,40)`). Location markers use **raw pixel offsets** (no ×8, no +6) added to `8*cell`; region 0's `02 11 09 11 29` → `(65,49)`, `(65,81)`. The player marker is drawn first, so it holds the lowest OAM indices and wins; composite back-to-front. Close-up: the player is pinned at `(70,54)`; region markers go to `40*dx+8*((P>>4)>>1)-8*cell_col` / `40*dy+8*((P&$0F)>>1)-8*cell_row`, tile `$20`, attr XOR `$01`, set `$28`; there is no area name on the close-up.

## 9. Monster and foe art

| set | table | content |
|---|---|---|
| map monster sprite | `MonsterSpriteTable $04:$4EAA`, 383 dfars | 16-tile (256 B) sheets, banks `$20-$23` + `$91`; 315 pointers → 311 distinct sheets; palettes `MonsterSpritePalettes $27:$7328` (384 × 8 B BGR555) |
| battle portrait | `MonsterPictureTable $38:$4001`, 383 dfars | 576 B = **36 tiles = 6×6 = 48×48 px**, banks `$74-$7B`; palettes `MonsterPaletteTable $7B:$4209` (383 × 16 B); per-tile mask `MonsterAttributeMapTable $38:$447E` (36 B blocks, bank `$7B`) |

`LoadMonsterPicture $00:$1FE3` uses the species word itself as the index (no translation table): `HL = species*3` into the picture table, then `DecompressToVRAM`. Species 383 (`?`) and 384 (no name) have no entry (383 = 384-1). 315 distinct picture streams serve 383 entries (67 aliases; `$74:$4001` is the placeholder for unused slots; species 2 and 27 share `$74:$40F1`), and every portrait expands to exactly 576 bytes. Palette 0 is `[shade, white, main, black]` for all 383 entries (word 1 `$7FFF`, word 3 `$0000`); palette 1 is a real second palette for 227 of the 315 pictures and a flat fill (`$7FE0`/`$7C1F`) for 88. The 36-byte attribute block only ever contains 0 and 1 across the whole cartridge — purely a per-tile palette select (1839 of 11340 tiles pick palette 1), never flips or priority.

Battle placement: `LayoutTileBlocksForBattleFoeCount $31:$72CC` (blocks at `vTiles2+$140/$380/$5C0`); `LoadBattleMonsterPictureAttributes $31:$7321` stamps each foe's 36 attribute bytes at `vBGMap0+$E1/$E4/$E7/$EA/$ED` (tile row 7, columns 1/4/7/10/13) with palette base `C = 1/3/5` (palettes 1+2, 3+4, 5+6). Family icons: `FamilyIconTiles $16:$7ACD`, 11 raw 16-byte tiles. The pedigree/party picture path is `$03:$4846` → `$1D:$682A` → `$1D:$6899` (origins 16,120 / 48,104 / 48,136; tile offsets 0/`$10`/`$20`; attr XOR 0/1/2). The 48×48 portraits are battle-only; the field draws the 16-tile sheets.

## 10. Title screen and asset banks

Title screen (bank `$E1`), loaded by `TitleOpening_LoadTitle $07:$5CD8` via `DecompressToVRAM $00:$2478`: `TitleLogoTiles $E1:$4E67` (1438→2048 = 128 tiles) → `vTiles2` `$00-$7F`; `TitleKeyAndTarasAdventureTiles $E1:$49DA` (1165→2048 = 128 tiles) → `vTiles1` `$80-$FF`; `TitleScreenTilemap $E1:$582B` (152→360, 20×18) → BG map via `wScreenTileBuffer`; `TitleScreenAttrMap $E1:$58C5` (80→360) → attributes; title BG palettes `$E1:$5A2F` (64 B) → `wBGPaletteBuffer`. Verified exact against VRAM: `$E1:$49DA` == `$8800-$8FFF`, `$E1:$4E67` == `$9000-$97FF`, `$E1:$582B` == the visible 20×18 map. The streams `$7D:$40FA/$7D:$4001/$7D:$438E` are **not** title assets.

| bank | contents |
|---|---|
| `$00` | home: copy, LZSS (`$00:$0CF5`/`$00:$0DA8`), `$00:$2478`, screen writers `$00:$1E29`/`$00:$1EA5` |
| `$04` | `FieldSpriteGraphicsTable`, slots, player/follower loaders, field commands |
| `$02`, `$0F`, `$12`, `$5F`, `$73`, `$85` | field states and scene code (tables in `$12`) |
| `$16` | menu gfx, `FamilyIconTiles $16:$7ACD`, keyboard tables `$16:$19C0` |
| `$1F` | the 256-glyph font grid `$1F:$4010` |
| `$20-$23`, `$91` | 16-tile monster map sheets |
| `$25/$26/$27` | field meta-sprite sets, `MonsterSpritePalettes $27:$7328` |
| `$31`, `$33`, `$38` | battle layout; keyboard map `$33:$0800`; monster picture/attr tables |
| `$5D/$5E`, `$A1` | world-map tiles/silhouettes/grids, Automap blocks; world-map machine |
| `$69` | map object records (11-byte) |
| `$74-$7B` | 48×48 foe pictures (+ palettes `$7B:$4209`) |
| `$7D/$7E` | field sheets and streams (+ `$7E:$4B15` palettes, `$7E:$545E` coffin) |
| `$7F` | meta-sprite tables (42 scene sets, 98 Sets98) and OAM builders |
| `$E1` | title/attract screen and palettes; Tara/Cobi diff block `$E1:$182D-$E1:$3B4E` |
| `$F1/$F2` | gift-menu/link and game-mode-8 code — no tile assets located |

## 11. Exact-match checklist

- **Tiles**: 16-byte 2bpp, plane-0 byte then plane-1 byte per row, bit 7 leftmost; 2×2 composites in TL, TR, BL, BR. Flips are OAM attributes and are never baked into the art.
- **Palettes**: copy the 21 field palettes, 8 title BG + 8 title OBJ, world-map BG palette 0 (`$318c $7fff $5294 $0000`), BG palette 1 (`$014d $6bff $2a55 $0000`) and the 8 close-up palettes verbatim (BGR555 LE); OBJ colour 0 is transparent. The 128-byte overview table holds 16 palettes but only entry 0 is copied.
- **Indirection**: field palette by gfx id, hardware slot by record `[7]`; scene objects by `SharedOBJPalettes[selector]`; followers by species; battle foes by species with base 1/3/5 plus the per-tile attribute bit.
- **OAM**: bottom-centre anchor (`OBJ_X-8..+8`, `OBJ_Y-$10..OBJ_Y`), raw OAM bytes, cull `y >= $A8`/`x >= $B8` (or `y >= $B8` clipped), hide test against `$FFBA`, 40-entry budget, stop at `$80`. Priority: lower OAM index wins; OBJ-vs-BG by attribute bit 7; BG priority by its attribute map. Field order: player, followers, slots, trigger marker, bit-6 marker.
- **Animation**: `pair*2 + bit5(hPlayerAnimCounter)` for player and followers; slots use the 32- or 8-tick counter bit; the down-walk frame reuses the standing tiles with flipped/shifted legs.
- **Text**: glyph = `$1F:$4010 + code*16`; dialogue tile ids positional; `$F0`/`$F1`/`$8D`/`$8E` as in §7.
- **Screen**: 20×18 stride-20 buffers, `$9800 + (scrollY>>3)*32 + (scrollX>>3)` with `H & $9B`, the 20-wide wrap, the 20×13 window variant with its 5-row shift, and generated attribute maps.

## 12. Unknown or unconfirmed

- `$E1:$45A7` (name-entry screen-def) is only partly decoded (`03 xx 0f` record semantics open); the keyboard's BG palette 0 `3160 56b5 62e8 0000` was not found raw in ROM.
- The dialogue tile base is `$80` (`$C919`, not byte-verified) or `$D0` (observed); the font's bit layout was once reported unreadable, but the `plane 0 = $FF` / `plane 1 = ink` decode is verified on the ribbon.
- `field_palettes.md`'s "p18 = Tara / p19 = Cobi" is superseded by the palette-byte evidence (id 0 = Cobi = 18, id 1 = Tara = 19).
- Whether any *reachable* meta-sprite frame exceeds 40 OAM parts is unresolved: the sources disagree — `meta_sprites.md` reports 25 of 42 scene sets with 40+ part frames (max 64 in set `$1F` frame 7), while a later measurement finds the reachable maximum at 9 parts and the four field set tables at ≤20. Set `$1F` frames 7-31 and set `$18` frames 2-5 are unreachable through any record.
- The facing→frame-pair map is inferred, not traced; `hPlayerSpriteOverride` (`$FF93` bit 7) triggers, the monster path of `DecompressGraphicsTemp0ToTemp4`, and the `$FFD2-$FFD5` addends (no writer in ROM) are documented from control flow only.
- `graphics.md`'s "`$8800-$97FF` = OBJ tiles" is unverified and inconsistent with the field placements in §1.

## Sources

re/notes/graphics.md · re/notes/tile_format.md · re/notes/scene_render.md · re/notes/meta_sprites.md · re/notes/sprite_slots.md · re/notes/object_graphics.md · re/notes/field_palettes.md · re/notes/monster_sprites.md · re/notes/foe_art.md · re/notes/wm_atlas.md · re/notes/wm_font.md · re/notes/world_map.md · re/notes/font_and_tileviewer.md · re/notes/text_classifier.md · re/notes/title_screen.md · re/notes/player_sprite.md. Follower draw/loader addresses were cross-checked against the reference disassembly's
section comments and a session investigation of the follower path.
