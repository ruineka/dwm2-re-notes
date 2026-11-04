# 5. Field: maps, screens, objects, warps, collision

## MapTable (bank `$11`)

`MapTable` is 256 `u16` pointers at **file `0x444B8`** (bank `$11`, CPU
`$44B8`), indexed by `hMapId`. Each points at a **map record** in the same bank.
54 entries are `$0000` (no map): `30, 31, 39, 44, 70, 71, 105–111, 156, 158,
159, 165–167, 183, 198, 199, 207, 216, 225, 227–255`. 183 distinct records
(19 aliases, e.g. entries `69, 104, 157, 164, 175, 178, 197, 208, 217, 226`
alias `MapRecord29`).

### Map record

A `dfar`-driven struct; `dfar X` = `{dw X, db BANK(X)}` (3 bytes):

| Off | Size | Field |
|---:|---:|---|
| 0 | 3 | tileset stream (`dfar`) → VRAM `$9000` |
| 3 | 3 | palettes (`dfar`) |
| 6 | 1 | width in screens |
| 7 | 1 | height in screens |
| 8 | 1 | blocking cutoff (→ `wMaxBlockingTile`) |
| 9 | 1 | interaction tile id (0 = none, → `wMapHeaderByte7`) |
| 10 | 1 | field-event kind (low nibble → animation jump table) |
| 11 | 1 | encounter rate (0 = none, else index into the encounter-rate table; the game ORs `$80` into WRAM) |
| 12 | 1 | move type (0 none, 1–7 hurt-floor kinds) |
| 13 | 1 | sprite kind (high nibble = special-tile set, low nibble 1 = follower sprite) |
| 14 | 1 | tall-tile minimum **or** event tile (depends on sprite kind's low nibble) |
| 15 | 1 | unread (always 0) |
| 16 | 2 | variant flag (`dw`): always `wStoryFlags + $60…$69`, i.e. story flags 768–847 (histogram `$CC3B` 44×, `$CC3A` 32×, `$CC37` 30×, `$CC39` 21×) |
| 18 | 6N | N variants of `{dfar screens, dfar attrs}` |

Size = `18 + 6N`. **N is not stored**; recover it from the distance to the next
record (`(next − this − 18) / 6`). Observed N: `1×7, 2×23, 3×44, 5×64, 7×15,
8×28, 9×1, 13×1`. `screens`/`attrs` are `width × height` `dfar` arrays naming
per-screen compressed 20×18 streams (below).

Verified examples:

* **Map 0** (overworld): `W=3 H=4 cutoff=$4E`, 8 variants, flag `$CC37`;
  screen (1,1) is the barn `$46:4451`, screen (2,2) the farm `$46:49F6`.
* **Map 29 ("Deck")**: `W=2 H=1 cutoff=$37`, 2 variants, screens at `$90:75DE`.
* **Map 41**: `W=1 H=1 cutoff=$32`, 7 variants.

Variant selection walks the flag byte's bits from bit 7 down
(`ld hl,record+$12`, `add $30`, then `sla a` / step back 6 bytes per clear bit):
**bit n selects the record at `record+$18+6n`**, and a flag byte of 0 selects
`record+$12`. Since the flag byte is a story-flag byte only 8 bits are
reachable, so a record with more than nine slots (map 155 has 13) has slots this
reader can never select.

## Screen and attribute streams (layout decoder)

A screen layout stream is `{u16 360, u8 marker, body}`; the body consists of
`{marker, X, Y}` triplets meaning:

```
rows = (Y & 0x0F) + 4          ; when (Y & 0x0F) == 0x0F: rows = next body byte + 0x13
for i in 0..rows-1:
    out[cursor++] = out[((Y >> 4) << 8) | X + i]
```

The copy reads from the **already decoded** buffer, so a 2-byte source pattern
propagates into long runs — that is how fences and grass rows are encoded.
Verified byte-exact against live VRAM (`2672/2672` bytes across the five
uploads of one screen). `{marker, $FF, $FF}` is not a repeat: offset `$FFF`
resolves past the 360-byte screen, the wrap code adds `$F0` to the page (and
`$10` on a second miss) and the byte read is 0, so it is a **zero-fill run** of
`next + $13` bytes.

The attribute stream (CGB attribute byte per tile) uses the same format and is
paired with the layout: layout `$46:49F6` ↔ attrs `$46:5363`, layout
`$46:4E30` ↔ attrs `$46:5698`; menu screens use the same pipeline from bank
`$E1` (e.g. layouts `$E1:40D6, $E1:45A7, $E1:4946`).

## Tilesets

Field tile art comes from five `{u16 budget, u8 marker, body}` uploads (same
copy command, but the destination is VRAM):

| Chunk | VRAM dest | Budget |
|---|---|---:|
| `$7D:40FA` | `$8000` | 256 |
| `$20:46E4` | `$8100` | 256 |
| `$7D:54ED` | `$8500` | 224 |
| `$7D:4D02` | `$8600` | 224 |
| `$46:570C` | `$9000` | 1712 |

The BG tile-id base for the field is **`$8800` (signed mode, LCDC.4 = 0)**.
The five uploads above are what one screen loads, not fixed destinations: a map's
record names its own tileset dfar (loaded to `vTiles2 = $9000`), the player sheet
goes to `$8000`, follower sheets to `vTiles0+$100+i*$100`, and NPC sheets to
`$85`/`$86` pages.

The palette set at **file `0x120001`** (bank `$48`) is 8 palettes × 4 RGB555
colours and belongs to **map 0**; every map record carries its own palette dfar
and the loader copies whichever set the record names. Map 0's grass is palette 2
(`0x02C0 0x3F7F`).

## Special maps

Not every map uses the ordinary record. `SpecialMapTable` at **bank `$61`, CPU
`$60D8`** holds 128 words; 35 of them point at **26-byte special-map records**
in `$61D8`–`$6565`:

| Off | Size | Field |
|---|---|---|
| 0 | 4 | tileset `dfar` |
| 4 | 4 | palette `dfar` |
| 8 | 5 | header bytes (width, height, cutoffs, kind) |
| 13 | 9 | unread |
| 22 (`+$14`) | 4 | screen-array `dfar` |
| 26 (`+$17`) | 4 | attribute-array `dfar` |

These are the interiors and menus that have no grid of screens, so a decoder that
only models `18 + 6N` records will fail on them.

## Objects (NPCs, chests, signs)

`MapObjectTable` at **bank `$69`, CPU `$4174`** — 228 words indexed by
`hMapId`. Each word points at the map's **screen table**: `width × height`
words in row-major screen order (dimensions from the map record). A `$0000`
screen word means no objects; anything else points at a **selector**.

Entry words tried in order (first match wins):

| Word | Bytes | Meaning |
|---|---:|---|
| `$FFFF` | 2 | no objects |
| `$FFFE` | 4 | object list follows |
| `$FFFD` | 8 | two flags then a list: taken when **neither** flag is set |
| `$FFFC` | 6 | flag + distance: flag **set** → next entry; clear → skip `entry+6+distance` |
| `$FFFB` | 6 | flag + distance: flag **clear** → next entry; set → skip |
| other ≥ `$FF00` | 2 | no objects |
| plain word | 4 | flag + list: taken when the flag is **clear** |

Flags are tested as `DE >>= 3; bit DE&7 of byte $CBD7 + (DE>>3)` — the same flat
story-flag numbering used everywhere else.

An object list is a count byte + that many **11-byte records**:

| Off | Field |
|---:|---|
| 0 | VRAM page (`$85`/`$86` seen) |
| 1 | graphics table index |
| 2 | graphics number in that table |
| 3 | graphics id high byte |
| 4 | behaviour type (0–5, a six-entry jump table in `UpdateSpriteSlots`) |
| 5 | X in pixels (cell = `>>3`) |
| 6 | Y in pixels |
| 7 | OBJ attribute byte (palette in bits 0–2) |
| 8 | state/facing, and the graphics loader's palette slot |
| 9 | tile offset added by the sprite parts (`page low nibble << 4`) |
| 10 | talk byte (`$FF/$FE/$FC/$FB/$FA` are sentinels, else the talk group) |

Records are copied into 16-byte `wSpriteSlots` entries.

## Warps

`MapWarpTable` at **file `0x467A6`** (bank `$11`, CPU `$67A6`): 256 `u16`
pointers indexed by `hMapId`, each to a list of **9-byte records terminated by
`$80`** (504 records total; the empty list is at `$69A6`).

| Off | Facing 0–3 / `$FD` (positional) | `$FE` / `$FF` (any-facing) |
|---:|---|---|
| 0 | required facing; `$FD` = fires per step | `$FE` (absolute) / `$FF` (relative) |
| 1 | `(src screen X << 4) \| src screen Y` | unused padding |
| 2 | source `hPlayerX` (pixels) | source screen X (full byte) |
| 3 | source `hPlayerY` (pixels) | source screen Y (full byte) |
| 4 | destination `hMapId` | same |
| 5 | dest screen X (low nibble); bit 7 = +8 px to dest Y; bits 4–5 = `wLastWarpIndex` (3 = don't store) | same |
| 6 | dest screen Y (low nibble); high nibble = field transition kind | same |
| 7 | dest X (`low nibble × 16` px) | same |
| 8 | dest Y (`low nibble × 16` px) | same (relative for `$FF`) |

`CheckWarpAtPlayer` is the reader. `$FE`/`$FF` entries fire on a **screen
transition** (after `hMapScreenX/Y` change), so their source screen can be one
past the map edge or `$FF` (walked off the left/top edge).

Census over the 504 records: byte 0 is `$FD` in 353, `$FE` in 116, `$FF` in 31 and
a facing value 0–3 in 4; byte 5 bit 7 is set in 58. `$FD` records never reach
`CheckWarpAtPlayer` (they are step-triggered), which is why nearly all of them
carry a positional source.
`wWarpDestX = (byte7 & 0x0F) << 4`, `wWarpDestY = (byte8 & 0x0F) << 4` plus
**8 px when byte 5 bit 7 is set**.

## Movement and collision

* The player moves in **pixel** units within a screen; a step is 16 px and
  `hPlayerStepDX/DY` holds the per-frame delta (16-bit, so screen scrolling
  uses the same variables with larger values).
* `TileBlockedAtPixel` compares the tile id under the player's 2×2 point block
  against `wMaxBlockingTile`; `wMapTallTileMin` adds "tall tile" handling for
  field events, and `wMapEventTile` fires a talk event when faced.
* `hPlayerFacing` selects the probe direction (`+16` Y, `+16` X, `−16` Y,
  `−16` X) used by `CheckInteractionInFront`.
* `wMapMoveType` selects one of the hurt-floor / ice-style movement routines;
  `wFieldActionRequest`/`wScreenScrollDir` drive the screen-to-screen scroll.
* Steps are counted (`wStepCounter`, `$C7C9`/`$C7CA`) for periodic field
  events and stored-record updates; step triggers are scanned once per step
  (`wStepTriggerFlag`).

## Screen transitions

A transition is `wFieldTransitionKind` (warp record byte 6 high nibble): fade
out → load the new map/screen → place the player → fade in. Field state code
maps these onto the fade machinery (`wFadeState`, `StepFade`) and the
`wScreenState`/`wScreenStep` state machine.

## Related notes

* `re/notes/map_data.md` (this file's primary source), `map_objects.md`,
  `field_map.md`, `submap.md`, `triggers.md`, `object_placement.md`,
  `area_loader.md`, `map_variants.md`, `field_palettes.md`.
* Text/scripts that drive all of the above: `06-text-and-script-vm.md`.
