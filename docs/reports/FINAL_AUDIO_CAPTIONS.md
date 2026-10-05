# Final audio captions — 2026-10-05

The owner-authorized caption-only update uses application SHA
`452c6196fbda4f96f6b9d6624e17ea1c677a5643`, tested on the server,
pushed normally and deployed through the protected backup procedure.
Final server evidence: **2026-10-05T09:09:33Z** (12:39:33 Tehran).

## Behavior and verification

Audio headings are **Fave**, **Drop**, **LP Drop** or **EP Drop**, both bold
and linked to `https://t.me/RapFaDrop`. Popular collection tracks retain Fave.
The next line contains `› Spotify · Album` when a confirmed corresponding
production introduction exists, otherwise `› Spotify · SoundCloud`.
Missing links and separators are omitted; no links means no link line.
Validated version relationships retain their optional Instrumental/Reissue/Deluxe
line and confirmed Original link. Titles, artist rows, blank lines and footer
are absent from these audio captions.

Known stored audio defaults migrate as immutable versions, idempotently;
custom templates remain preserved. Album introductions, administrative and
correction messages, the eleven-field metadata policy and quality policy are
unchanged. Later reconciliation and quality edits use the updated audio template.

Server verification passed **78 focused publication/collection tests**, followed
by the exact final SHA's **200 application tests and eight backup tests**, Django
system checks, migrations and migration drift checks. Tests cover conditional
links, headings, escaping, versions, unchanged introductions, known-default
migration/custom preservation, paused caption authorization and replay.

The pre-deployment encrypted recovery point was
`rapfadrop-20261005T083554Z-c8733ad9.tar.age` (1,382,936 bytes).
An isolated restore matched all 43 tables before deployment; upload completed
as backup-channel messages **80/81**. This is upload/restore evidence, not a
claim of a fresh Telegram download/readback of that backup.
Deployment health returned `status=ok, database=ok`.

## Production caption results

All **41 unique audio posts** were edited in place in production channel
`-1004311149640` / `@RapFaDrop`, after verifying bot `8697681226`
(`@RapFaDropBot`), exact channel identity, administrator posting permission and
durable collection/publication bindings. Edited IDs: **4, 5, 6, 7, 9, 10, 11,
12, 13 and 15–46**. Unchanged/skipped IDs: none. Failed/uncertain IDs: none.
Other channel messages, including 8 and 14, were outside this task.

Telegram responses verified both bold and text-link entities over the entire
Fave heading on every post. All 41 message IDs, audio file identities, track and
candidate bindings were preserved. The retained response entities provide
readback evidence without downloading audio again.
An explicit second `refresh-published` run succeeded with **zero additional
attempts**: the durable caption attempt count remained 41. All 41 captions
were already current on replay; no duplicate message or repeated edit was made.
No custom-template conflict was observed in this production collection.

Final durable results and Telegram response entities are recorded in
[safe caption evidence](data/final_audio_caption_evidence.json).
This audit compares the protected pre-edit snapshot with current rows and
compares each edit response's audio identity with the prior send/media edit.
No provider probe, audio acquisition, retag, media replacement, new music send,
deletion or correction reply is part of this task.

All pre-existing artist/source/item/baseline/review/selection/track/media rows
passed field preservation checks, apart from explicitly permitted caption fields
and routine source polling timestamps. There are still **83 active verified
Spotify sources**, 131 total sources and **84 baselines**, with zero downstream
jobs. Ordinary scheduled discovery appended Spotify release
`5DGYK44aTDyMJrka40TZ0S` (Amin Tijay — Pellezterari) at
2026-10-05T08:32:20Z, with an identity-review match and open low-confidence review.
This accounts for 4,124→4,125 source items, 1→2 reviews and 192→193 source matches;
it was not acquired or published. The first audit rejected these count changes;
inspection established their scheduled discovery provenance, and the corrected
audit permits validated append-only discovery records while comparing every
pre-existing row. The caption edits themselves had all succeeded.
The one-shot edit service therefore initially ended with an audit failure;
after correcting the audit and completing replay it is inactive. The previous
acquisition service was independently verified inactive with MainPID 0.
No application/configuration change beyond the tested caption capability and
known-default migration was needed on the server. No remaining caption blocker.

The earlier background collection already produced 41 unique posts; this task
does not claim the complete Popular inventory has been published. Its frozen
83-artist, 166-slot, 155-native-row inventory remains paused, with 113 native
rows still unposted. The previous acquisition service is stopped; metadata
discovery remains active, while the bridge and ordinary publication remain OFF.
Stop after the caption update; no automatic future publication is activated.
