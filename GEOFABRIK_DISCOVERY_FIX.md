# Geofabrik discovery fix

The previous patch attempted to parse `https://download.geofabrik.de/asia/`
with redirects disabled. That URL can itself redirect, so the parser received
the redirect response body instead of the directory contents.

This patch uses the Philippines download page directly:

```text
https://download.geofabrik.de/asia/philippines.html
```

The page contains the dated Philippines `.osm.pbf` links. Sigma Siphon selects
the highest YYMMDD filename and downloads that exact dated file.

The large PBF download still uses explicit, loop-detecting redirects restricted
to HTTPS Geofabrik hosts.
