# Frontend Implementation Guide (Current)

Dokumen ini adalah source of truth implementasi frontend yang aktif saat ini.

## Stack yang dipakai

- React 18 + TypeScript
- Vite (tetap dipertahankan)
- Client-side navigation manual via `window.history` di `web/src/app-shell.tsx`
- Styling berbasis CSS files (`web/src/styles/**`), bukan Tailwind
- Testing dengan Vitest + Testing Library

## Struktur frontend aktif

```text
web/
  src/
    app/
      page.tsx
      checks/
        single/page.tsx
        all/page.tsx
        arbel/page.tsx
      customers/page.tsx
      profiles/page.tsx
      history/page.tsx
    app-shell.tsx
    api/
      client.ts
      checks.ts
      customers.ts
      profiles.ts
      history.ts
      sessions.ts
    features/
      arbel/menu.ts
      checks/normalize-execute-response.ts
      customers/profile-status.ts
    components/
      common/
      ui/
    styles/
      ops-theme.css
      pages/
        arbel.css
        customers.css
```

## API contract frontend

Base path frontend ke backend: `/api/v1` (diproxy oleh Vite saat development).

Request utama execute checks:

```json
{
  "customer_ids": ["uuid"],
  "mode": "single|all|arbel",
  "check_name": "guardduty",
  "account_ids": ["uuid"],
  "send_slack": false,
  "check_params": {"window_hours": 12}
}
```

Compatibility:

- Frontend normalize response execute untuk dua shape:
  - `consolidated_outputs` (baru)
  - `consolidated_output` (legacy)

## Hardening yang sudah diterapkan

- Runtime guard untuk payload yang tidak konsisten pada halaman `Customers` dan `Arbel`.
- Loading/error state lebih konsisten dengan retry action di flow kritikal.
- CSS mulai dipecah ke `web/src/styles/pages/*` untuk mengurangi coupling `ops-theme.css`.
- Quality gates frontend ditambahkan:
  - `npm --prefix web run typecheck`
  - `npm --prefix web run lint`
  - `npm --prefix web run format:check`
  - `npm --prefix web run test`
  - `npm --prefix web run build`

## Menjalankan lokal

```bash
npm ci --prefix web
npm --prefix web run dev
```

Default dev URL: `http://localhost:4173`.

## Verifikasi frontend sebelum merge

```bash
bash scripts/ci/web-quality.sh
npm --prefix web run format:check
```

Jika salah satu command gagal, perbaiki sebelum merge agar CI Web tetap hijau.
