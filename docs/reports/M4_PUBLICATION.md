# M4 publication and caption report

Observed locally on 2026-10-02, starting from `main` / `origin/main` at `7edcc5354a502ed8ae040c9b9eaf9c05ff2ccb42`. This report covers M4 only. All publication tests used a fake or mocked transport. No real Telegram Bot API request, source activation, baseline, deployment or M5 implementation occurred.

## Durable behavior

Added `Publication`, `PublicationAttempt`, `PublicationChannel`, `AlbumSession`, `PublicationReconciliation`, `PublicationAuditEvent` and immutable-after-use `CaptionTemplate` records. Publication identity is unique by channel and canonical track; a second constraint protects channel/message ID. Attempts retain operation, candidate/previous candidate, payload, response, UTC times and error evidence. A channel row protects concurrent reservation and records a committed pending attempt/lease before network work. PostgreSQL concurrency tests observed one send and one durable publication for two simultaneous requests.

| Observed fixture condition | Durable outcome |
| --- | --- |
| Successful send | Message ID/URL and response facts persisted; replay does not send again |
| Definite gateway rejection | Retry due time and sanitized error retained; bounded backoff and review notification |
| Lost response or response-commit interruption | `uncertain` attempt and open reconciliation; no automatic resend |
| Worker lease expires | Pending operation becomes uncertain; operator review required |
| Operator observes success | Existing remote message attached to the reserved identity; no second send |
| Operator confirms non-delivery | Due retry explicitly reopened with actor/evidence audit |
| Local media no longer ready | Publication routes to review; unrelated reserved work continues |
| Media edit fails | Original message/candidate retained; only the edit is retried |

M3 readiness, confidence and local file eligibility are rechecked on audio sends/retries. Music-player sends are restricted to MP3/M4A within a conservative 50,000,000-byte cap. Original validated/prepared media is retained for safe recovery and upgrades. The live gateway uses Bot API operations only, bounded HTTPS requests and sanitized structured errors; no user-account/session automation is implemented. Audio thumbnails are derived as JPEG within 320×320 and 200,000 bytes without modifying source audio. These implemented limits follow the [official Bot API documentation](https://core.telegram.org/bots/api#sendaudio); actual live behavior was not probed.

## Captions and template evidence

JSON templates configure literal headers, labels, conditional row order and footer. Dynamic display text and links are escaped for HTML; credential-bearing/non-HTTPS links are rejected. Every publication retains its chosen version and rendered output; changing a referenced template is refused, and a newer version does not alter a historical caption edit.

Observed rendered single fixture with only Spotify:

```html
<b>DROP</b>

<a href="https://open.spotify.com/track/example?a=1&amp;b=2">Spotify</a>

t.me/RapFaDrop
```

Observed introduction rules include this escaped Persian/Latin fixture:

```html
<b>راه &amp; &lt;script&gt; 🎧</b>
EP · هیچ‌کس × Artist &lt;Two&gt;
feat. <i>Guest &amp; One</i> · <i>مهمان</i>

پیش‌تر از این آلبوم منتشر شده:
› <a href="https://t.me/test_channel/12">Earlier &lt;single&gt;</a>

@RapFaDrop
```

Tests verified complete omission of missing video/platform/feature/prior-single blocks, a single platform with no slash, removable LP/EP track headers, title-only bold and guest-only italics. All prior-single rules/examples in PRODUCT_SPEC and IMPLEMENTATION use `›`. Caption accounting uses conservative UTF-16 visible length after HTML decoding; intro captions fit 1024 units and overflow chunks fit 4096. Only prior-single links overflow into following text posts. Those posts retain publication identities and album-session relations and are not resent when the session is replayed. Unsafe URLs and oversized core text are refused before sending.

## Upgrades, editions and album sequencing

- A generated 192 kbps candidate replaced a 64 kbps candidate through a fake media edit. The publication message ID/URL stayed unchanged; the previous candidate remained in attempt evidence. One correction reply was created, kept through minute 9 and deleted at minute 10. A definite edit failure retried the edit without a new audio send; an uncertain edit stopped for reconciliation.
- A prior single was linked in the later album introduction, its caption gained an Album link and retained `DROP`, and its audio was skipped. New album tracks had LP/EP headers and no reply-to-intro parameter.
- Album preparation withheld the introduction for missing/invalid ready media and for a missing album-specific official cover. A prior single's cover was not substituted. Readiness was rechecked immediately before the introduction.
- The four-track failure fixture sent One, Two, then failed at Three. Its cursor remained at index 2. An unrelated single was held at minute 1, allowed at minute 16, then the reconstructed session resumed at Three and Four. The intro, One and Two were never resent; a review notification was recorded.
- An uncertain introduction held all album audio. Operator success evidence attached the observed intro, and the session resumed without another intro send.
- A track added after completion published independently with an Album link; the frozen original ordering remained unchanged.
- A distinct instrumental linked to its original publication. A candidate with the original content hash reused the original publication instead of producing a second audio post. Verified late video/platform links edited the stored message caption in place.

## Local verification

- `docker compose config --quiet` and `docker compose build`: passed; web, worker and beat images built.
- `docker compose up -d --force-recreate`: all five services started and reported healthy.
- `migrate --noinput`: `publication.0001_initial` applied; `migrate --check`: passed.
- `makemigrations --check --dry-run`: no changes detected. `manage.py check`: no issues.
- `manage.py test -v 1`: 78 tests passed in 19.148 seconds, including 34 publication tests, the existing M0–M3 suite and PostgreSQL concurrency cases. Test audio/artwork lived in local temporary directories and was removed afterward.
- `/health/`: `{"status":"ok","database":"ok"}`.
- Read-only dev-database check: 30 artists, 57 sources, zero enabled artists/sources, zero verified sources, zero source items, zero baseline runs and zero publications. Fixtures were isolated in Django's test database.
- `git diff --check`, source/docs staging review and secret/media scans: clean. `.env` remains ignored; no token, generated media or private data is included in Git.

## Live test-channel gate

`probe_telegram --configuration-status` observed `live_enabled=false`, `test_mode=false`, `bot_token_configured=false`, `isolated_test_target_configured=false`; the live probe was **not run**. A bot token and isolated test-channel ID are absent locally. No token/chat value was printed.

The opt-in probe and real gateway are implemented, but actual sendAudio/editMessageMedia behavior, message ID preservation, player/tag presentation, reply deletion and Telegram limits remain empirical gates. Production `@RapFaDrop` is explicitly blocked; the configured numeric production ID and resolved target username/ID are checked before mutations. Normal tests and worker defaults cannot reach the real gateway. A test with a numeric target resolving to production's username was refused before a mutation.

## Remaining gates and next scope

Operator evidence, not an automated history lookup, resolves uncertain sends; no reliable Bot API lookup strategy is claimed. Guest metadata and newly discovered links must be verified by the caller/operator before being supplied to the renderer/edit service. Production rollout, media retention/cleanup policy, backup/restore, and broad source coverage remain open. M5 may later provide the full admin product, configuration previews and operator flows after owner review; it was not started here.
