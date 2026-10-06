# Bache Mardom: missed pre-Spotify discovery

Historical diagnosis. The owner-authorized recording subsequently published as
[message79](https://t.me/RapFaDrop/79); independent discovery was partially rolled
out, with an unresolved RSS correction/check/connectivity blocker. See
[dated follow-up](MULTIPLATFORM_FRESH_DISCOVERY.md). Do not read the initial
no-dispatch observation below as the current Bache Mardom publication state.

Observed on the server **2026-10-06**, following owner report
https://t.me/RapRelease/17716. Running application
`7bf07060c4ddcf7496c8ffe369420505d13242e6`.

The public Telegram embed hides this post's content; the owner identified it as
**Hiphopologist — Bache Mardom**. Do not claim to have read its audio/caption.

Authoritative source19 (`45YMrIBH74j8e2wNlRSSdK`) is enabled/verified. Three latest
scheduled polls at 17:19:21, 17:20:11 and 17:21:01 UTC succeeded, each returning78
catalog releases and creating0 IDs. A further read-only real complete adapter
response returned78 releases, with no matching title, in0.302 seconds,3 requests,
2 pages. No matching SourceItem/FreshDispatch exists. This does not establish
absence across every Spotify region or catalog; it establishes the supported
adapter's observed response.

The registered acquisition profile `hiphopologistsoroush`, native380097545,
returned **Bache Mardom**, native track2413998492, as its latest public upload:
https://soundcloud.com/hiphopologistsoroush/bachemardom.
Only bounded latest-five metadata was read; no audio download/publication/DB writes.
That verified acquisition profile is separate from the ArtistSource discovery row,
which remains disabled/unverified for SoundCloud. No baseline/activation was run.

The root cause is **discovery coverage by platform**: fresh eligibility currently
starts from Spotify discovery. SoundCloud/YouTube/intermediaries are acquisition
fallbacks after that discovery, and do not independently discover a pre-Spotify
upload. Enabling intermediary acquisition for83 artists does not close this gap.
No media retry, approval or Telegram resend can process a nonexistent dispatch.
Adding automatic SoundCloud/YouTube discovery requires explicit implementation,
historical baselining, source/recording identity, deduplication and freshness checks;
do not insert a fake Spotify release or activate this source without those steps.

At17:20:52 UTC,83 enabled verified Spotify sources had no consecutive failures,
maximum latest-success age44.901 seconds; fresh control unpaused, zero uncertain
sends. All five runtime services were up and web healthy. No production mutation,
deployment, caption change, temporary post or download was made in this diagnosis.
