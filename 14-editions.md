# 14. The two editions: Tara's Adventure vs Cobi's Journey

Both cartridges are the same engine and the same data format. This file is what
differs, so a reimplementation can build one and support both.

## The byte diff

Both ROMs are 4,194,304 B. **241 of 256 banks are byte-identical**; 17,767 bytes
differ in 15 banks (0.42 %):

| Bank | Bytes | Contents |
|---|---:|---|
| `$00` | 7 | cart title (`DWM2-T` / `DWM2-C`), licensee byte, header/global checksums, and three **low bytes of bank-`$E1` graphics source pointers** |
| `$01` | 3 | credits/graphics pointers |
| `$07` | 12 | title-menu art stream pointers (`$07:5C7B…`) and one new-game flag index (`$07:68C2`) |
| `$0A` | 1793 | encounter tables and area stubs |
| `$0C` | 4 | library/arena data |
| `$0F` | 2 | scenes |
| `$13` | 9 | talk text |
| `$33` | 1 | `$33:58CA` — team-mode fight-info mark byte |
| `$34` | 1156 | monster record table + pregenerated roster |
| `$85` | 7 | scene code (also the routine that sets `wLinkSetting`, but the diff is elsewhere in the bank) |
| `$88` | 6126 | key-name pointer table + name pool |
| `$A2` | 146 | roster B |
| `$A3` | 1 | `$A3:4244` — formation-table flag match |
| `$E0` | 30 | credits |
| `$E1` | 8470 | title/menu/credits graphics |

Everything that runs during play — the field engine (`$02`), the pause menu
(`$03`), encounters (`$0A` code except tables), breeding (`$0E`), battles
(`$30`–`$3A`, `$A0`, `$A3`), the script VM (`$10`), the sound engine
(`$40`–`$43`), the entire link bank `$1B` — is byte-identical.

## The hero-variant flag (the one behavioural difference)

`GameMode5_Update_NewPlayerSetup_SetGameBegun` (`$07:68C1`) writes **one** story
flag at the end of new-game setup:

| ROM | bytes at `$07:68C1` | flag set |
|---|---|---|
| Tara's Adventure | `1e 00 16 00` (`ld e,$00`) | `$000` |
| Cobi's Journey | `1e 01 16 00` (`ld e,$01`) | `$001` |

The flag means "this cartridge's hero is the *second* field sprite". It drives:

* which graphics sheet/palette the player uses (`LoadPlayerSpriteGraphics`;
  `hPlayerSpriteVariant` is saved at SRAM `0x3B01`);
* which sheet the follower uses (the complement);
* the deck map's object selector (`$69:$770C`: `unless_flag $0001`), i.e. which
  of the two heroes stands next to you;
* the at-sea talk handler `ReadableTalkEvents_AtSeaScene` (`$04:$5660`), which
  branches on `$001`.

So in Tara's game flag `$000` is set (player = sprite id 1 = Tara, follower =
id 0 = Cobi), and in Cobi's game the reverse. A port must write the same flag
its cartridge writes, or the two heroes swap sheets and the deck dialogue picks
the wrong branch.

## Consequences for a reimplementation

* **One code path serves both.** Read the flag; do not hardcode a hero.
* **Saves are interchangeable.** A Tara `.sav` loads in the Cobi build (and vice
  versa); the flag decides which sheet is the player, so the heroes appear
  swapped. Useful for testing everything with one progressed save.
* **Link works across editions.** The wire protocol is edition-neutral; the only
  edition-varying wire byte is `$33:58CA` (team-mode fight-info byte 15: `$00`
  Tara, `$01` Cobi) which lands in `wLinkFightInfo $C963` and is never read.
  `$A3:4244` (formation flag match) only runs outside link battles.
* **Data-level divergence is real.** Because banks `$34`/`$88`/`$0A` differ, a
  cross-edition bred child can come out with different stats on each side, and a
  traded key can show a different name/encounters locally. The protocol
  transfers the parents/record; each console resolves the rest from its own
  tables.
* **Graphics differ** (`$E1`, `$07` art pointers, `$00` pointer bytes): the title
  logo, menu art and credits are per-edition, with the rest of the art shared.

## Verifying a build is the right edition

* Header title string (`DWM2-T`/`DWM2-C`) at `$134`.
* Flag index byte at `$07:68C2` (`$00` vs `$01`).
* Byte at `$33:58CA` (`$00` vs `$01`).
* SHA-256: Tara `fc6809c31ff69c889dee80c5f39f4d8069042a2b4d933edd83d1627c32e013cc`,
  Cobi `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.
