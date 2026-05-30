#!/bin/bash
# SınavVeri.com deploy — build + rsync (flat static)
# Cloudflare doğrulama marker'ı (e77c...txt) sunucuda korunur; gönderilmez.
set -e
cd "$(dirname "$0")"
python3 build.py
rsync -az --delete \
  --exclude 'build.py' --exclude 'deploy.sh' --exclude 'data/' --exclude 'pipeline/' \
  --exclude '__pycache__/' --exclude '.venv/' --exclude '.git/' --exclude '.gitignore' \
  --exclude 'e77c22b97eb527506d152246be339059.txt' \
  -e "ssh -i $HOME/.ssh/tr_server -o StrictHostKeyChecking=accept-new" \
  ./ root@185.136.205.177:/var/www/sinavveri.com/
ssh -i "$HOME/.ssh/tr_server" root@185.136.205.177 \
  'chown -R www:www /var/www/sinavveri.com; chmod -R 755 /var/www/sinavveri.com'
echo "Deploy tamam → https://sinavveri.com"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://sinavveri.com/
