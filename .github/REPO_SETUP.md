# GitHub repo & profile setup (manual)

Run these once after merging to `main`. The cloud agent token cannot edit repo settings or user pins — **you** run these locally with `gh` auth as @Iron-Mark.

## 1. Repository About & topics

```bash
gh repo edit Iron-Mark/Iron-Mark \
  --description "Product designer & full-stack developer (@Iron-Mark) — proof-backed AI, mobile & Web3 portfolio index. Philippines · llms.txt · STACK.md" \
  --add-topic product-design \
  --add-topic full-stack \
  --add-topic react \
  --add-topic nextjs \
  --add-topic flutter \
  --add-topic web3 \
  --add-topic portfolio \
  --add-topic ui-ux \
  --add-topic philippines \
  --add-topic llms-txt \
  --add-topic aeo
```

Remove stale topics if needed: `config`, `github-config`, `readme-template` (Settings → Topics).

## 2. Social preview image

**Settings → General → Social preview → Upload**

Use `assets/brand/banner.gif` (or a static 1280×640 PNG export) so link shares look on-brand.

## 3. Pin 6 repositories (profile, not this repo)

**github.com/Iron-Mark → Customize pins**

Suggested alignment with Featured Work + lab:

1. `Iron-Mark/Iron-Mark` (this index)
2. HireProof repo (or primary HireProof org repo)
3. `Iron-Mark/qwen-ui-lab`
4. `UMakLumen/ResQLinkWeb` or team ResQLink repo
5. Stellaroid / PalengkePay team repo (`polsalarm/PalengkePay-Pro`) or `Iron-Mark/Hackathon-LexInsights`
6. `ACSADians/kudlit-app` or BaybayInscribe-related repo

Pick the six with strongest proof + recent activity.

## 4. GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions**

Then run workflow **Deploy GitHub Pages mirror** once. Live at:

https://iron-mark.github.io/Iron-Mark/

## 5. Profile README visibility

If README does not show on https://github.com/Iron-Mark:

- Repo must be **public**, named exactly `Iron-Mark`
- `README.md` on **default branch** (`main`)
- Click **Share to profile** on the repo page if prompted

## 6. Portfolio mirror (marksiazon.dev)

Copy block from [portfolio-sync/marksiazon-dev-append.md](../portfolio-sync/marksiazon-dev-append.md) into portfolio `llms.txt` and footer. Verify with:

```bash
python3 scripts/check_portfolio_mirror.py
```

## 7. LinkedIn headline sync

Match README one-liner:

> Product Design Engineer & Full-Stack Developer | Proof-backed AI, mobile & Web3 | Philippines & remote
