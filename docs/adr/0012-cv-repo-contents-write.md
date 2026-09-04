# Private `cv` vault via GitHub Contents API

Resume backups go to a dedicated GitHub repo named `cv` on the Owner account, written with the Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`). If that repo is missing we create it (private, `auto_init`). We still do **not** clone or store git objects in Mongo; the site of record for Resume fields remains Mongo. The public site never proxies this vault.
