---
name: World of Dissonance Compendium
description: The Tantalos setting doc set as a cloth-bound, thumb-indexed reference work.
colors:
  cloth: "#1d4a52"
  cloth-deep: "#153840"
  cloth-line: "#33656c"
  cloth-text: "#e3eeea"
  cloth-mute: "#bcd4cf"
  gilt: "#c9a227"
  gilt-soft: "#e7cf7c"
  gilt-ink: "#1f1806"
  page: "#f6f7f3"
  page-edge: "#e9ece5"
  plate: "#ffffff"
  ink: "#16202b"
  ink-2: "#3a4450"
  mute: "#5b6570"
  rule: "#d6dbd3"
  rule-soft: "#e4e8e1"
  link: "#1d5b66"
  vol-lore: "#8a2f3c"
  vol-peoples: "#2f6b4f"
  vol-aspects: "#2b5d9b"
  vol-arcana: "#6b3f8f"
  vol-rules: "#a8561a"
  vol-catalogs: "#626870"
typography:
  display:
    fontFamily: "Spectral SC, Palatino Linotype, Georgia, serif"
    fontSize: "clamp(40px, 5.6vw, 78px)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.03em"
  headline:
    fontFamily: "Spectral SC, Palatino Linotype, Georgia, serif"
    fontSize: "clamp(30px, 3.4vw, 48px)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "0.02em"
  title:
    fontFamily: "Spectral SC, Palatino Linotype, Georgia, serif"
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.22
    letterSpacing: "0.02em"
  title-sm:
    fontFamily: "Spectral SC, Palatino Linotype, Georgia, serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.03em"
  body:
    fontFamily: "Source Serif 4, Iowan Old Style, Georgia, serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.62
  label:
    fontFamily: "Archivo Narrow, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.14em"
  data:
    fontFamily: "Archivo Narrow, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.45
    fontFeature: "tnum"
rounded:
  hairline: "2px"
  field: "3px"
  thumb: "12px 0 0 12px"
spacing:
  gutter-phone: "16px"
  gutter: "28px"
  leaf-edge: "40px"
  column-gap: "32px"
  column-gap-wide: "64px"
  margin-column: "220px"
  thumb-width: "132px"
  masthead: "64px"
  running-head: "40px"
components:
  button-primary:
    backgroundColor: "{colors.gilt}"
    textColor: "{colors.gilt-ink}"
    rounded: "{rounded.hairline}"
    padding: "10px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.gilt-soft}"
    textColor: "{colors.gilt-ink}"
  button-cloth:
    backgroundColor: "{colors.cloth}"
    textColor: "{colors.cloth-text}"
    rounded: "{rounded.hairline}"
    padding: "10px 20px"
    height: "44px"
  button-cloth-hover:
    textColor: "{colors.gilt-soft}"
  search-field:
    backgroundColor: "{colors.cloth-deep}"
    textColor: "{colors.plate}"
    rounded: "{rounded.field}"
    padding: "0 40px"
    height: "40px"
  masthead:
    backgroundColor: "{colors.cloth}"
    textColor: "{colors.cloth-text}"
    height: "{spacing.masthead}"
  thumb-tab:
    textColor: "{colors.plate}"
    rounded: "{rounded.thumb}"
    padding: "0 12px 0 16px"
    width: "{spacing.thumb-width}"
  table-head:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.plate}"
    typography: "{typography.label}"
    padding: "6px 12px"
  table-cell:
    typography: "{typography.data}"
    padding: "8px 12px"
  record-cost-stamp:
    textColor: "{colors.plate}"
    typography: "{typography.label}"
    padding: "4px 7px 3px"
---

# Design System: World of Dissonance Compendium

## Overview

**Creative North Star: "The Thumb-Indexed Compendium"**

The wiki is set as a bound reference work on Tantalos: a teal book-cloth cover with a gilt rule and crescent stamp, cool India-paper leaves, and six coloured thumb tabs cut into the right edge, one per volume (Lore, Peoples, Aspects, Arcana, Rules, Catalogs). Every surface behaves like a page in that book. A volume colour owns its chapter band, its thumb tab, its section numbers and its list markers; nothing else borrows it.

Density is that of a good encyclopedia: a ~68ch reading column, a contents margin to its left, a running head with guide words above it, and sections numbered with § so any passage can be cited at the table. Entries are separated by space and hairline rules, never by boxes. Reference tables carry their hierarchy in weight, case and a reversed ink head, never in size.

The page is a single committed light theme (`color-scheme: light`). There is no dark variant by design: it is a book read under lamplight or beside the game, and the previous dark docs-site look is the confirmed rejection. Grey page trees, dark themes and floating cards are the anti-references.

**Key Characteristics:**
- Cloth-and-gilt masthead, colophon and title page; paper everywhere else.
- Six volume colours, each scoped to one volume through a single `--vol` variable.
- Thumb index as primary navigation: right edge on desktop, fixed bottom strip on phones.
- § numbering hung in the left gutter at 1101px and wider.
- Hairlines and ink rules instead of cards; flat paper with one floating layer (search results).
- Three faces with fixed jobs: Spectral SC headwords, Source Serif 4 text, Archivo Narrow labels and data.

## Colors

A cool paper page under a teal cloth cover, with gilt as the only metal and six saturated volume inks that each stay inside their own volume.

### Primary
- **Teal Book Cloth** (cloth): masthead, colophon, title page, phone thumb strip backing and the browser theme colour. **Cloth Deep** (cloth-deep) is the recessed search well; **Cloth Line** (cloth-line) its stroke and the ghost-button border; **Cloth Text** and **Cloth Mute** are the type colours on cloth.

### Secondary
- **Gilt** (gilt): the 3px rule under the masthead, above the colophon, atop the search results and the phone thumb strip; the crescent seal; the last-read ribbon; the primary button; the focus ring (2px outline, 2px offset); text selection at 45% mix. **Soft Gilt** (gilt-soft) sets the wordmark and title-page title on cloth and is the primary button hover. **Gilt Ink** (gilt-ink) is the only text colour placed on gilt.

### Tertiary
- **Volume inks**: Oxblood (vol-lore), Forest (vol-peoples), Lapis (vol-aspects), Violet (vol-arcana), Copper (vol-rules), Slate (vol-catalogs). Each fills its volume's thumb tab and chapter band with white type, and inside that volume tints § numbers, h4 labels, list markers, the running head's guide words, the active contents entry, record cost stamps, strong table cells, link hover and the 6% table-row hover.

### Neutral
- **India Paper** (page): the body ground; also the running head ground and the current sibling tab in the chapter band, so the band appears to open onto the page.
- **Page Edge** (page-edge): the gutter gradient behind the desktop thumbs, inline code ground, scrollbar track.
- **Plate White** (plate): picture plates and the search results sheet.
- **Ink** (ink): text, reversed table heads, 2px table and pager head rules. **Ink 2** (ink-2) for secondary text and blockquotes; **Mute** (mute) for counts, captions and running-head text.
- **Rule** (rule) and **Soft Rule** (rule-soft): every hairline divider. **Link** (link): a deep teal kin to the cloth, underlined at 45% opacity.

### Named Rules
**The One Volume Rule.** Volume colour is set once per page through `--vol` (a `v-*` class on body or on a home-page volume section) and never hard-coded on a component. A page wears exactly one volume ink; the home contents and the thumb index are the only places all six appear together.

**The Gilt Is Metal Rule.** Gilt appears as rules, the seal, the ribbon, focus and the one primary action. It never fills a text area or becomes a body-text colour on paper.

**The One Light Page Rule.** There is no dark variant. Do not add `prefers-color-scheme: dark` styles; the cloth surfaces already supply the dark notes.

## Typography

**Display Font:** Spectral SC (with Palatino Linotype, Georgia)
**Body Font:** Source Serif 4, optical sizing on (with Iowan Old Style, Georgia)
**Label/Mono Font:** Archivo Narrow (with Arial Narrow, Roboto Condensed); inline code uses the system monospace stack

**Character:** Small-capital headwords give every title the look of a dictionary entry; a sturdy text serif carries long lore; a condensed grotesque handles every label, number and table so the apparatus never competes with the prose.

### Hierarchy
- **Display** (700, clamp(40px, 5.6vw, 78px), 1): the title-page title on cloth, in Soft Gilt.
- **Headline** (700, clamp(30px, 3.4vw, 48px), 1.08): the entry title inside the chapter band. Volume names in the band use 30px; home volume heads 26px.
- **Title** (700, 27px, 1.22): section heads (h2) with a hairline above. **Title Small** (700, 20px, 1.3) for h3; skill record names and pager titles use 19px.
- **Body** (400, 18px, 1.62; 17px on phones): reading text, max 68ch. Italic for blockquotes, volume blurbs and blank entries.
- **Label** (Archivo Narrow 600-700, 11-13px, uppercase, 0.14-0.24em tracking): running head, thumb labels, h4, table heads, record stat labels, contents summary, pager direction, gallery count.
- **Data** (Archivo Narrow 500, 15px, 1.45, tabular figures): all tables; record stat values at 13px.

### Named Rules
**The Three Jobs Rule.** Spectral SC names things, Source Serif 4 tells things, Archivo Narrow labels and counts things. A face never takes another face's job.

**The Weight Not Size Rule.** In tables and records, rank by weight, case and reversal (ink head with white type, a volume-coloured cost stamp), never by enlarging type.

**The Section Mark Rule.** h2 and h3 carry a § number (§3, §3.1) in Archivo Narrow 700 in the volume ink. From 1101px it hangs in the left gutter at 14px; below that it sits inline at 0.62em.

## Layout

The desktop page is a two-part book: a leaf (minmax(0, 1fr)) and a 132px thumb column. Inside the leaf, the chapter band and the spread share one grid: a 220px contents margin and the reading column, separated by 32px (64px at 1101px and wider, so the hung § numbers have room). Left gutters are 28px (respecting safe-area insets), the right edge 40px.

Two things stick on desktop: the 64px cloth masthead at the top, and the 40px running head directly beneath it, whose right side shows the guide words of the section in view (updated by an IntersectionObserver). The contents margin and thumb column are sticky below them. Anchors scroll with `scroll-padding-top` equal to masthead + running head + 16px.

At 1100px and below, the margin column narrows to 180px with a 24px gap and the home contents drop to one column. At 820px and below (phones): the masthead becomes static and scrolls away, search wraps to a full-width row, the thumbs become a fixed 58px bottom strip of six equal tabs on cloth with a gilt top rule (body gains matching bottom padding), the band stacks and its sibling tabs scroll sideways, the contents margin becomes a collapsible "Show / Hide" disclosure, and the running head shows only the guide words and hides when empty. Gutters are 16px.

The home page opens on a cloth title page (stamp at left, title, one-line sub, the intro's first paragraph as an italic quote, actions) followed by a two-column contents of the six volumes, each entry with a dotted leader to its § count.

## Elevation & Depth

Flat paper. Depth comes from material (cloth against paper), hairlines and ink rules, and from the thumb tabs physically shifting, not from shadows. The search results sheet is the only floating layer.

### Shadow Vocabulary
- **Results sheet** (`box-shadow: 0 18px 40px -12px rgba(16, 32, 40, .35)`): the search dropdown only.
- **Field focus halo** (`box-shadow: 0 0 0 3px` gilt at 30%): the search input on focus.
- **Tab notch** (`box-shadow: -10px 0 0 -4px` page colour): the current desktop thumb, a paper-coloured cut, not a shadow.
- **Phone tab marker** (`box-shadow: inset 0 4px 0 #fff`): current/hovered tab in the bottom strip.

### Named Rules
**The No Cards Rule.** Entries, volumes, records and results are separated by space and hairlines (rule, rule-soft) or a 2px ink head rule. Never wrap content in a bordered, shadowed or rounded box.

## Shapes

Almost square. Buttons, inline code and gallery arrows use a 2px corner; the search field, its key hint and the band's sibling tabs (top corners only) use 3px. The one rounded silhouette is the thumb tab: 12px on its outer left corners and square against the fore-edge, like a cut index tab (square everywhere in the phone strip). The last-read ribbon is a gilt bookmark with a swallowtail notch (clip-path). The crescent seal is set at -24deg in the masthead and on the title page.

Rules are the main form element: 3px gilt under the masthead and above the colophon, results sheet and phone strip; 2px ink above tables and the pager; 1px ink below tables; 1px hairlines between sections, entries and rows.

## Components

### Buttons
Upright, tracked and plain; they live only on the cloth title page.
- **Shape:** near-square (2px), min-height 44px, padding 10px 20px, Archivo Narrow 700 14px, uppercase, 0.1em tracking.
- **Primary:** gilt fill with gilt-ink text ("Begin at Vol. I"); hover lifts to soft gilt.
- **Cloth (ghost):** transparent on cloth, cloth-line border, cloth-text; hover turns text soft gilt and border gilt. Used for "Make a character" and the "Continue: …" resume button that appears from the last-read record.
- **Phone:** actions stack full width, centred.

### Inputs / Fields
- **Search:** a recessed well on the cloth (cloth-deep fill, 1px cloth-line, 3px corners, 40px tall), Archivo Narrow 500 15px in white, a stroked magnifier at left and a "/" key hint at right (hidden on phones). "/" focuses it from anywhere.
- **Focus:** border turns gilt plus a 3px gilt halo at 30%. Elsewhere, focus is a 2px gilt outline with 2px offset.
- **Results:** a plate-white sheet under a 3px gilt top rule, each hit as path label (11px uppercase mute), Spectral SC headword (16px) and a serif excerpt with gilt-tinted matches; arrow keys move a paper-coloured selection.

### Navigation
- **Thumb index:** six tabs stacked down the right edge in equal rows, each a volume ink with white type: roman numeral, uppercase name, and a two-word hint. Tabs sit inset 20px from the column edge, slide to 10px on hover (0.28s, cubic-bezier(.2, .8, .2, 1)), and the current volume pulls flush with a paper notch. The last-read volume carries the gilt ribbon. On phones the strip is fixed to the bottom, hints hidden.
- **Chapter band:** a full-width field in the volume ink holding "Vol. N / Name", the entry title in Spectral SC, and the volume's sibling entries as tabs; the current sibling is paper-coloured, so the band opens onto the page.
- **Running head:** sticky uppercase line, volume · entry at left in mute, current § guide words at right in the volume ink.
- **Contents margin:** "In this entry" list with § numbers in tabular figures; the section in view goes ink and bold with its number in the volume ink.
- **Pager:** two halves under a 2px ink rule, direction label above a Spectral SC title, split by a hairline.

### Reference Table (signature)
A timetable, not a spreadsheet: 2px ink rule on top, 1px ink at the bottom, an ink-reversed uppercase head row, hairline row dividers, bold first column, strong cells in the volume ink, 6% volume-tinted row hover. Wide tables scroll horizontally inside their wrapper.

### Skill Record (signature)
The doc's one-row skill tables are recast as dictionary records: Spectral SC name (19px) and a volume-coloured cost stamp (EP n) on one line, the effect in body serif beneath at full width, then a run of stat pairs (11px uppercase mute label, 13px value). Blank costs become an outlined stamp. Records are divided by hairlines, never boxed.

### Plates and Galleries (signature)
A single picture is a plate: white mat, 1px hairline, 8px padding, max 520px tall. Several adjacent pictures become a horizontal snap strip on one plate with square-ish ink-outlined prev/next buttons (38px, invert to ink on hover, 30% when disabled), arrow-key support and an uppercase "n / N" count beneath.

### Contents Entry (home)
Volume head as a volume-ink bar with "Vol. N" and the name in Spectral SC, an italic blurb, then entries as title, dotted leader and § count in tabular figures; blank entries are italic and mute.

### Skill Tree Diagram (signature)
Under each tree's heading on the Skills page: a figure with a 2px ink head rule, the main path as filled volume-colour tier boxes, then each branch as outlined boxes, tiers joined by volume-colour arrows. Built from the doc's "NAME: tier -> tier -> tier" lines; every box links to its tier entry. On phones the path name stacks above its row.

### Unwritten Slots
Runs of blank skill templates fold into one `details` line: "+ 3 unwritten slots #3–#5" in Archivo Narrow caps, mute; opened records sit at reduced opacity. Folded content is left out of search and summaries.

### Term Link and Popover
A `[Bracketed Term]` the glossary knows is a dotted volume-colour underline. Hover, focus or first tap opens a plate-white card with a gilt head rule: the term in Spectral SC, its definition, and a "Read it in <page>" link. Escape, scrolling (pointer devices) or clicking elsewhere closes it.

## Do's and Don'ts

### Do:
- **Do** scope every volume colour through `--vol` and the `v-*` / `t-*` classes; components read `var(--vol)`.
- **Do** separate content with space and the rule / rule-soft hairlines, and head tables and the pager with a 2px ink rule.
- **Do** rank table and record information by weight, case and reversal: an ink head row, a volume-coloured cost stamp, uppercase 11-12px labels.
- **Do** keep every new heading numbered with § and let it hang in the gutter at 1101px and wider.
- **Do** keep gilt to 3px rules, the seal, the ribbon, focus and the single primary action.
- **Do** keep phone navigation in the fixed bottom thumb strip and let the masthead scroll away.

### Don't:
- **Don't** add a dark theme or `prefers-color-scheme: dark` styles; the single light page is deliberate.
- **Don't** wrap entries, volumes, records or results in cards (bordered, rounded or shadowed boxes).
- **Don't** enlarge type to signal importance inside tables or records.
- **Don't** use a volume colour outside its own volume, or put two volume inks on one entry page.
- **Don't** add shadows beyond the search results sheet and the field focus halo.
- **Don't** set body text in Spectral SC or Archivo Narrow, or headwords in Source Serif 4.
