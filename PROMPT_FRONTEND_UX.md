# Prompt Perbaikan Frontend dan UX

Gunakan prompt ini di OpenCode untuk memperbaiki UX aplikasi pada folder ini.

```text
Kamu sedang bekerja di repository monitoring-ics-apps.

Tujuan:
Perbaiki frontend/UX agar terasa lebih enak dipakai, lebih jelas, dan lebih cepat dipahami operator.
Fokus utama adalah TUI (interactive terminal UI), bukan sekadar ubah warna.

Konteks file penting:
- src/app/tui/interactive.py
- src/app/tui/common.py
- src/app/tui/flows/dashboard.py
- src/app/tui/flows/customer.py
- src/app/tui/flows/settings.py
- src/core/runtime/ui.py

Yang harus kamu kerjakan:
1. Audit UX saat ini dan identifikasi pain points (navigasi, istilah menu, hierarchy informasi, beban kognitif, feedback setelah aksi).
2. Refactor alur menu agar:
   - struktur menu lebih konsisten,
   - istilah lebih singkat dan jelas,
   - aksi utama lebih menonjol,
   - alur kembali (back/exit) lebih intuitif.
3. Tingkatkan dashboard agar lebih informatif dengan prioritas visual yang jelas (apa yang penting duluan terlihat).
4. Rapikan copywriting UI (Bahasa Indonesia yang ringkas, konsisten, dan operasional).
5. Tambahkan UX detail yang berdampak tinggi:
   - hint keyboard singkat,
   - loading/progress state yang jelas,
   - pesan error yang actionable,
   - konfirmasi setelah aksi penting.
6. Pertahankan kompatibilitas behavior lama (jangan rusak command CLI yang sudah ada).

Constraint:
- Ikuti pola kode yang sudah ada.
- Hindari perubahan arsitektur besar yang tidak perlu.
- Jangan menurunkan keterbacaan output terminal.
- Prioritaskan perbaikan yang terasa langsung oleh user.

Output yang saya minta:
- Implementasi langsung di kode.
- Ringkasan before vs after (singkat).
- Daftar file yang diubah + alasan tiap perubahan.
- Jalankan verifikasi berikut dan tampilkan hasilnya:
  - uv run --with pytest pytest tests/unit/test_interactive_v2.py
  - uv run --with pytest pytest tests/integration/test_cli_entrypoints.py

Mulai dari audit cepat, lalu eksekusi perbaikan paling berdampak dulu.
```
