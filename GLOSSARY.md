# GLOSSARY: the words, and where to find the authoritative answer

Every entry is a term you will meet in the notes, a one-line definition, and the
phrase to search when you need the full, accurate story. The last section lists
the sources worth trusting and how to check a claim you found on the web.

Rule for using this list: a definition here tells you *what to ask*; the source
tells you *the answer*. Hardware details change nothing on the cartridge, but
community pages do contain errors — verify anything load-bearing against the ROM
or an accurate emulator.

---

## 1. Hardware and memory

| Term | Definition | Search |
|---|---|---|
| **DMG / CGB / SGB** | Original Game Boy / Game Boy Color / Super Game Boy | `pan docs CGB differences` |
| **LR35902** | The CPU (Sharp SM83 core): 8-bit, GB-specific instruction set | `game boy opcode table` |
| **WRAM** | 8 KiB work RAM at `$C000–$DFFF`, 4 banks of 4 KiB on CGB | `SVBK FF70 WRAM bank` |
| **HRAM** | 127-byte high RAM at `$FF80–$FFFE`, the only place OAM DMA's source can live | `OAM DMA FF46 HRAM` |
| **VRAM** | 8 KiB video RAM at `$8000–$9FFF`, two banks on CGB | `VBK FF4F VRAM bank` |
| **OAM** | 40 sprite entries × 4 bytes at `$FE00`, shadowed via DMA | `OAM structure Y X tile attributes` |
| **IO registers** | Memory-mapped hardware at `$FF00–$FF7F` | `pan docs I/O registers` |
| **Echo RAM** | Mirror of `$C000–$DDFF` at `$E000–$FDFF`; don't rely on it | `echo RAM game boy` |
| **Banking** | Swapping a 16 KiB cart bank into `$4000–$7FFF` | `MBC5 bank switching` |

## 2. Cartridge and mapper

| Term | Definition | Search |
|---|---|---|
| **MBC** | Memory Bank Controller in the cart; decodes writes in `$0000–$7FFF` | `game boy MBC types` |
| **MBC5** | The 4 MiB-capable mapper: low bank at `$2000`, high bit at `$3000`, RAM enable at `$0000`, RAM bank at `$4000` | `MBC5 registers 2000 3000 4000` |
| **RAM enable** | Writing `$0A` to `$0000–$1FFF` unlocks battery RAM | `MBC5 RAM enable 0x0A` |
| **RTC** | Real-time clock in MBC3 carts; latch register, halt bit | `MBC3 RTC latch` |
| **SRAM / battery save** | Save memory in the cart; `.sav`/`.ram` files in emulators | `game boy SRAM save file` |
| **ROM header** | `$0100–$014F`: entry, logo, title, CGB flag, mapper, sizes, checksums | `game boy cartridge header fields` |
| **Global checksum** | `$014E–$014F`, sum of all ROM bytes; emulators rarely verify it | `game boy global checksum` |

## 3. CPU and timing

| Term | Definition | Search |
|---|---|---|
| **Cycle / clock** | 4,194,304 Hz; one frame is 70,224 cycles = 59.7275 Hz | `game boy frame 70224 cycles` |
| **M-cycle / T-cycle** | Machine cycle (4 clocks) and clock ("T-state") | `SM83 machine cycle timing` |
| **Double speed** | CGB mode where the CPU runs at 8,388,608 Hz inside the same frame | `KEY1 FF4D double speed` |
| **VBlank** | Period after line 144 where VRAM/OAM are free; the frame's main interrupt | `pan docs VBlank interrupt` |
| **STAT / LCD modes** | Mode 0 HBlank, 1 VBlank, 2 OAM scan, 3 drawing; STAT interrupts | `pan docs STAT LCD modes` |
| **HALT bug** | HALT with `IME=0` and a pending interrupt skips the next instruction | `HALT bug game boy` |
| **EI delay** | Interrupts are enabled one instruction after `EI` | `EI delay game boy` |
| **DIV / TIMA** | `$FF04` divider, `$FF05` timer; edge cases on writes and overflows | `DIV TIMA edge cases` |
| **Far call** | Guest idiom: write a bank register, then call into `$4000–$7FFF` | `game boy far call bank switching idiom` |

## 4. Graphics

| Term | Definition | Search |
|---|---|---|
| **PPU** | The video hardware: BG, window, sprites, palettes | `pan docs rendering` |
| **Tile** | 8×8, 2 bits per pixel, 16 bytes: two interleaved bit-planes per row | `game boy tile format 2bpp` |
| **Tilemap / BG map** | 32×32 grid of tile indices at `$9800`/`$9C00` | `game boy background map 9800` |
| **Attributes (CGB)** | VRAM bank 1: palette, X/Y flip, priority per tile | `CGB tile attributes VRAM bank 1` |
| **LCDC** | `$FF40`, master display control: enable, map select, sprite size, window | `LCDC bit meanings` |
| **SCX/SCY** | Background scroll registers | `pan docs SCX SCY` |
| **Window** | A second BG layer keyed to screen position, not scroll | `game boy window layer WX WY` |
| **Sprite limits** | 10 sprites per scanline, 40 total; overflow drops later sprites | `10 sprite limit per scanline` |
| **Sprite priority** | Decided by X position, OAM index and the attribute bit | `game boy sprite priority rules` |
| **Palettes** | CGB: 15-bit BGR555 in `$FF68–$FF6B`; DMG: `$FF47`/`$FF48`/`$FF49` | `BGR555 palette format` |
| **LZSS** | Common sprite/map compression; several incompatible variants | `Enix LZSS game boy decompression` |
| **VRAM access blocking** | VRAM is inaccessible in mode 3, OAM in modes 2–3 | `pan docs VRAM OAM access` |

## 5. Audio

| Term | Definition | Search |
|---|---|---|
| **APU** | Four channels: two pulses, one wave, one noise | `pan docs audio channels` |
| **Frame sequencer** | 512 Hz stepper for length/envelope/sweep | `game boy frame sequencer 512 Hz` |
| **NR registers** | `$FF10–$FF26`: sweep, duty, envelope, wave, noise, master | `NR10 NR52 register map` |
| **Envelope / sweep** | Volume ramp and frequency ramp units | `game boy envelope sweep timing` |
| **Wave RAM** | 16 bytes of 4-bit samples for the wave channel | `wave channel RAM NR30` |
| **DAC** | Each channel's digital-to-analog enable is a separate bit | `game boy DAC NRx2` |

## 6. Serial and link cable

| Term | Definition | Search |
|---|---|---|
| **SB / SC** | `$FF01` shift register, `$FF02` control (start bit 7, clock select bit 0) | `pan docs serial transfer` |
| **Master clock** | The side that drives the serial clock (`SC` bit 0 = 1) | `game boy link cable master` |
| **Serial transfer completion** | Interrupt at `$0058` after 4096 clocks (128 in double speed) | `serial interrupt 4096 cycles` |
| **Byte-synchronous protocol** | Link protocols that exchange one byte at a time with no framing | `game boy link protocol byte synchronous` |
| **Timeout / cable fault** | Behaviour when the peer never answers (`$FF` received, stalled state machine) | `serial transfer no cable FF` |

## 7. Reverse engineering

| Term | Definition | Search |
|---|---|---|
| **Disassembly** | Machine code rendered as assembly text with labels | `mgbdis game boy disassembler` |
| **Symbol file (.sym)** | `bank:addr name` lines that name routines/variables in a disassembly | `game boy .sym file format` |
| **Recursive descent** | Follow control flow from entry points to find code | `recursive descent disassembler` |
| **Linear sweep** | Decode every byte as an instruction; fast but produces false code | `linear sweep disassembly` |
| **Code/data separation** | Deciding which bytes are instructions vs data — the central disassembly problem | `code data separation binary` |
| **Jump table** | Array of code pointers used for `switch`-like dispatch | `jump table recovery binary analysis` |
| **Coverage trace** | Which addresses actually executed under a given input | `execution trace coverage basic block` |
| **Breakpoint (conditional)** | Stop when PC or a memory access matches a condition | `emulator conditional breakpoint` |
| **Savestate** | Snapshot of the full machine; great for exploring, dangerous for claims | `savestate vs battery save` |
| **Checksum / magic** | Validity pattern in save/asset data | `save file checksum game boy` |
| **TCRF** | The Cutting Room Floor — unused content wiki | `tcrf dragon warrior monsters 2` |
| **ROM map** | Community documentation of a game's data layout | `data crystal ROM map` |

## 8. Static recompilation

| Term | Definition | Search |
|---|---|---|
| **Static recompilation / static binary translation (SBT)** | Translating guest code to host code ahead of time | `static binary translation` |
| **Dynamic recompilation / JIT** | Translating at run time, block by block | `dynamic recompilation JIT emulator` |
| **AOT translation** | Ahead-of-time compilation of guest code | `ahead-of-time binary translation` |
| **Runtime** | The library that provides memory, PPU, APU, cart, timing | `emulator runtime design` |
| **HLE vs LLE** | High-level emulation (behavioural shortcuts) vs low-level (hardware-faithful) | `high level emulation low level emulation` |
| **Fallback interpreter** | Interpreter used for code the translator missed; its hit count is a coverage metric | `fallback interpreter recompiler` |
| **Trace-seeded recompilation** | Using an execution trace to decide what is code before translating | `profile guided binary translation` |
| **Differential self-check** | Run generated code and interpreter on the same input and compare | `differential testing emulator` |
| **Frame hash** | Hash of the machine's visible state at a frame, used as a fingerprint | `frame hash regression emulator` |
| **Deterministic replay** | Same inputs → identical run, enabling bisection | `deterministic input replay emulator` |

## 9. Porting and verification

| Term | Definition | Search |
|---|---|---|
| **Clean room** | Reimplementation from specification/observation, without copying code | `clean room design` |
| **Oracle** | The reference implementation you compare against | `oracle based testing` |
| **Differential testing** | Run two implementations on the same input, compare | `differential testing software` |
| **State parity** | Agreement on the game's own variables, frame by frame | `state comparison testing emulator` |
| **Golden master** | A recorded expected output used as a regression test | `golden master testing` |
| **Lockstep / desync** | Two runs advancing together; "desync" = they disagree | `lockstep simulation desync` |
| **Property-based testing** | Assert invariants over generated inputs | `property based testing` |
| **Coverage-guided fuzzing** | Fuzzing steered by new code paths | `coverage guided fuzzing` |
| **Smoke test** | A short run that proves the thing starts and the main path works | `smoke test` |
| **Golden-frame test** | Pixel-exact comparison at selected frames | `golden frame testing` |

## 10. Save data

| Term | Definition | Search |
|---|---|---|
| **Battery save** | SRAM content persisted by the emulator to a `.sav` | `battery backed save game boy` |
| **Save block / record** | A fixed-size struct inside SRAM | `save file structure` |
| **Validity checks** | Magic byte + per-block checksum + global checksum, any of which may gate loading | `save file checksum validation` |
| **Save round-trip** | Write with A, read with B, compare — the strongest save-layer test | `round trip test serialization` |

## 11. Legal and project hygiene

| Term | Definition | Search |
|---|---|---|
| **Own dump** | The only ROM you may lawfully use (back up of your own cartridge, in most jurisdictions) | `ripping own game boy cartridge` |
| **No ROM distribution** | Repositories ship tools, not ROMs; data is extracted at install time | `rom hacking legal clean room` |
| **Patch (IPS/BPS)** | A diff applied to a ROM by the user | `IPS BPS patch format` |
| **Regenerate, don't ship** | Derived game data is produced by the user's own extraction step | `extract assets from rom legal` |

## 12. Game-domain vocabulary (DWM2)

Useful when searching wikis rather than hardware docs.

| Term | Meaning | Search |
|---|---|---|
| **Monster Master** | The player's role/profession | `Dragon Warrior Monsters 2 Master` |
| **GreatLog / GreatTree** | Main hub towns of the two chapters | `Dragon Warrior Monsters 2 GreatLog` |
| **Key world** | Randomly generated dungeon world opened by a "magic key" | `DWM2 key world magic key` |
| **Breeding / plus value** | Two monsters produce an egg; `+` counts generations | `DWM2 breeding plus` |
| **Dream Egg / Terry** | Link-cable features (gift egg, Terry's breeding service, gated by a save flag) | `DWM2 Terry Dream Egg link` |
| **Key trade** | Linking to exchange keys | `DWM2 key trade link` |
| **Tara / Cobi** | The two editions (heroine and hero) sharing one engine | `DWM2 Tara Cobi version differences` |

## 13. Sources worth trusting (and how to check one)

| Source | What it is good for |
|---|---|
| **Pan Docs** (gbdev.io/pandocs) | The standard hardware reference; start here for any register |
| **Game Boy: Complete Technical Reference** (Gekkio) | Cycle-level detail, timing tables, edge cases |
| **The Ultimate Game Boy Talk** (Michael Steil) | The mental model of PPU/APU/DMA in one hour |
| **awesome-gbdev** (GitHub) | Curated list of tooling, docs, test ROMs |
| **mgbdis** (GitHub) | Practical GB disassembler; produces diffable listings |
| **SameBoy / mGBA / BGB / PyBoy / binjgb** | Emulators at different accuracy/tooling trade-offs; SameBoy is the accuracy reference, mGBA and PyBoy the scripting ones |
| **mooneye / blargg test ROMs** | Pass/fail hardware conformance suites |
| **RGBDS docs** | Assembler, linker and the `.sym` conventions |
| **GB Recompiled** (github.com/arcanite24/gb-recompiled) | A working static recompiler for GB/GBC, with its own accuracy notes |
| **Data Crystal** (datacrystal.romhacking.net) | Community ROM maps and formats |
| **TCRF** (tcrf.net) | Unused content, version differences |
| **Dragon Quest Wiki** (dragon-quest.org) | Game data: monsters, items, story |

How to check a web claim:

1. Prefer a primary source (Pan Docs, Gekkio) over a forum post or a wiki summary.
2. Find the register or format it refers to, then confirm the concrete value in
   the ROM or in an accurate emulator's behaviour.
3. If a page contradicts the hardware and the hardware is observable, the page
   is wrong; write the correction into your notes with the evidence.
4. For game-specific data (tables, sprites, text), community docs are a *map*:
   the index may be right while the stride is not. Decode one record to check.
5. Date your sources. A 2003 ROM-hacking page can be right about the mapper and
   wrong about everything measured since.

**Search phrasing that works.** Hardware: `pan docs <register name>`,
`<thing> game boy` + `accuracy`/`timing`. Tooling: `<tool name> github`. Game
data: `<game name> <system> ROM map`, `<game name> TCRF`. Technique:
`<technique> binary analysis` or `<technique> emulator design`. Prefer results
from gbdev.io, GitHub repositories with test ROMs, and pages that quote the
registers rather than paraphrase them.
