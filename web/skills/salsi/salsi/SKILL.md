---
name: salsi
description: Write Persian with Persian words. Use when writing, editing, translating or reviewing Persian (Farsi) prose — articles, documentation, posts, essays, UI copy — to replace loanwords with Persian equivalents while leaving technical terminology, proper nouns and code untouched. Also use when the user asks for پارسی سره, سره‌نویسی, فارسی‌سازی, or "make this text more Persian".
license: MIT
---

# سالسی — Write Persian with Persian words

Persian prose is full of borrowed words that have perfectly good Persian
equivalents. Replacing them makes writing clearer and more native. Replacing
them *carelessly* makes writing wrong — it mangles technical terms, changes
meaning, and produces words no reader recognises.

This skill is about the difference.

## The one rule that matters

**A loanword is only worth replacing when the replacement is at least as clear
to the reader.** Purity is never worth clarity. If you are unsure whether a
reader would recognise the Persian equivalent, keep the original.

## Workflow

1. **Scan** the text to find candidates:

   ```bash
   salsi scan article.md --format json
   ```

   If `salsi` is not on PATH, this skill ships its own copy — run
   `./bin/salsi` from this skill's directory instead. It needs nothing
   installed beyond Python 3.10 and carries the full 20,129-word lexicon.

   Add `--domain tech` (or `medical`, `legal`, `science`, `business`) so the
   terminology of that field is protected. Add `--topic <subject>` to help the
   scanner pick the right sense of an ambiguous word.

2. **Read each finding.** Every one carries `level`, `ambiguous`, and a `sense`
   label per suggestion. Apply the judgement rules below. Most findings will be
   *rejected* in a technical document — that is the expected outcome, not a
   failure.

3. **Apply** with your normal editing tools, one considered change at a time.
   For the settled subset only, `salsi apply article.md` does it mechanically.

4. **Show the user a diff and the reasoning** before finalising. Never rewrite
   someone's text wholesale without showing what changed.

Only if you cannot run commands at all — no shell available — work from
`reference/core-words.md`, which holds the settled replacements as a plain
table. It is ~119 words against the lexicon's 20,129, so say plainly that you
are working without the full dictionary and be correspondingly conservative.

## Judgement rules

### Never touch

- Anything inside code fences, inline code, URLs, file paths, commands,
  identifiers, or configuration keys. (`salsi` already excludes these; if you
  are working by hand, you must too.)
- Quoted text from another author, or a cited title. Quotations are evidence,
  not drafts.
- Proper nouns: people, places, companies, products, brands, standards bodies.
- Numbers, units, and formulas.

### Technical terms — the part people get wrong

Ask **what the field itself writes**, not what a dictionary offers.

- Use the Persian term when the field already uses it: `کامپیوتر`→`رایانه`,
  `دیتابیس`→`پایگاه داده`, `دانلود`→`بارگیری`, `فایل`→`پرونده`. These read as
  normal technical Persian.
- Keep the loanword when it *is* the term of art: `الگوریتم`, `پروتکل`,
  `کامپایلر`, `ای‌پی‌آی`, `توکن`, `کرنل`. Translating these makes the text
  harder for its own audience.
- Never invent a term. If the lexicon offers something you have not seen used
  in that field, do not be the first to use it in someone else's document.
- In medicine, law and standards, a term can have a *defined* meaning. Changing
  it changes the content. Leave it.

### Meaning first

The lexicon is keyed by spelling, not sense. Check the `sense` label on each
suggestion before using it.

- `سرور` in a systems document is *server*, not `سُرور` "joy".
- `استرس` is `تنش` in mechanics but `دلهره` in psychology.
- `تست` is `آزمون` in science, but a `تُست` is bread.

When `ambiguous` is true, either pick the sense the context demands or leave the
word alone. Never take the first suggestion because it is first.

### Register and audience

- Formal, literary and cultural writing tolerates more purism.
- Technical documentation, legal text and UI copy tolerate much less: the reader
  is there to accomplish something, not to admire the prose.
- Casual and conversational text should stay casual. `سلام، فایلو فرستادم`
  should not become a treatise.

### Craft

- **Be consistent.** Once you choose `پرونده` for `فایل`, use it everywhere in
  the document, including headings.
- **Introduce once.** When an unfamiliar equivalent genuinely earns its place,
  the first occurrence may carry the original: `بارگیری (دانلود)`. Once.
- **Fix the grammar around the change.** Persian suffixes change shape:
  `فایل‌ها`→`پرونده‌ها`, `خانه‌ای` patterns, ezafe. Re-read the sentence after
  each edit.
- **Do not increase word count much.** A three-word phrase replacing one word is
  usually a bad trade.

### When the user asks for سره‌نویسی

Full purism (`--level pure`) also targets Arabic loanwords that are ordinary
modern Persian — `کتاب`, `علم`, `قانون`. Only do this when the user explicitly
asks for it, and warn that the result reads as a deliberate literary style, not
as neutral Persian.

## Levels

| Level | What it offers | Use it for |
| --- | --- | --- |
| `safe` | Only the curated, settled replacements | Automation, first pass, anything you cannot review |
| `standard` (default) | Everything except naturalised and protected words | Normal editing with review |
| `pure` | The full lexicon | سره‌نویسی, only on request |

## Commands

```bash
salsi scan FILE [FILE...]        # --format text|json|markdown
salsi apply FILE                 # settled replacements only; --diff to preview
salsi lookup WORD                # what does the lexicon offer, and in which sense
salsi domains                    # protection profiles available
salsi info                       # lexicon size and provenance

# useful flags
--level safe|standard|pure
--domain tech|medical|legal|science|business    # repeatable
--topic "زبان‌شناسی"                            # disambiguates senses
--protect WORD / --protect-file FILE            # your own exceptions
```

Exit code with `--strict` is non-zero when anything is found, which makes
`salsi scan --level safe --strict` usable as a CI or pre-commit check.

## Reference

- `reference/judgement.md` — worked examples of accepting and rejecting findings
- `reference/core-words.md` — the settled replacements, usable without the CLI
- `reference/install.md` — installing `salsi` and this skill elsewhere

## Credit

The word list and every Persian equivalent come from **پاسبان (Pasban)** —
<https://pasbans.ir>. This skill is a way of using their work; it is not a
substitute for it. Keep the attribution when you redistribute.


---
### 📚 پیوست مرجع: core-words
# Settled replacements

Generated from `salsi/data/curated.tsv` — do not edit by hand; run
`python3 scripts/build_reference.py`.

These are the replacements considered settled: a Persian reader recognises
them, they carry one meaning, and they are safe to apply without a case-by-case
decision. They are the *only* thing `salsi apply` will change on its own.

Use this table when the `salsi` CLI is unavailable. It is a small fraction of
the full lexicon (20,071 entries) — for anything not listed here, you need
the CLI or you should leave the word alone.

Everything here comes from the Pasban dictionary (<https://pasbans.ir>), except
where a note marks a deliberate departure.

| واژهٔ بیگانه | برابر پارسی | یادداشت |
| --- | --- | --- |
| کامپیوتر | رایانه |  |
| دانلود | بارگیری |  |
| آپلود | بارگذاری |  |
| پرینتر | چاپگر |  |
| پرینت | چاپ |  |
| فکس | نمابر |  |
| اسکنر | پویشگر |  |
| اسکن | پویش |  |
| سیستم | سامانه |  |
| فایل | پرونده |  |
| فولدر | پوشه |  |
| دایرکتوری | پوشه |  |
| لینک | پیوند |  |
| پسورد | گذرواژه |  |
| رمز عبور | گذرواژه |  |
| یوزر | کاربر |  |
| یوزرنیم | نام کاربری |  |
| مانیتور | نمایشگر |  |
| کیبورد | صفحه‌کلید | پاسبان: تخته‌مدنگ — در نوشتار امروز به کار نمی‌رود |
| اسپیکر | بلندگو |  |
| دیتا | داده |  |
| دیتابیس | پایگاه داده |  |
| بک‌آپ | پشتیبان‌گیری |  |
| آپدیت | به‌روزرسانی |  |
| سایت | تارنما |  |
| وب‌سایت | تارنما |  |
| سرچ | جست‌وجو |  |
| چت | گپ |  |
| آنلاین | برخط |  |
| آفلاین | برون‌خط |  |
| سرور | کارساز | پاسبان: شادمانی — سُرورِ فارسی را با server یکی گرفته |
| کلاینت | کارخواه |  |
| هاست | میزبان |  |
| هاستینگ | میزبانی |  |
| دامین | دامنه |  |
| ایمیل | رایانامه |  |
| اس‌ام‌اس | پیامک |  |
| سی‌دی | لوح فشرده |  |
| پلتفرم | سکو |  |
| اپ | برنامک |  |
| فرمت | قالب |  |
| سیو | ذخیره‌سازی |  |
| پروفایل | نمایه |  |
| کامنت | دیدگاه |  |
| لایک | پسند |  |
| فالوور | دنبال‌کننده |  |
| هکر | رخنه‌گر |  |
| ویروس | ویروس | واژهٔ دانشی جهانی؛ دست نخورد |
| تکنولوژی | فناوری |  |
| تکنیک | فن |  |
| اتوماتیک | خودکار |  |
| اتومات | خودکار |  |
| اتوماسیون | خودکارسازی |  |
| مکانیزم | سازوکار |  |
| پروسه | فرایند |  |
| پتانسیل | توان |  |
| پاور | توان |  |
| سنسور | حسگر |  |
| اکچویتور | کارانداز |  |
| ترمینال | پایانه |  |
| هلیکوپتر | بالگرد |  |
| هلی‌کوپتر | بالگرد |  |
| اتوبان | بزرگراه |  |
| پارکینگ | توقفگاه |  |
| بیولوژی | زیست‌شناسی |  |
| اکولوژی | بوم‌شناسی |  |
| اکوسیستم | زیست‌بوم |  |
| ژئولوژی | زمین‌شناسی |  |
| جئولوژی | زمین‌شناسی |  |
| سایکولوژی | روان‌شناسی |  |
| آرکئولوژی | باستان‌شناسی |  |
| متدولوژی | روش‌شناسی |  |
| متد | روش |  |
| آنالیز | واکاوی |  |
| ریسرچ | پژوهش |  |
| ساینس | دانش |  |
| یونیورسیتی | دانشگاه |  |
| آکادمیک | دانشگاهی |  |
| تز | پایان‌نامه |  |
| دیکشنری | واژه‌نامه |  |
| گرامر | دستور زبان |  |
| آرتیکل | نوشتار |  |
| پاراگراف | بند |  |
| سابتایتل | زیرنویس |  |
| ادیت | ویرایش |  |
| ادیتور | ویراستار |  |
| اکو | پژواک |  |
| فستیوال | جشنواره |  |
| کنفرانس | همایش |  |
| سمینار | هم‌اندیشی |  |
| ورکشاپ | کارگاه |  |
| دپارتمان | بخش | پاسبان: گپارمان — واژه‌ای ساختگی و ناشناخته |
| اسپانسر | پشتیبان |  |
| کمپین | پویش |  |
| فیدبک | بازخورد |  |
| آپشن | گزینه |  |
| مارکتینگ | بازاریابی |  |
| لیدر | رهبر |  |
| تیم | گروه |  |
| استپ | گام |  |
| ریپورت | گزارش |  |
| موتیویشن | انگیزه |  |
| تایمر | زمان‌سنج |  |
| تایم | زمان |  |
| دکتر | پزشک |  |
| نرس | پرستار |  |
| هاسپیتال | بیمارستان |  |
| کلینیک | درمانگاه |  |
| آکتور | بازیگر |  |
| دیرکتور | کارگردان |  |
| سناریو | فیلم‌نامه |  |
| استادیوم | ورزشگاه |  |
| پارک | بوستان |  |
| موزیسین | نوازنده |  |
| لیست | فهرست |  |
| فرم | برگه |  |
| کپی | رونوشت |  |
| موبایل | تلفن همراه |  |
| اکانت | حساب کاربری | پاسبان: شمارد/مارد — ناشناخته |

_119 rows, 118 distinct words._

---
### 📚 پیوست مرجع: install
# Installing

## The CLI

**You do not have to install anything.** `./install.sh` bundles the engine and
the full lexicon into every skill it installs, reachable as `bin/salsi` inside
the skill folder. Python 3.10+ is the only requirement, and there are no
dependencies.

Installing it on your PATH as well is optional:

```bash
pip install salsi      # or, from a clone: pip install -e .
salsi info
```

On systems where pip refuses to touch the environment (PEP 668), use the
bundled copy or a virtualenv. `python3 -m salsi` works identically to
`salsi` wherever the package is importable.

## The skill

`./install.sh` from the repository root detects what you have and offers to
install into each. Or do it by hand:

| Tool | Where the skill goes |
| --- | --- |
| Claude Code (all users) | `~/.claude/skills/salsi/` |
| Claude Code (one project) | `.claude/skills/salsi/` |
| Claude.ai / Claude Desktop | `./install.sh --bundle ./dist` then upload that folder |
| Codex | append `skills/adapters/AGENTS.md` to your `AGENTS.md` |
| Cursor | `.cursor/rules/salsi.mdc` |
| Windsurf | `.windsurf/rules/salsi.md` |
| Cline / Roo | `.clinerules/salsi.md` |
| Continue | `.continue/rules/salsi.md` |
| Zed | add to `.rules` |
| Anything else | paste `skills/adapters/PROMPT.md` into the system prompt |

Copy the whole `salsi/` directory, not just `SKILL.md` — the bundled
engine and the reference files are what make the skill work on its own. Use
`./install.sh --bundle <dir>` to produce that self-contained folder anywhere.

## Without a shell

Where an assistant cannot run commands at all, the skill falls back to
`reference/core-words.md` — the settled replacements only, ~119 words rather
than 20,129. That is a real reduction in capability, so the skill is told to
say when it is working that way.

## As a check in CI

```yaml
- run: pip install salsi
- run: salsi scan docs/**/*.md --level safe --strict
```

`--level safe` only fails on replacements nobody argues about, which is the
right bar for a gate that blocks a merge.

## As a git hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
git diff --cached --name-only --diff-filter=ACM | grep '\.md$' \
  | xargs -r salsi scan --level safe --strict
```

---
### 📚 پیوست مرجع: judgement
# Worked examples

Every example below is a real finding from `salsi scan`. What matters is not the
verdict but the reason — the same reasoning applied to a finding you have not
seen before should give you the right answer.

---

## Accept

### The field already writes the Persian word

> این **سیستم** روی سه **سرور** اجرا می‌شود و **فایل‌های** پیکربندی را از
> **دیتابیس** می‌خواند.

→ **سامانه**, **کارساز**, **پرونده‌های**, **پایگاه داده**

Persian technical writing uses all four. Nothing is lost, and the sentence
becomes more readable, not less.

### The loanword adds nothing

> کاربران به **تدریج** با آن آشنا می‌شوند.

→ **کم‌کم**

`کم‌کم` is ordinary Persian that every reader knows. There is no cost.

### The suffix follows along cleanly

> **فایل‌ها** را **دانلود کنید**.

→ **پرونده‌ها** را **بارگیری کنید**.

Note the verb keeps the reader's inflection. `بارگیری کردن` dropped in
unchanged would have been wrong.

---

## Reject

### It is the term of art

> این **الگوریتم** از یک **پروتکل** رمزنگاری استفاده می‌کند.

The lexicon has entries for both. Do not use them. A reader in this field knows
these words precisely; a coined replacement makes the sentence *less* exact.

### The suggestion is a different word

> سه **سرور** در این اتاق هست.  →  سه **شادمانی** در این اتاق هست.

The lexicon keys on spelling. `سُرور` "joy" and `server` are written the same
way. The `sense` label said `سُرور به چم خوشحالی` — that was the warning.

Always read the sense label. This is the single most common way an automated
rewrite goes wrong.

### Nobody would recognise it

> رعایت **حریم** خصوصی کاربران.  →  رعایت **بژکما**ی کاربران.

Formally correct, practically unusable. A word that sends the reader to a
dictionary has failed at the one job prose has.

### It is a quotation

> فردوسی می‌گوید: «توانا بود هر که دانا بود»

Never edit inside a quotation, even to "improve" it.

### It is inside code

> مقدار `system.config.path` را عوض کنید.

`salsi` excludes inline code automatically. When editing by hand, watch for
identifiers that happen to be Persian-adjacent.

### The trade is bad

> این کار **ریسک** دارد. → این کار **خطرِ احتمالیِ زیان** دارد.

One word became three. Keep the original, or find a one-word equivalent.

---

## Ambiguous — decide from context

`استرس` has two senses in the lexicon:

| Context | Choose |
| --- | --- |
| مهندسی، مکانیک، مقاومت مصالح | `تنش` |
| روان‌شناسی، سلامت، زندگی روزمره | `دلهره` |

Pass `--topic مکانیک` or `--topic روانی` and the matching sense is ranked first.
If the context does not tell you, leave the word alone and say why.

---

## A note on quantity

Scanning a normal Persian article at `standard` level flags roughly one word in
six. Accepting all of them would produce something no one wants to read.

A good pass on a technical document changes **a handful of words**. If your diff
touches every other line, you have gone too far — go back and keep only the
changes that a reader of that document would call an improvement.