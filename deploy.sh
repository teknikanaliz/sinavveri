#!/bin/bash
# ⚠️ KULLANIMDAN KALDIRILDI (2026-05-31) — bu site artık Capistrano kullanıyor.
#
# Eski davranış (flat rsync → /var/www/sinavveri.com/) ARTIK YASAK ve
# deploy-guard hook tarafından komut seviyesinde bloke edilir.
#
# DOĞRU DEPLOY:  git push origin main   → GitHub Actions (.github/workflows/deploy.yml)
#                 atomic release + health-check + otomatik rollback yapar.
#
# Sadece lokalde içerik üretmek istersen:  python3 -m pipeline.run --build-only
echo "⚠️  deploy.sh kullanımdan kaldırıldı. Deploy için: git push origin main (Capistrano)."
echo "    Lokal build için:  python3 -m pipeline.run --build-only"
exit 1
