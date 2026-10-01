# Geofabrik redirect fix

Geofabrik changed `*-latest.osm.pbf` downloads to HTTP redirects.

Sigma Siphon 0.1.7 no longer downloads the `philippines-latest.osm.pbf` alias.

Instead it:

1. reads the Geofabrik Asia directory index;
2. identifies the newest dated file, such as
   `philippines-260929.osm.pbf`;
3. downloads that dated file directly;
4. verifies the matching `.md5` file when available;
5. records the exact Geofabrik source version in cache metadata.

Redirects for the dated file are followed manually with loop detection and are
restricted to HTTPS Geofabrik hosts.

This avoids the redirect loop observed with the `latest` alias while preserving
the refresh-age prompt and local Osmium extraction architecture.
