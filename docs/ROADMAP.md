# Community roadmap

Daily Berlin Jobs should remain useful before it becomes ambitious. The public
roadmap favors reliable data, a calm job-search experience, and contributions
that can be reviewed in small pieces.

## Now

- stabilize the `engineering-v2` taxonomy and collect false-positive fixtures;
- make local development work without production credentials;
- document scraper ownership and expected test coverage;
- validate the Next.js admin workflow before retiring the legacy UI.

## Next

- add automated accessibility checks;
- improve scraper health reporting without exposing private configuration;
- add contributor-friendly fixtures for ATS parsers;
- clarify data freshness and source attribution on the public board;
- create and label a small set of `good first issue` tasks.

## Completed

- normalize canonical ATS identifiers and aliases;
- audit duplicate domains, careers URLs, ATS support, source freshness, and
  public URL health without exposing production credentials;
- validate GitHub company suggestions and require explicit maintainer approval
  before idempotent PostgreSQL sync.

## Later

- evaluate additional cities or job families only through a versioned scope
  proposal and measured dataset review;
- support community-operated deployments with any standard PostgreSQL host;
- add database-size and retention health alerts before free-tier limits.

Roadmap items are directions, not promises. Open an issue before starting a
large change so scope and architecture can be agreed first.
