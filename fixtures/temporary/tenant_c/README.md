# Small Tenant C sample

All seven submission rows and the client are synthetic. `operations_c.csv` uses
the same 13-column contract as the portal. Upload it manually; the existing seed
and fixture-generation scripts cover Tenants A and B only.

| Submission cohort | Submissions | With an interview | Conversion |
| --- | ---: | ---: | ---: |
| May 2026 | 3 | 2 | 66.67% |
| June 2026 | 4 | 1 | 25% |

There is one May start. June includes a document queue, a client-review queue,
and an explicit rejection reason. These records illustrate possible contributors;
they do not prove a general causal explanation.

Generate a token with the existing custom tenant option:

```powershell
& "D:\DockerDesktop\resources\bin\docker.exe" compose exec api python scripts/demo_token.py --tenant-id 33333333-3333-4333-8333-333333333333 --role admin
```

Connect using that token before uploading. Creating a CSV does not register or
ingest a tenant; the authenticated upload attaches its tenant identity.

To demonstrate freshness, add an interview for `SUB-C-J02` using a new outcome ID
such as `INT-C-NEW-01`, occurred at `2026-06-25T10:00:00Z`. Ask again: June should
become 2/4 = 50%. The portal's prefilled outcome values refer to Tenant A and must
be replaced for this sample. A separate Tenant C policy has not been included.
