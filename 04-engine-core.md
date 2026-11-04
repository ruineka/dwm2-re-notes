# 4. Engine core: boot, interrupts, main loop, game modes

Routines below are named as in the annotated disassembly; addresses are
`bank:address`.

## Reset and boot

`BootAndMainLoop_StartUp` (`$00:01xx`, the entry the reset vector jumps to):

1. `di`, `ld sp,$DFFF` (`wStackTop`).
2. `DisableVBlankTimerSerialJoypadInterrupts`.
3. `ClearWRAMHRAMAndSRAMBanks0And2` — WRAM, HRAM and the two visible SRAM banks
   are cleared (a save is *not* preserved across reset).
4. `InstallOamDmaRoutine` — copies the DMA stub to `$FF80`.
5. Clears `$8000`–`$9BFF` (`vTiles0`, `$1C00` bytes); on CGB also clears the BG
   map attributes in VRAM bank 1 and restores `rVBK`.
6. `wGameMode = 5` (title/opening), `rRAMB = 0`, `rRAMG = 0`, `rROMB0 = 1`,
   `rROMB1 = 0`, `wSGBActive = 1`, music/SFX request bytes `$FF`,
   `InitSoundHardware`.
7. CGB: load palette 0. DMG: `DetectSGB`; on a Super Game Boy it sends packet
   sets, the border tiles/map and palettes.

`wIsCGB` is set from the boot-register value (`A == $11` → CGB). It is the only
hardware-identity byte the game keeps.

## Interrupts

| Vector | Target | Job |
|---|---|---|
| `$0040` VBlank | `VBlankHandler` (`$00:05xx`) | all per-frame hardware work |
| `$0048` STAT | `StatInterruptHandler` | the scroll split (window/HUD region) chosen by the mode |
| `$0058` Serial | `SerialInterruptHandler` | link-cable byte completion |
| `$0060` Timer | — | not used by the game (the timer is disabled) |
| `$0068` Joypad | `LinkExchangeJoypadPerFrame` path | SGB/link joypad exchange |

### `VBlankHandler` order (this is the frame contract)

1. Save registers; force `rSVBK = 0`.
2. If `wVBlankFlags` bit 0 is already set (VBlank hit while the previous handler
   ran) → skip to `WriteLCDCShadow` + `SoundTick` only. Otherwise set the bit.
3. `hOAMDMARoutine` — `$C000`–`$C09F` → OAM.
4. On CGB with `wFadeState == 0`: upload `wBGPaletteBuffer` /
   `wOBJPaletteBuffer` when their request bytes are set, then clear the requests.
5. `FlushQueuedBGMapWrite`, `CopyDMGPalettesToHardware`, `CopyScrollToHardware`,
   `ApplyScreenShake`, `WriteLCDCShadow`.
6. **Not linked** (`wLinkMode == 0`): `ei`, then `PollJoypad`,
   `UpdateJoypadPresses`, `SoundTick`, `NextRandomSeed`, `ProcessSoundQueue`,
   `GameFrameUpdate`, `StepTextPrinter` (when `wTextFlags` set), `StepFade`, and
   `wFrameCounter` += 1. **Linked**: only `SoundTick`, `ProcessSoundQueue`,
   `GameFrameUpdate`.
7. If no fade is running, not linked, and A+B+Select+Start are all held → jump
   back to `BootAndMainLoop_StartUp` (soft reset).
8. Clear the flag, restore banks/registers, `reti`.

### `GameFrameUpdate` (`$00:06xx`)

```
hOamNextEntry = 0
ComputeSpriteScrollOffsets
RunGameModeUpdate
ClearUnusedOAMEntries      (skipped while a fade is running)
```

`RunGameModeUpdate` returns immediately when `wModeChangeRequest != 0`, or when
a fade is running (fade = `wFadeState != 0` with bit 7 clear) — except in link
mode, where fades do not pause the game.

## Main loop

After the mode's start-up routine, the loop:

1. `ClearBGMapOrFillWithC3` (mode dependent), `ClearShadowOAM`,
   `SetDefaultDMGPaletteBytes`, `ClearScrollPositions`,
   `ResetFadeFromDMGPaletteBGP` — the "screen clear" every mode change goes
   through.
2. `RunGameModeInit` (below), reset frame counters, `ei`, then `halt` forever;
   all work happens in the interrupt handlers.
3. While not linked, each wake from `halt` advances the table PRNG
   (`NextTableByte`).
4. When `wModeChangeRequest` is set and `wFadeState` is 0 or bit 7 is set:
   disable interrupts, send SGB packet set 0, `SpinDelay`, and jump back to the
   screen clear with the new mode.

So "changing mode" always means: request → wait for fade → clear → init.

## Game modes (`wGameMode`, `$C5DB`)

Nine entries; both `RunGameModeInit` and `RunGameModeUpdate` dispatch through
9-entry tables. The value is **not** range-checked.

| Mode | Meaning | Init | Update |
|---:|---|---|---|
| 0 | Debug menu | `GameMode0_Init` (`$01`) | `GameMode0_Update` (`$01`) |
| 1 | Field (walking, events, scripts) | `GameMode1_Init` (`$02`) | `GameMode1_Update` (`$02`) |
| 2 | Pause menu | `GameMode2_Init` (`$03`) | `GameMode2_Update` (`$03`) |
| 3 | None (returns at once) | — | — |
| 4 | Battle | `GameMode4_Init` (`$31`) | `GameMode4_Update` (`$31`) |
| 5 | Title, opening, name entry, new player | `GameMode5_Init` (`$07`) | `GameMode5_Update` (`$07`) |
| 6 | Egg and save screens (link mode) | `GameMode6_Init` (`$24`) | `GameMode6_Update` (`$24`) |
| 7 | Link battle | `GameMode7_Init` (`$A0`) | `GameMode7_Update` (`$A0`) |
| 8 | Egg hand-over | `GameMode8_Init` (`$F2`) | `GameMode8_Update` (`$F2`) |

Mode 1 is the normal game, mode 5 is everything around the title, mode 4 covers
ordinary battles and mode 7 link battles. Random encounters enter mode 4; the
pause menu's INFO screen enters mode 2.

## Banking: the far-call idiom

```
    rst  $10          ; push current bank, select bank B
    rst  $18          ; call the routine at HL, then restore the bank
```

* `RST_10` (`$0010`): read `[$4000]` (current ROM bank), push it,
  `ld [$2100],b` (MBC5 low bank register), `ret`.
* `RST_18` (`$0018`) → `Call_000_000e`: `ld a,[hl+]`, `ld h,[hl]`, `ld l,a`,
  `jp hl`; the called routine ends with `pop af`, `ld [$2100],a`, `ret`.

Consequences for a reimplementation: bank switches are explicit and reversible,
`HL` at a far call points into a pointer table in the caller's bank, and the
called routine may clobber any register except the ones the `pop` restores.

## Random numbers

Two independent generators, both stateful:

1. **Frame-table PRNG** — `NextTableByte` (`$00:1726`):
   `wRandomHi = (wRandomHi + 1) & $7F`, `wRandomLo = RandomByteTable[wRandomHi]`
   (128-byte table at `$00:0973`). Called once per main-loop wake when not
   linked, plus 46 explicit call sites (`AdvanceRandom`,
   `NextTableByteSecondStream`, monster creation, …). Link play swaps in a
   second stream so the two consoles cannot consume the same sequence.
2. **Key-world seed** — `NextRandomSeed` (`$00:09Fx`):
   `wKeyRandomLo/Hi = 5 * seed + 11 (mod 65536)`, computed with two shifts and
   a word add. Used for key generation, encounter rolls and link seeds.

A port must reproduce the exact call order of both, or "random" results
diverge silently.

## OAM and sprites

`wShadowOAM $C000` holds 40 four-byte entries. The DMA stub at `$FF80` copies
them during VBlank. Entries are built each frame by
`BuildOamFromSpriteTable`, driven by `hSpriteSetIndex`/`hSpriteSubIndex`/
`hSpriteOriginX|Y`/`hSpriteTileOffset`/`hSpriteAttrXor` (see
`13-graphics-and-assets.md`).

## Fades

`wFadeState`: 0 = none, bit 7 set = the fade is "instant"/final. `StepFade`
runs the palette interpolation; `RunGameModeUpdate` pauses game logic while a
fade runs (except in link mode); palettes are uploaded in VBlank only when the
fade is idle, so a fade writes the buffers directly.

## Input

`PollJoypad` runs once per frame in VBlank (not in link mode; the link exchange
path polls instead). It fills `wJoypadHeld`/`wJoypadHeldPrev` from
`ReadJoypadDirect`, or from the two SGB pads when `wSGBActive` is set.

## Screen shake and scroll split

`ApplyScreenShake` runs in VBlank right after `CopyScrollToHardware` and offsets
the scroll registers by `wScreenShakeOffset` while `wScreenShakeTimer` counts
down. The STAT handler implements the split screen (fixed HUD window vs.
scrolling field) by rewriting `rSCY`/`rWY` mid-frame at a scanline chosen by the
mode.

## Sound hook

`SoundTick` runs every frame from VBlank (both linked and unlinked) and is the
only per-frame driver the sound engine needs; `ProcessSoundQueue` starts newly
requested tracks/effects. See `12-audio.md`.
