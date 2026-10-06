# Automatic fresh-release acceleration

Work started 2026-10-06 on the server. Owner authorized rapid automatic fresh
publication and broader acquisition coverage; RapRelease is a benchmark, not an
audio source. Historical Popular collection remains paused.

## Implementation awaiting exact server verification

Remove periodic-only handoff waits: validated unseen discovery and eligible
review approval enqueue media after commit; fully prepared single/album enqueue
publication after commit. Explicit queues preserve credential/worker isolation.
Hints expire, durable records and recovery schedules remain authoritative.
Broker failures cannot mark a successfully committed discovery as failed.
Discovery tick 10 s, media recovery/progress 15 s; publication recovery 30 s.
No caption, tag, baseline, archive selection or publication identity reset.

An independently corroborated collaborator profile is acquisition evidence,
not proof that the monitored artist uploaded it. Its recordings must establish
every official credit explicitly before acceptance.

## Observed provider and capacity evidence

Prior authoritative 83-source successful sweep: 202 metadata requests,
21.767 s summed provider time, maximum individual probe 2.682 s. Server has
9.5 GB free disk and about 512 MiB available memory before checks; no new
permanent service or parallel downloader is required.

One bounded owner-authenticated YouTube probe using yt-dlp 2026.8.19 and the
[maintainer's supported client workaround](https://github.com/yt-dlp/yt-dlp/issues/17389)
(`default,web_embedded`) failed after 35.960 s with “The page needs to be reloaded”.
No complete audio obtained, no anonymous retry or access bypass. The underlying
error now triggers provider-specific 15-minute backoff. Tataloo's official
SoundCloud track remains DRM protected and unacquired; no substitution or send.

Bounded public metadata searches for the 28 missing acquisition identities are
running separately on the server. Native public account response and native
catalog ID must agree, own uploads must match independent official Spotify works;
reposts cannot corroborate an artist's own account. Final counts, exact deployed
SHA, polling observations and preservation results will be recorded after checks.

First-minute publication across all 83 artists is not yet established. Provider
upload availability and upstream detection latency cannot be inferred from a
historical replay or queue interval. No RapRelease audio has been downloaded.
