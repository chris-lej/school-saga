# Web Deployment

School Saga deploys to Vercel as a static Godot Web export. The repository is pinned to **Godot 4.7.1-stable** in `.godot-version`.

## Export Contract

- Godot export preset: `Web`
- Export command: `bash scripts/export-web.sh`
- Output directory: `build/web`
- Entry HTML: `build/web/index.html`
- Vercel build command: `bash scripts/export-web.sh`
- Vercel output directory: `build/web`

The generated `build/` directory must be regenerated from a clean checkout rather than treated as source.

## Local Export

Install Godot **4.7.1-stable** with matching export templates, then run:

```bash
bash scripts/export-web.sh --no-install
```

Set `GODOT_BIN=/path/to/godot` when the editor executable is not named `godot` or `godot4` on `PATH`.

On Linux CI or Vercel, `bash scripts/export-web.sh` can download the pinned editor and export templates when Godot is unavailable locally.

## Vercel Behavior

The checked-in `vercel.json` allows a Vercel Git integration to build pull requests as Preview deployments and merges to `main` as Production deployments. It does not add a competing deployment workflow, serverless functions, or a Node application.

The current Web export is single-threaded and does not use web extensions. Repository-level COOP/COEP isolation headers are therefore not enabled. Revisit that decision before enabling Godot Web threads or web GDExtensions.

Direct navigation rewrites to `index.html`. Static generated asset requests retain their filenames and resolve from `build/web`.

## Environment Variables

The current static deployment requires no Vercel secrets or project-specific environment variables.

Do not place private credentials in the Godot client export. Browser-visible runtime configuration must be treated as public.

## Validation

The shared required gate is:

```bash
bash scripts/validate-pr.sh
```

It exports the Web build, verifies the generated HTML, JavaScript, WASM, and PCK artifacts, checks locally referenced HTML assets, and confirms that `vercel.json` matches the repository deployment contract.

A focused local export can be run with:

```bash
bash scripts/export-web.sh --no-install
python scripts/validate-web-export.py
```

GitHub Actions runs the same repository-owned validation gate on pull requests and pushes to `main`. Vercel remains responsible for creating Preview and Production deployments from the checked-in command.

## Troubleshooting

- `Godot was not found on PATH`: install Godot 4.7.1-stable or set `GODOT_BIN`.
- Godot version mismatch: use the version pinned in `.godot-version`.
- `No export template found`: install matching export templates, or allow the Linux export script to download them.
- `export_presets.cfg is missing`: restore the checked-in Web export preset.
- `missing expected generated asset types`: the export failed or wrote to the wrong path; keep the entry path at `build/web/index.html`.
- Missing referenced assets: inspect the generated `index.html` and ensure every local asset is present beneath `build/web`.

## Remaining Manual Vercel Actions

The repository assumes the Vercel project is already imported and connected to GitHub. Account, team, billing, DNS, custom-domain ownership, and dashboard-only settings remain manual actions outside the repository.
