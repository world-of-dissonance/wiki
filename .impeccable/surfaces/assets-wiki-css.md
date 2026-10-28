---
version: 1
slug: "assets-wiki-css"
primary_target: "assets/wiki.css"
related_targets: ["build.py","assets/wiki.js"]
---

# Wiki pages (all generated pages + home)

Scope: every page build.py emits (home, 20 doc pages, search). Mode: Read.
Audience/job: players mid-session looking up a skill, condition or rule (often on a phone beside Minecraft); players reading lore before joining; the DM mid-combat; the doc's author receiving it as a gift.
Constraints: content is the doc verbatim; static GitHub Pages; noindex until reveal; light page required (user found the old site too dark and flat, generic, hard to scan, weak home).

## Direction contract

THESIS: The wiki is a bound reference work, a compendium of Tantalos. Six coloured thumb tabs (Lore, Peoples, Aspects, Arcana, Rules, Catalogs) are the primary navigation, always visible down the right edge, like the cut thumb index of an encyclopedia. Refuses the docs-site default of a grey page tree, a dark theme and floating cards.

OWN-WORLD: Teal book cloth (#1d4a52) masthead with a gilt (#c9a227) rule and crescent stamp; cool India-paper page (#f6f7f3), ink #16202b; tab colours oxblood, green, blue, violet, copper, grey, each owning its chapter band. Spectral SC headwords, Source Serif 4 reading text, Archivo Narrow labels, running heads and § numbers. No boxed cards: space and hairline rules separate entries. Reference tables rank by weight, case and a reversed ink label, never by size.

STORY: A reader lands on the shelf (home), sees six volumes, opens one, and can always jump to another volume by its tab, search with "/", and cite any section by its § number.

FIRST VIEWPORT: Cloth masthead (64px) with crescent, title, and a wide search. Below, a full-width chapter band in the volume's colour carrying the volume name and the page title in Spectral SC. A running head with section guide words. Left margin: § contents list. Centre: the reading column at ~66ch. Right edge: the thumb index, current tab pulled flush with a gilt ribbon on the last-read volume. Phone: thumbs become a bottom tab strip.

FORM: The Thumb-Indexed Compendium, position 3 of my ordered list; seed key 64fe6f4c. Raises: timetable (table ranking by weight/reversal), cutting bench (ribbon on last-read, return to paragraph), origami (strict § margin numbering), cloud quarry (chapter opens on a full tab-colour band), console void (no panels).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
