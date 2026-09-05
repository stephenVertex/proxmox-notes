# Beads issue store

Run `bd prime` for workflow context and `bd ready` for available work.
Issues live in the local embedded Dolt database, excluded from code commits.
`bd dolt push` and `bd dolt pull` sync database history through the git remote
under `refs/dolt/data`, separately from code branches. JSONL exports are
optional viewing/interchange artifacts, not the source of truth or sync wire.

`origin` is the GitHub mirror; `gitlab` is the self-hosted GitLab mirror.
The runtime Dolt remote list is managed with `bd dolt remote`, separately
from `git remote`. Credentials belong in SSH/keychain configuration.
