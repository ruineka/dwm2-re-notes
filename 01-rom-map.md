# 1. The ROM: header, geometry, bank map

Everything in this file was read out of the two retail dumps and cross-checked
against an annotated disassembly of the same engine (the Cobi build, which is a
byte-for-byte re-assembly of the cartridge). Addresses are `bank:address`;
a bank is 16 KiB, so `$11:459A` means file offset `0x4459A`.

## Cartridge

| Field | Value |
|---|---|
| Size | 4,194,304 B = 256 banks × 16 KiB |
| Cartridge type | `$1B` = MBC5 + RAM + battery |
| ROM size code | `$0C` (4 MB) |
| RAM size code | `$03` (4 banks × 8 KiB = 32 KiB) |
| CGB flag | `$80` (CGB-only title; runs on DMG in monochrome compatibility mode) |
| SGB flag | `$03` |
| Title | `DWM2-T` (Tara's Adventure) / `DWM2-C` (Cobi's Journey) |
| Far-call convention | Enix `rst $10` (bank switch) + `rst $18` (call through HL) |

Only **157 of the 256 banks** contain data; the rest are padding (every byte
`$00` or `$FF`). The last non-empty bank is `$F2`. Empty banks:
`$44–$45, $8B–$8F, $9A–$9F, $A4–$DF, $E3–$EF, $F3–$FF`.

## Bank map

### Core engine (`$00`–`$3F`, `$A0`–`$A3`, `$E0`–`$E2`, `$F0`–`$F2`)

| Bank | Contents |
|---|---|
| `$00` | Home bank: boot, main loop, interrupt handlers (VBlank/STAT/timer/serial/joypad), bank switching (`rst $10`/`rst $18` trampolines), the text printer, palette fades, OAM DMA install, decompression, general helpers |
| `$01` | Debug menu (game mode 0): message test, debug battle set-up, monster creation, results |
| `$02` | Field mode (game mode 1): map play, map header loading, field states, collision, field menus |
| `$03` | Pause menu (game mode 2): items, monsters, plan, info |
| `$04` | Field events: chests, vases and barrels, key-world events, the at-sea/Yold talk routines |
| `$05` | Battle AI: per-skill scoring routines (`AIScore_*`) and their conditions |
| `$06` | Battle AI: the personality table |
| `$07` | Link cable sessions and the title screen (game mode 5): opening, name entry, new-player setup, title menu, all eight link sessions |
| `$08` | String tables: system text, monster/skill/item names |
| `$09` | String tables |
| `$0A` | Random encounters: encounter groups and grids, battle intro |
| `$0B` | String tables |
| `$0C` | The monster library and the arena; script helpers |
| `$0D` | TinyMedal prizes, egg appraisal and blessing, key appraisal |
| `$0E` | Breeding tables (species pair rules, family results) and the breeding message bank |
| `$0F` | Story scenes: Darck, the homecoming, the mermaid, others |
| `$10` | Event script engine: command fetch and handlers, plus scripts |
| `$11` | **Map records and warps** (`MapTable`) |
| `$12` | Field objects and paths, key-world field code, arena rounds |
| `$13` | Talk events: messages by region (GreatLog, Norden, …), chests |
| `$14` | Name entry, default and suggested names, hibernation |
| `$15` | The breeding menu |
| `$16` | Item use (usable/apply routines) and the end of a battle |
| `$17` | Super Game Boy packets and border control |
| `$18` | Super Game Boy border data |
| `$19` | Battle loading (game mode 4 set-up) |
| `$1A` | Skill prerequisites; tile rectangles |
| `$1B` | Link key exchange, egg service, link screens |
| `$1C` | Shops, the vault and the inn; item names |
| `$1D` | The vault menu, scripts and glyph tiles |
| `$1E` | The monster swap menu |
| `$1F` | **The font**, scripts, strings and SGB data |
| `$20`–`$23` | Compressed monster sprites |
| `$24` | Link mode (game mode 6), item descriptions, the priest |
| `$25`–`$27` | Meta-sprite frames |
| `$28`–`$2E` | Messages |
| `$2F` | Battle text |
| `$30` | Battle commands and personality rolls |
| `$31` | Battle phases, the end of a battle, slot drawing (also holds `GameMode4_Init`) |
| `$32` | Battle action steps and resolve steps |
| `$33` | Link sessions (team mode) and strings |
| `$34` | **The monster table** (species base stats/EXP, pregenerated roster) |
| `$35` | **Species records** |
| `$36` | Battle action resolution and skill effects (`ActionEffect_*`) |
| `$37` | Link sessions (Terry breeding) and strings |
| `$38` | Monster picture and attribute tables |
| `$39` | Battle target choice |
| `$3A` | Battle effect steps and battle text hooks |
| `$3B` | Battle helpers; meta-sprites |
| `$3C` | Battle effect graphics |
| `$3D`–`$3F` | Meta-sprite frames |
| `$A0` | Battle turns, encounter bands, game mode 7 (link battle) |
| `$A1` | The world map screen and game-mode helpers |
| `$A2` | Strings and monster loading |
| `$A3` | Battle helpers: battler stats, personality index |
| `$E0` | Debug: staff roll and debug screens |
| `$E1` | Screen graphics, tiles and palettes (title/menu art streams) |
| `$E2` | Battle AI: the second set of scoring routines |
| `$F0` | Link sessions, family bands, gift effects (dream-egg session 8) |
| `$F1` | Screens, item lists and pause-menu helpers |
| `$F2` | Screens and game mode 8 (egg hand-over) |

### Audio (`$40`–`$43`)

Four banks of sound tracks, read by the sound engine through `hSoundBank`
(`$FFDD`). Each track is a stream of `event → parameter` pairs (2 bytes).

### Map screens / tilesets (`$46`–`$5C`, `$5E`, `$90`, `$93`)

Each bank holds a batch of **map screens**: a screen is a 20×18 (or 32×32 for
special maps) tile block plus its CGB attribute block plus tileset definitions.
Which bank a map's screens come from is part of the map record (see
`05-field-maps-and-objects.md`).

| Bank | Contents |
|---|---|
| `$46`–`$5C` | Map screens, attributes and tilesets (the main block; maps 0..~0x47 point here) |
| `$5D` | The world map screen data |
| `$5E` | More map screens |
| `$60` | Key worlds: random room generator and the debug automap |
| `$61` | Special maps, warps and map loading |
| `$62`–`$66` | Key-world map screens |
| `$67`, `$72` | Key-world data |
| `$68` | Key-world map screens |
| `$69` | **Map object lists and selectors** (object programs, `unless_flag` chains) |
| `$6A`–`$6C` | Special map screens (title, ship deck, cutscene maps, …) |
| `$6D`–`$71` | Key-world map screens |
| `$84` | Key-world helpers and debug field code |
| `$87` | Map interactions and steps |
| `$90`, `$93` | More map screens |
| `$94` | Special map screens |
| `$5F`, `$73`, `$85` | Scene scripts, messages and map data for story scenes |

### Graphics (`$20`–`$27`, `$38`, `$3C`–`$3F`, `$74`–`$7F`, `$91`–`$92`, `$E1`)

| Bank | Contents |
|---|---|
| `$74`–`$7B` | Compressed monster pictures (and palettes in `$7B`) |
| `$7D` | **Field sprites** (the sheets `FieldSpriteGraphicsTable` uploads) |
| `$7E` | Field graphics, additional sprites and palettes |
| `$7F` | Meta-sprite frames (set 1: the player's walk animation lives here) |
| `$3D`–`$3F`, `$92` | Meta-sprite frames |
| `$25`–`$27` | Meta-sprite frames |
| `$91` | Monster sprites and battle effect graphics |
| `$18` | SGB border graphics |
| `$E1` | Screen graphics, tiles and palettes |

### Tables worth knowing by address

| Data | Where |
|---|---|
| Map records (`MapTable`) | bank `$11` |
| Encounter groups/grids | bank `$0A` (`$0A:081C` is the boss-battle table, `$0A:1773` the random-encounter data) |
| Monster table (base stats) | bank `$34` (`$34:0000` record table, `$34:0075` pregenerated roster) |
| Species records | bank `$35` |
| Species pair / breeding rules | bank `$0E` and bank `$81` |
| Skill prerequisites | bank `$1A` (`$1A:100A`) |
| Font (256 glyphs) | bank `$1F`, `$1F:4010` |
| String tables | banks `$08`, `$09`, `$0B`, `$28`–`$2F`, `$7C`, `$80`, `$82`, `$83`, `$86`, `$88`–`$89`, `$8A`, `$95`–`$99`, `$A2` |
| Sound tracks | banks `$40`–`$43` |

## Memory geometry beyond the ROM

* Work RAM `$C000`–`$DFFF`: WRAM bank 0 is the default; banks 2 and 3 hold the
  screen attribute buffers (`wScreenAttrBuffer $D000`, `wWindowAttrBuffer
  $D168`, `wSavedScreenAttrs $D2D0`).
* High RAM `$FF80`–`$FFFE`: I/O mirrors, the OAM DMA routine at `$FF80`, the
  player/scroll/sprite variables, the decompressor state, and the sound channel
  copy.
* Cartridge RAM `$A000`–`$BFFF` (4 banks): the save, see
  `03-sram-save-format.md`.

## Edition note

Tara's Adventure and Cobi's Journey are the same engine: 241 of 256 banks are
byte-identical. See `14-editions.md`.
