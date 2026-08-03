// Sırlar (VAPID/ADMIN_SECRET) burada YOK — server.js `require('dotenv').config()` ile
// aynı dizindeki `.env`'i okur (gitignore'lu, sunucuya elle/SSH ile konur, git'e girmez).
module.exports = {
  apps: [
    {
      name: 'sinavveri-push',
      script: 'server.js',
      cwd: '/var/www/sinavveri.com/current/push-server',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PORT: 3032,
        DB_PATH: '/var/www/sinavveri.com/shared/push-server/subscriptions.db',
      },
    },
  ],
};
