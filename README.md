# DWM2 — reverse-engineering notes

A complete reverse-engineering reference for **Dragon Warrior Monsters 2**
(Game Boy Color): *Tara's Adventure* and *Cobi's Journey*. The bank map, the
memory map, data structures, the text and script engines, battle maths, breeding,
key worlds, graphics, audio and the link cable — each claim tied to a ROM address
or a file offset, plus the method guides for using it.

The goal is that nobody has to derive this again: someone wanting to build a port,
a static recompilation, a mod, a randomiser or a viewer should be able to start
from these notes and verify each fact in minutes.

## Start here

| Guide | What it covers |
|---|---|
| [`HOW-TO.md`](HOW-TO.md) | **The method.** How to start reverse-engineering a GBC game, the instruments, how to avoid believing wrong things, how to notice and correct your own mistakes, and how a large model should work a problem for accuracy rather than speed |
| [`HOW-TO-RECOMP-AND-PORT.md`](HOW-TO-RECOMP-AND-PORT.md) | **The two builds.** Static recompilation (translator, runtime, code/data separation, banking, interrupts, PPU/APU timing) and a clean-room port (state parity, architecture, extraction, bring-up order), plus the project layout for both |
| [`GLOSSARY.md`](GLOSSARY.md) | Every term used here, one line each, with the search phrase that finds the authoritative source |

Read it in this order depending on what you need:

* **I want to build something.** Read the two guides, then `01` (where everything
  lives), `04` (the frame contract every subsystem depends on) and the files for
  the subsystems you are porting first — field and text, usually.
* **I want to understand one system.** Go straight to its file; every one opens
  with its structure and ends with the addresses and the open questions.
* **I want to check a claim.** The conventions below say how to turn an address
  into a file offset; `HOW-TO.md` §4 says what counts as evidence and §6 how to
  catch a bad decode.

## The reference

| # | File | Contents |
|---|---|---|
| 1 | [`01-rom-map.md`](01-rom-map.md) | Cartridge header, all 256 banks, which bank holds which subsystem, table addresses |
| 2 | [`02-memory-map.md`](02-memory-map.md) | WRAM/HRAM/SRAM map by subsystem: field, text, sprites, battle, link, sound |
| 3 | [`03-sram-save-format.md`](03-sram-save-format.md) | SRAM geometry, the 165-byte monster record, compact records, saved blocks, checksums, key-world records |
| 4 | [`04-engine-core.md`](04-engine-core.md) | Boot, interrupt handlers, the VBlank frame contract, game modes, far-call idiom, both PRNGs |
| 5 | [`05-field-maps-objects.md`](05-field-maps-objects.md) | MapTable and map records, screen/attribute streams, tilesets, object selectors, warps, collision |
| 6 | [`06-text-and-script-vm.md`](06-text-and-script-vm.md) | Charset, text printer, script byte-code and opcodes, talk events, triggers, story flags |
| 7 | [`07-battle-system.md`](07-battle-system.md) | Battle flow, damage formula, status, command block, AI, rewards, arena |
| 8 | [`08-monsters-breeding.md`](08-monsters-breeding.md) | Species tables, stat curves, skills, breeding and eggs, items |
| 9 | [`09-key-worlds.md`](09-key-worlds.md) | Key generation, generated world layout, the SRAM key record, key-world encounters |
| 10 | [`10-menus-towns-services.md`](10-menus-towns-services.md) | Pause menu, shops, vault, inn, name entry, arena, library |
| 11 | [`11-link-cable.md`](11-link-cable.md) | The cable protocol: menu codes, pairing rules, sessions, record formats, seed rule |
| 12 | [`12-audio.md`](12-audio.md) | Sound engine, track format, commands, music ids |
| 13 | [`13-graphics-and-assets.md`](13-graphics-and-assets.md) | Tile format, sprite sheets and meta-sprites, palettes, fonts, art banks |
| 14 | [`14-editions.md`](14-editions.md) | Tara vs Cobi: the byte diff, the hero-variant flag, what is safe to share |

## The repository itself

| File | Purpose |
|---|---|
| [`PROVENANCE.md`](PROVENANCE.md) | what the facts were derived from, the standard each claim was held to, and what was deliberately left out |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | the evidence bar for a correction, and the shape of a useful report |
| [`tools/check.py`](tools/check.py) | layout check: titles, links, the numbered set, no absolute paths, no game data — runs in CI on every push |
| [`LICENSE`](LICENSE) | CC BY 4.0 |

```sh
python3 tools/check.py     # 24 files, 20 Markdown, 0 errors
```

## Conventions

* `$BB:AAAA` — ROM address: bank `$BB`, CPU address `$AAAA`.
  File offset = `bank × 0x4000 + (addr − 0x4000)` for banks ≥ 1; bank `$00` is
  flat `$0000–$3FFF`.
* `$Cxxx` / `$FFxx` — WRAM / HRAM. `0x…` — a file offset in a ROM or `.sav`.
* Story flags are the flat numbering in `wStoryFlags` (`$CBD7`): flag *n* is bit
  `n & 7` of byte `$CBD7 + (n >> 3)`.
* Claims that are inferred rather than verified are marked *unconfirmed*; a few
  files carry confidence tags (**C1** listing, **C2** listing + ROM agree,
  **C3** verified on a running cartridge).

## Verify it yourself

Nothing here asks for trust. Every table is a pointer table plus a stride and is
one line of Python away:

```python
rom = open('rom.gbc', 'rb').read()
bank, addr = 0x11, 0x44B8                       # the field MapTable
off = addr if bank == 0 else bank * 0x4000 + (addr - 0x4000)
print(hex(off), rom[off:off + 32].hex(' '))
```

The guides explain the full procedure, including what a wrong decode looks like
and which invariants catch it. Cross-checks used for these notes: byte-level
table dumps from a retail dump, an annotated disassembly of the same engine, a
live execution trace, and a frame-by-frame differential comparison between a
static recompilation and a clean-room port.

## What is not here

No ROM, no extracted assets, no game code, no save files. Every table in these
notes is presented as addresses, structure and a few sample values — you need
your own legally obtained cartridge dump to extract the data itself.

*Dragon Warrior Monsters 2*, *Tara's Adventure* and *Cobi's Journey* are
trademarks of their respective owners. This is an independent, unofficial
compatibility and preservation reference, not affiliated with or endorsed by
them.

## Corrections

Found something wrong? Please open an issue with the file, the claim, and the
evidence that contradicts it (a byte dump, a file offset, or a trace). See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

The text is licensed under [CC BY 4.0](LICENSE). Facts and addresses are not
copyrightable; the prose and structure are, and attribution is appreciated.
