# 3. Cartridge save (SRAM) format

Battery RAM is 32 KiB: **4 banks × 8 KiB**, one save slot, no slot index.
In a flat `.sav` file, bank *b* occupies `[b*0x2000, (b+1)*0x2000)`. The layout
is identical in both editions.

| Bank | File range | Contents |
|---|---|---|
| 0 | `0x0000` | 30 full monster records (`0xA5` = 165 B each), then 29 compact `0x6F` = 111 B cache records |
| 1 | `0x2000` | bank-1 compact records, record backup, saved WRAM/HRAM blocks, timer block, signature and checksums |
| 2 | `0x4000` | 20 key-world flag records (`0x195` = 405 B each) |
| 3 | `0x6000` | backup copy of bank 2 + its own checksum |

## Validity: exactly three checks

`CheckSaveData` accepts a battery iff **all three** hold:

1. signature `0x3B00 == $55`;
2. bank-1 record checksum at `0x3A73` == `~sum(0x206F..0x3A72) + 0x4321`
   (16-bit, little-endian);
3. bank-3 checksum at `0x7FFE` == `~sum(0x6000..0x7FFD) + 0x1234`.

A fourth checksum, the **saved-block** checksum at `0x3F98` == `sum(0x3B01..0x3EBF)
+ 0x9753`, is *not* part of the gate — the link code reads it.

## Monster record (`0xA5` = 165 B, little-endian)

30 records starting at file `0x0000`, stride `0xA5`. Named fields span
`0x00`–`0xA4`.

| Off | Size | Field | Notes |
|---:|---:|---|---|
| `0x00` | 1 | state | 0 empty, 1 farm/kept, 2 party |
| `0x01` | 10 | name | `$F0`-terminated charset |
| `0x0B` | 2 | species | species id (1…384) |
| `0x0D` | 1 | family | low nibble, 0…10 |
| `0x0E` | 1 | sex | bit 0: 0 male, 1 female |
| `0x0F` | 10 | master_name | the breeder that owns it |
| `0x19` | 1 | master_id | player id |
| `0x1A` | 2 | parent1_species | |
| `0x1C` | 2 | parent2_species | |
| `0x1E` | 10 | parent1_master | |
| `0x29` | 10 | parent2_master | |
| `0x28`, `0x33` | 1 | unused | preset 0; `$FF` for unknown parents |
| `0x34` | 8 | skills | equipped skill ids, `$FF` empty |
| `0x3C` | 25 | skill_list | learnable skills, `$FF` none |
| `0x55` | 1 | status | bit 7 dead, bit 2 poison |
| `0x56` | 1 | level | 1…99 |
| `0x57` | 1 | max_level | level cap |
| `0x58` | 3 | exp | 24-bit |
| `0x5B`/`0x5D` | 2 each | hp / max_hp | |
| `0x5F`/`0x61` | 2 each | mp / max_mp | |
| `0x63`/`0x65` | 2 each | atk / def | |
| `0x67`/`0x69` | 2 each | agl / int | |
| `0x6B` | 2 | wld | wildness |
| `0x6D` | 1 | plus | breeding plus value |
| `0x6E` | 1 | egg | 0 not an egg, 1 egg, 2 appraised egg |
| `0x6F` | 4 | personality | four axes |
| `0x73` | 27 | resistances | one level per element |
| `0x8E` | 10 | parent1_name | |
| `0x98` | 1 | parent1_plus | |
| `0x99` | 10 | parent2_name | |
| `0xA3` | 1 | parent2_plus | |
| `0xA4` | 1 | item | equipped item id |

Text uses the game's charset (`$0A`–`$23` = `A`–`Z`, `$24`–`$3D` = `a`–`z`,
`$F0` = end).

### Compact record (`0x6F` = 111 B) — a lossy cache, not authoritative

The farm/hibernate list shows these. Packed from the full records on save
(`PackRecordFieldsToBank1Slot`) and unpacked on load. Names truncate to five
letters; stat words keep the low byte plus two high bits. The 30 full records in
bank 0 stay the source of truth.

Regions that hold compact records:

| Region | File range | Count |
|---|---|---|
| bank-0 farm cache | `0x1356`–`0x1FE8` | 29 × `0x6F` |
| bank-1 records | `0x206F`–`0x2D70` | 30 × `0x6F` (covered by the bank-1 checksum) |
| record backup | `0x2D71`–`0x3A72` | compact + one extra slot |

## Saved-state blocks (bank 1, file `0x3B01`, `0x3BF` bytes total)

Written contiguously by `SaveGameToSRAMWithChecksum`, four blocks:

| File offset | Size | Block | WRAM/HRAM source |
|---|---:|---|---|
| `0x3B01` | `0x0E` | HRAM block | `$FF8A`–`$FF97` |
| `0x3B0F` | `0x291` | player block | `$C60C`–`$C89C` |
| `0x3DA0` | `0x6B` | story flags | `$CBD7` |
| `0x3E0B` | `0xB5` | key-world slot block | `$CC42` |

HRAM block fields: `sprite_variant` `0x3B01`, `player_x` `0x3B05`
(`hPlayerX`), `screen_x` `0x3B06`, `map_id` `0x3B07`, `player_y` `0x3B08`,
`screen_y` `0x3B09` (bytes `0x3B02`–`0x3B04`, `0x3B0A`–`0x3B0E` are opaque).

Player block fields:

| File offset | Field | Notes |
|---|---|---|
| `0x3B0F` | player_name (10 B) | |
| `0x3B19` | player_id | |
| `0x3B1A` | gold | 24-bit |
| `0x3B1D` | item vault | 100 × `{id, count}` |
| `0x3B20` | bag | 24 one-based item ids |
| `0x3C00` | party_count | |
| `0x3C01` | party_list | 3 record indices |
| `0x3C0A` | key list | 32 × 4 B (`kind`, two name words, level/flag) |
| `0x3C8A` | key seeds | 32 × 2 B |
| `0x3CCF` | species flags | 47 B bitmap (bit `id&7` of byte `id>>3`) |
| `0x3D30` | play_time | 5 B: frames, seconds, minutes, hours lo/hi |
| `0x3D36` | key_index | |
| `0x3D37` | text_speed | 0…7, default 4 |
| `0x3D3A` | game_completed | |
| `0x3D97` | **link_setting** | non-zero unlocks the 8th title-menu row (TERRY) |

`0x3EC0`–`0x3F97` (`0xD8` B) is the GM2 timer block: frames/seconds/minutes,
roll bytes, 11 family scores and the gift-Egg record.

## Key worlds (banks 2 and 3)

20 records of `0x195` bytes at `0x4000`: a marker byte (slot + `$50`) followed
by `0x194` bytes of key-world flags. Bank 3 mirrors bank 2's first `0x1FFE`
bytes and stores its checksum at `0x7FFE`. The 405-byte record is what the link
cable sends verbatim when trading a key.

## Checksum reference

| Name | Offset | Covers | Formula |
|---|---:|---|---|
| saved-block | `0x3F98` | `0x3B01..0x3EBF` | `sum + 0x9753` |
| bank-1 records | `0x3A73` | `0x206F..0x3A72` | `~sum + 0x4321` |
| bank-3 | `0x7FFE` | `0x6000..0x7FFD` | `~sum + 0x1234` |

All 16-bit mod 65536, little-endian. A decode → encode round trip of a genuine
32 KiB image is byte-exact.
