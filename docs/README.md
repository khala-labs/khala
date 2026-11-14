# Khala — Ecosystem Docs

Astro Starlight site. EN (root) + ko.

## Dev
```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # → dist/
```

## Deploy (GitHub Pages)

- The site deploys to GitHub Pages through `.github/workflows/docs-deploy.yml` on a push to `master` that changes `docs/**`, or by manual dispatch.
- The repository's Pages source must be set to "GitHub Actions".
- The site is served at https://khala-labs.github.io/khala/ (base path `/khala/`).
- Pull requests are gated by the `docs` job in `.github/workflows/ci.yml` (build and link check).
