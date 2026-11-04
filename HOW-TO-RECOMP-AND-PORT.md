# HOW-TO: static recompilation, and a clean-room port

*Part 1 covers building a static recompilation of a GBC game. Part 2 covers
building a clean-room reimplementation. Part 3 is how the two feed each other and
what the project tree looks like. §5 is the vocabulary, with the search phrase
for each term's authoritative source.*

Prerequisite: you already know *what* the game does at the data level (the state
of the reverse engineering described in [`HOW-TO.md`](HOW-TO.md)). This document
is about turning that knowledge into a running program two different ways.

Both are ways to run the same cartridge with none of the original code:

| | Static recompilation | Clean-room port |
|---|---|---|
| What you write | a translator that turns guest code into host code at build time, plus a runtime that provides the hardware | your own implementation of the game's logic and data |
| What you get | fidelity by construction, cheaply | maintainability, portability, moddability |
| Main cost | the translator and the runtime's hardware edge cases | re-deriving every behaviour and every table |
| Failure mode | subtle mis-translation or missing hardware behaviour | "looks right", but internal state drifted |
| Best use | an oracle, a preservation build, a fast test target | a product, a platform port, a study |
| Effort to first frame | days | weeks |
| Effort to whole game | weeks (mostly hardware corner cases) | months (every subsystem, twice-verified) |

They compose: use the recompilation as the **oracle** while you build the port.
That combination is the single biggest productivity multiplier in this field —
it turns "does it look right?" into "at which frame does the state differ?".

---

# Part 1 — Static recompilation

## 1.1 What it is, precisely

At build time you read the ROM, decode every executing instruction, and emit host
code (usually C) with one function per guest basic block or subroutine. At run
time that code executes on a small library — the **runtime** — that provides:

* the guest CPU state (registers, SP, PC, flags, interrupt enable);
* a memory map: ROM (read-only, banked), WRAM banks, VRAM banks, HRAM, OAM,
  IO registers, unmapped regions;
* the cartridge mapper (MBC5 here: bank registers at `$2000/$3000`, SRAM
  enable/bank, RTC);
* the PPU (registers, tiles, palettes, OAM, scanline timing, LCD/STAT state);
* the APU (channels, frame sequencer, envelopes, wave RAM, mixing);
* timers, joypad, serial (and, if the game links, the link cable transport);
* save/SRAM persistence.

The guest *code* is never interpreted in a normal run. Everything else about the
machine is the runtime's job, and that is where nearly all of the real work ends
up.

**Choose a recompilation when** you want maximum behavioural fidelity for minimum
understanding: you do not need to know what a routine means, only what it does.
**Do not choose it when** you want to restructure the game, port its logic to
new features, or ship readable source.

## 1.2 The pipeline

```
ROM ──► symbol/trace seeding ──► decoder ──► per-function C ──► generated tree
                                                                    │
runtime library (CPU, PPU, APU, cart, timers, serial, input) ───────┤
                                                                    ▼
                                                        build (cmake/ninja) ──► binary
```

In order:

1. **Bank map and code/data split.** The hardest problem. Solve it with
   *reachability*: seed with the reset vector (`$0100`), the interrupt vectors
   (`$0040–$0060`), and any known entry points. Then decode recursively along
   calls and jumps, and use an execution trace to confirm which PCs actually run.
2. **Decoding.** Instructions → C. Keep it literal: a flag-accurate ALU, a
   `DAA` that is tested, correct `ADD SP,e8`, `LD HL,SP+e8`, `POP AF` masking,
   and the exact `RETI`/`EI` timing. Bugs here look like random gameplay
   corruption months later.
3. **Control flow.** Direct calls/jumps become C calls/gotos inside one bank.
   Indirect flows need a dispatcher:
   * jump tables (`JP HL`, table-driven `JP`): resolve statically where the table
     is known, else dispatch through the runtime;
   * cross-bank calls: the guest switches the bank register then calls into
     `$4000–$7FFF`, so the translator must model the bank register;
   * returns across banks: rare but real; a generic dispatcher covers it.
4. **Generation.** One C file per bank (or per function group), one function per
   basic block, a symbol table from the ROM's labelling, and an entry table
   `bank:addr → function pointer` for dispatches and for anything the runtime has
   to trigger (interrupts, callbacks).
5. **Fallback.** Keep an interpreter for addresses the translator has not seen.
   In development builds make a fallback call *loud* (log, count, option to
   abort): every fallback is a hole in your coverage, and you want the count to
   reach zero during a long play session.
6. **Verification.** Three levels:
   * generated code vs interpreter on the same input (catches translation bugs);
   * recompilation vs emulator, same input, compare PC and registers at
     checkpoints (catches runtime hardware bugs);
   * a full play session with frame hashes (VRAM/OAM/palettes/registers) on both
     sides (catches drift).
7. **Iterate coverage.** Re-record a trace, feed it back into the seeding step,
   regenerate. Ten minutes of play per iteration until the fallback count is
   zero over a long, varied session.

## 1.3 The hard problems, and what normally works

**Code/data separation.** Recursive descent alone over-translates (it walks into
data that happens to look like code) and under-translates (it misses entries
reached only through computed jumps). The practical recipe: descent from vectors
and known entries, plus coverage from a trace, plus a manual overrides file
(`bank:addr = code | data | jumptable`) for what remains. Validate by executing:
if the translator emitted code for a jump table, you will see it in the fallback
log or in a crash, and the override fixes it.

**Jump tables.** Heuristics: a run of 16-bit values in `$4000–$7FFF` inside the
same bank, pointing at instruction boundaries, often preceded by a bounds check.
Generate a table *and* keep the dispatcher: correctness first, speed later.

**Bank switching.** Never bake a bank number into a read. Either keep the bank
register in the runtime and access ROM through an accessor, or invalidate and
re-point the window on each bank write. A block that writes `$2000` and then
keeps reading `$4000` must see the new bank immediately.

**Interrupts.** Model them at instruction boundaries with the real latency: an
interrupt is taken after the current instruction if `IME`, pushes PC, jumps to
the vector, clears `IME`, and `RETI` sets it. Do not run one interrupt per host
frame — run vblank at the right dot, and let STAT/timer/serial interrupts fire
from their own counters. `HALT` (and its quirk: `HALT` with pending interrupts
does not halt) and the one-instruction `EI` delay are classic sources of "the
game freezes" reports.

**PPU.** Two viable levels: scanline-accurate (needed if the game depends on
mid-frame register changes — status bars, splits, window tricks) or frame-level
(render 144 lines at vblank). Start frame-level, switch when a visual difference
appears at a scanline boundary; the trace tells you which registers change
mid-frame. Keep LCD-off, window, sprite-per-line limits, the 10-sprite cut-off
and the palette write timing honest.

**APU.** Music is the second thing players notice. Model the frame sequencer at
512 Hz, envelopes/sweeps per frame, wave RAM quantisation, and the channel
trigger order; compare against recorded WAVs. It is fine to get there in two
passes: make it not crash, then make it identical.

**Timers and serial.** Count cycles, not frames. `DIV`/`TIMA` edge cases and the
serial transfer rate matter if the game reads them (sound engines and link code
do). Double-speed halves the CPU cycle count per frame while the frame keeps its
duration — model the speed switch explicitly.

**Cartridge writes.** Every write in `$0000–$7FFF` is a mapper command, not
memory. Route them through the mapper and ignore writes where the mapper ignores
them.

**Determinism.** One thread, one frame at a time, no host clock inside the guest.
The moment `time()` leaks into game logic, your differential tests stop being
exact.

## 1.4 Bring-up order

```
boot ROM / reset vector → Nintendo logo → title screen → first playable field
   → menus → text → save/load → battle → every remaining screen → a full run
```

At each step, fix the *lowest* layer that fails (mapper, PPU, APU, timing), not
the symptom on screen. Record a savestate and a frame hash at each milestone; the
hash list is your regression suite.

## 1.5 Definition of done for the recompilation

* fallback count `0` over a long, varied play session (and a log line if it is
  not);
* the self-check (generated vs interpreter) and the cross-check (vs emulator) both
  clean on your standard input scripts;
* frame hashes match the emulator for every milestone savestate;
* save files write and reload, and an emulator-created save loads in the
  recompilation (the strongest single test of the cartridge/save layer);
* the link/network path works if the game has one (two instances, balanced
  counters, zero stalls).

---

# Part 2 — Clean-room port

## 2.1 What "clean-room" changes

In a port you do not translate instructions; you reimplement the *behaviour* the
game exhibits, from the reverse-engineering notes and observed evidence. The
legal and engineering point is the same: your source is yours, your extracted
data is derived at install time from the user's own dump, and no Nintendo code or
art is shipped.

Because you are reimplementing rather than translating, the risk profile flips: a
recompilation is only wrong where the machine is (rare, local, testable), while a
port is wrong wherever your understanding is (frequent, systemic, and it still
*looks* right). Everything in Part 2 is about shrinking that risk.

## 2.2 The one rule that makes ports tractable: state parity

Do not compare screenshots first. Compare **named game state**:

```
frame=3124 map=29 px=80 py=64 sx=1 sy=0 face=3 flags=05
```

Pick the variables the game itself uses (`hMapId`, `hPlayerX`, screen position,
mode words, script state). Dump them from your port every frame, dump them from
the oracle for the same frame, and diff. A first-diverging-frame number is worth
more than a hundred eyeballed screenshots because it is (a) exact, (b) bisectable
and (c) attributable to a subsystem.

Pixels come after state: once state matches, a pixel difference means a rendering
bug, and you no longer have to ask which of the two it is.

## 2.3 Architecture

```
┌──────────────────────────────────────────────────────────┐
│ shell / platform layer                                   │
│   window, input, audio device, timing, save file paths   │
└───────────────┬──────────────────────────────────────────┘
                │  calls into a pure library
┌───────────────▼──────────────────────────────────────────┐
│ game logic (pure C, no OS, no threads, no wall clock)    │
│   field  menus  text  script VM  battle  breeding  link  │
│   save format  PRNG  object/spawn logic  audio sequencer │
└───────────────┬──────────────────────────────────────────┘
                │  reads immutable data
┌───────────────▼──────────────────────────────────────────┐
│ data layer (generated at install time from the ROM)      │
│   tables, text, graphics, palettes, audio, maps          │
└──────────────────────────────────────────────────────────┘
```

Rules that keep it a port rather than a pile of special cases:

* **The core never reads the ROM or files.** Everything it needs is in the data
  layer, produced by extractors, immutable at runtime.
* **No host timing inside the logic.** The logic is stepped at the guest's frame
  rate (59.7275 Hz); the shell decides when to step, and a debug switch can step
  without a window.
* **One module per subsystem, with the ROM's own vocabulary** in the names
  (`hPlayerX`, `wStoryFlags`, `DWM2_...`), so a note's address can be grepped to
  the module that owns it.
* **Rendering is a projection of state**, never a source of truth. If a screen
  draws correctly but the state is wrong, the bug is in the state.

## 2.4 The extraction pipeline

Reverse engineering gives you addresses; a port needs data. Build extractors
early and treat them as production code:

1. one extractor per data family (tables, text blocks, graphics, palettes,
   audio, maps, script byte-code);
2. output as generated includes/JSON, never typed by hand;
3. each extractor validated against a known record (a monster's stats, a shop
   price, a name) in a test;
4. the ROM is required only at install/build time — the repository contains no
   game data;
5. when an extractor's decode is corrected, regenerate everything and re-run the
   tests: a wrong decode in a shared table is the most expensive port bug there
   is, because it silently changes five subsystems at once.

## 2.5 Bring-up order for a port

Port in the order that produces something playable and measurable soonest:

```
1. data layer + one screen that draws (title or a map)
2. field movement, collision, camera/screen scroll
3. map load: tilesets, palettes, objects, warps
4. text engine (messages, choices, names)
5. script VM: movement, messages, flags, warps
6. pause menu, inventory, shops
7. save format (load, then write, then verify round-trip with the oracle)
8. battles (damage, status, AI, rewards)
9. breeding, eggs, key worlds (generated content)
10. link/network, then the endless screens
```

At every step the parity harness runs the same recorded inputs through both
sides. A subsystem is "in" only when the comparison agrees across its window.

## 2.6 Definition of done for the port

* parity: recorded play sessions agree on state for the whole session (or the
  first divergence is a known, documented gap);
* units: every decoder and formula has a test with values taken from the ROM;
* save compatibility: the port writes a save the oracle accepts and vice versa;
* a headless smoke run that boots, walks, warps, opens a shop, fights, saves;
* no ROM/file access in the logic layer (enforce it with a test or a build
  check);
* documentation written as facts with addresses, not as history.

---

# Part 3 — How the two fit, and what the tree looks like

## 3.1 The loop that uses both

```
        ┌─────────────── the ROM (single source of truth) ───────────────┐
        ▼                                                               ▼
  RE notes ──► recompilation (oracle)  ──► parity harness ──► clean-room port
      ▲              │                            ▲                    │
      └──────────────┴── evidence: first differing frame, dumps ────────┘
```

* The **recompilation** gives you a fast, deterministic oracle that runs at
  build speed and can dump the guest's own variables at any frame.
* The **port** gives you readable source you can instrument, refactor and ship.
* The **notes** are the shared substrate: addresses, formats, order of
  operations. Every fix made in either artifact goes back into them.

A worked example of why this matters: a visual difference that appears only on
one walk-animation frame. Screenshots say "the sprite is transparent"; the parity
harness says "state is identical, so it is a rendering bug"; the port's own
per-frame geometry dump says the draw rect is 17 rows tall while the frame's
tiles occupy rows 1–16. The oracle had already narrowed it to rendering; the port
supplied the exact numbers. Neither tool alone would have been as fast.

## 3.2 Repository layout

Two layouts, one for each artifact, sharing one RE tree and one test discipline.

```
repo/
├── docs/                      # design, decisions, handoffs, per-topic notes
├── re/                        # the reverse-engineering substrate
│   ├── notes/                 #   one file per subsystem, addresses + evidence
│   ├── symbols.json           #   ROM address → name database
│   └── fixtures/              #   battery saves, expected dumps
├── tools/                     # everything that turns evidence into artifacts
│   ├── coverage/              #   tracer + input scripts (code discovery)
│   ├── cleanroom/             #   per-topic extractors (data, flags, formulas)
│   ├── recomp/                #   recompiler wrapper, generators, patchers
│   └── pair/                  #   differential harness, trace tools
├── third_party/               # recompiler, emulator (MIT/GPL, unmodified)
│
├── build-recomp/              # ── static recompilation ──
│   ├── runtime/               #   CPU state, PPU, APU, cart, timers, serial
│   ├── generated/             #   per-bank C from the translator (gitignored)
│   ├── config/                #   symbols, code/data overrides, jump tables
│   └── build/                 #   the oracle binary (gitignored)
│
├── port/                      # ── clean-room port ──
│   ├── src/core/              #   pure logic: field, text, battle, save, …
│   ├── src/platform/          #   window, input, audio, timing
│   ├── assets/generated/      #   extracted data (gitignored, built from ROM)
│   ├── tests/                 #   unit + golden + smoke
│   └── CMakeLists.txt
│
├── launcher/                  # optional: the thing players actually run
└── .scratch/                  # traces, captures, screenshots (gitignored)
```

### Who owns what

| Directory | Rule |
|---|---|
| `re/` | claims with addresses; changes when evidence changes |
| `tools/` | must be re-runnable; output is deterministic; extractor tests live here |
| `build-recomp/runtime/` | the machine, not the game: keep it generic |
| `build-recomp/generated/` | never edited by hand; regenerated wholesale |
| `build-recomp/config/` | the only place where a translation decision is written down |
| `port/src/core/` | no I/O, no allocation churn, no host clock, no ROM reads |
| `port/src/platform/` | the only place allowed to know about SDL/windowing |
| `port/assets/generated/` | machine output; never committed if it is derived from the ROM |
| `docs/` | decisions and handoffs; historical, not authoritative for behaviour |

### CI / definition of green

```
1. extractors reproduce byte-identical output from the reference ROM
2. recompilation: translation self-check + cross-check on the standard scripts
3. port: unit tests (data asserts), smoke run (boot → walk → warp → shop → save)
4. parity: recorded sessions agree on state, with a budget of known divergences
5. no game data and no ROM in version control
```

## 3.3 Decisions you will have to make, and how to make them

* **Recompile first, port second.** The oracle pays for itself in the first week
  of port work; building the port first means every bug is a coin flip.
* **Frame-level before scanline-level.** Add accuracy only where a measurement
  forces it, and record which measurement did.
* **State before pixels.** Always. A pixel test on a wrong state teaches you to
  fix the wrong thing.
* **Generated data over hand-typed data.** Every table that is typed by hand will
  be subtly wrong and un-diffable.
* **One behaviour per commit, with its measurement.** "Fixes X; parity frame
  moves 5238 → 6130" is a commit message that future-you can use.

## 3.4 The one-page version

Recompilation: decode reachable code from vectors and traces, emit literal C,
model the machine honestly (mapper, PPU, APU, timing, interrupts), keep an
interpreter as a coverage alarm, and verify against an emulator.

Port: extract data, implement the game's own state machine, and prove it against
the oracle frame by frame on recorded inputs; treat every decode as a test, and
never let the presentation decide what is true.

Both: one shared RE substrate, one differential harness, and a rule that every
claim ends with an address or a frame number.

---

## 5. Key terms, and what to search for each

Definitions and sources for the whole vocabulary are in
[`GLOSSARY.md`](GLOSSARY.md); these are the ones this document leans on.

| Term | Meaning in one line | Search phrase |
|---|---|---|
| **static recompilation** | Translate guest code to host C ahead of time, run it on a runtime | `static binary translation` |
| **runtime** | Library providing CPU state, memory map, PPU, APU, cart, timing | `emulator runtime design` |
| **AOT / JIT** | Ahead-of-time vs just-in-time translation | `ahead of time compilation emulator` |
| **HLE / LLE** | Behavioural shortcuts vs hardware-faithful emulation | `high level emulation` |
| **fallback interpreter** | Runs code the translator missed; its count measures coverage | `fallback interpreter recompiler` |
| **trace-seeded** | Use an execution trace to decide what is code before translating | `profile guided binary translation` |
| **code/data separation** | The central problem: which bytes are instructions | `code data separation binary` |
| **recursive descent / linear sweep** | Two ways to find code; the first follows control flow | `recursive descent disassembler` |
| **jump table** | Pointer array behind a computed jump | `jump table recovery` |
| **frame hash** | Fingerprint of visible machine state at a frame | `frame hash regression` |
| **deterministic replay** | Same input stream, identical run — the basis of bisection | `deterministic input replay` |
| **clean room** | Reimplementation from observation, no copied code | `clean room design` |
| **oracle testing** | Compare against a reference implementation | `oracle based testing` |
| **differential testing** | Two implementations, identical input, diff the results | `differential testing` |
| **state parity** | Agreement on the game's variables every frame | `state comparison testing` |
| **golden master** | A recorded expected output kept as a regression test | `golden master testing` |
| **lockstep / desync** | Two runs advancing together; desync = disagreement | `lockstep desync testing` |
| **MBC5 / SRAM / RTC** | Cartridge mapper, battery save RAM, real-time clock | `MBC5 RTC registers` |
| **scanline accuracy** | Modelling mid-frame register changes | `scanline accurate emulation` |
| **VRAM/OAM access blocking** | Video memory is unavailable during drawing periods | `pan docs VRAM OAM access` |

### Sources worth trusting

| Source | Use |
|---|---|
| **Pan Docs** (gbdev.io/pandocs) | First stop for any register or hardware behaviour |
| **Game Boy: Complete Technical Reference** (Gekkio) | Timing and edge cases |
| **The Ultimate Game Boy Talk** (Michael Steil) | The one-hour mental model |
| **GB Recompiled** (github.com/arcanite24/gb-recompiled) | A working GB/GBC static recompiler, with accuracy notes |
| **mgbdis**, **RGBDS** docs | Disassembly and symbol conventions |
| **SameBoy / mGBA / BGB / PyBoy / binjgb** | Accuracy reference vs scripting/tooling |
| **mooneye / blargg test ROMs** | Conformance suites for the runtime |
| **Data Crystal / TCRF** | ROM maps and unused content |

Check a web claim by finding the register it talks about, then confirming the
value in the ROM or an accurate emulator. Community pages are right about formats
and wrong about specifics more often than they are wrong about both.

## 6. Provenance of these notes

These documents were produced from three artifacts, none of which are part of
this repository (they contain ROM-derived data or working-tree state):

| Artifact | What it was used for |
|---|---|
| The retail ROM, hashed | every table dump, every byte-level claim |
| An annotated disassembly of the same engine | routine boundaries, names, cross-references |
| A differential harness (recomp vs port) and recorded input traces | the behaviour claims: first-differing-frame measurements |

Citations inside the per-topic notes (`re/notes/…`, `docs/…`) point at the raw
research notes they were distilled from. Those files are kept for traceability in
the author's working tree and are deliberately not shipped: they contain
longer verbatim excerpts and ROM-derived data than a reference document should.
Every fact worth keeping was rewritten here as a statement with an address, and
can be re-derived from a ROM copy with the method in [`HOW-TO.md`](HOW-TO.md).

