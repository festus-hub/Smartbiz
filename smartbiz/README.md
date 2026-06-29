# SmartBiz

SmartBiz is a Django-based business management system for small businesses. It includes:

- User registration and login
- Role-based access control
- Dashboard analytics
- Product management
- Customer management
- Sales tracking
- Payment tracking with M-Pesa support
- Expense tracking
- Reports and CSV export

## How the website works

1. A business owner registers an account.
2. The user signs in and lands on the dashboard.
3. Staff use role-based pages:
   - Employees can view dashboard, customers, products, and stock movement.
   - Cashiers can manage sales and payments.
   - Managers can add expenses, manage products, and view reports.
   - Business owners inherit lower-level access through the role hierarchy.
4. Sales, payments, and expenses feed the dashboard and reports.
5. The API under `/api/` supports authenticated frontend or third-party integrations.

## Local setup

### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

PowerShell example:

```powershell
$env:DJANGO_SECRET_KEY="replace-with-a-secure-secret"
$env:DJANGO_DEBUG="true"
$env:DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost"
$env:DJANGO_CSRF_TRUSTED_ORIGINS="http://127.0.0.1:8000,http://localhost:8000"
$env:DJANGO_SECURE_SSL_REDIRECT="false"
$env:DJANGO_SESSION_COOKIE_SECURE="false"
$env:DJANGO_CSRF_COOKIE_SECURE="false"
$env:EMAIL_HOST_USER="your-email@example.com"
$env:EMAIL_HOST_PASSWORD="your-email-app-password"
$env:DEFAULT_FROM_EMAIL="your-email@example.com"
$env:CONTACT_RECIPIENT_EMAIL="your-email@example.com"
$env:MPESA_ENV="sandbox"
$env:MPESA_CONSUMER_KEY="your-mpesa-consumer-key"
$env:MPESA_CONSUMER_SECRET="your-mpesa-consumer-secret"
$env:MPESA_SHORTCODE="174379"
$env:MPESA_PASSKEY="your-mpesa-passkey"
$env:MPESA_CALLBACK_URL="https://your-public-domain/api/payments/mpesa/callback/"
```

Notes:

- `.env.example` shows a safe starter set of variables for both local and production use.
- Leave the M-Pesa values blank if you are not testing M-Pesa yet.
- `MPESA_CALLBACK_URL` must be a public HTTPS URL in real callback testing.
- Use an app password for Gmail SMTP, not your normal account password.
- If the email vars are not set in local development, Django falls back to the console email backend and prints password-reset emails in the terminal.
- For local development, keep `DJANGO_DEBUG=true` and the secure cookie / SSL redirect values set to `false`.

### 4. Apply database migrations

```powershell
python manage.py migrate
```

### 5. Create an admin user

```powershell
python manage.py createsuperuser
```

### 6. Run the website

```powershell
python manage.py runserver
```

Open:

- Main site: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
- API docs: `http://127.0.0.1:8000/api/docs/`

The warning about the development server is expected here. `runserver` is correct for local development.

## Client handoff guide

If the client is the business admin:

1. Open the website URL.
2. Register a new account or sign in with the provided account.
3. Add products first.
4. Add customers as needed.
5. Record sales.
6. Record payments.
7. Add expenses.
8. Use the dashboard and reports pages to monitor performance.

If the client is deploying the website on a server:

1. Install Python 3.13 or a compatible version.
2. Copy the project to the server.
3. Create a virtual environment.
4. Install `requirements.txt`.
5. Set the environment variables.
6. Run `python manage.py migrate`.
7. Run `python manage.py collectstatic`.
8. Run `python manage.py createsuperuser`.
9. Set `DJANGO_DEBUG=false`.
10. Set `DJANGO_ALLOWED_HOSTS` to the real domain, for example `smartbiz.example.com,www.smartbiz.example.com`.
11. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the full HTTPS origins, for example `https://smartbiz.example.com,https://www.smartbiz.example.com`.
12. Use a real `DJANGO_SECRET_KEY`.
13. Keep `DJANGO_SECURE_SSL_REDIRECT=true`, `DJANGO_SESSION_COOKIE_SECURE=true`, and `DJANGO_CSRF_COOKIE_SECURE=true`.
14. Serve Django with a production server and reverse proxy.

## Production example

Typical production stack:

- Django app served by `gunicorn`
- `nginx` as the reverse proxy
- HTTPS enabled at the proxy

Example `gunicorn` command:

```powershell
gunicorn smartbiz.wsgi:application --bind 0.0.0.0:8000
```

Typical production checklist:

1. Set `DJANGO_DEBUG=false`.
2. Set a strong `DJANGO_SECRET_KEY`.
3. Set `DJANGO_ALLOWED_HOSTS`.
4. Set `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Run `python manage.py migrate`.
6. Run `python manage.py collectstatic`.
7. Put Django behind `nginx` or another reverse proxy.
8. Point the domain to the server and enable HTTPS.

## Deploy on Vercel

This repository is now prepared for Vercel with:

- [vercel.json](C:/Users/user/OneDrive/Desktop/smartbiz/vercel.json) for Vercel routing and build settings
- [api/index.py](C:/Users/user/OneDrive/Desktop/smartbiz/api/index.py) as the Vercel Python WSGI entrypoint
- [requirements.txt](C:/Users/user/OneDrive/Desktop/smartbiz/requirements.txt) at the repository root so Vercel installs the Django dependencies
- PostgreSQL support via `DATABASE_URL`
- WhiteNoise static file serving for production

### Vercel steps

1. Push this project to GitHub.
2. Sign in to Vercel and import the GitHub repository.
3. Keep the project root as the repository root.
4. Add these environment variables in Vercel:
   - `DJANGO_DEBUG=false`
   - `DJANGO_SECRET_KEY=<a strong secret>`
   - `DATABASE_URL=<your production PostgreSQL connection string>`
   - `DJANGO_SECURE_SSL_REDIRECT=true`
   - `DJANGO_SESSION_COOKIE_SECURE=true`
   - `DJANGO_CSRF_COOKIE_SECURE=true`
   - Gmail SMTP and M-Pesa variables if you use those features.
5. Deploy the project.
6. Run migrations against the production database after deployment:

```bash
cd smartbiz
python manage.py migrate --noinput
python manage.py createsuperuser
```

### Important notes for Vercel

- Vercel's filesystem is ephemeral, so production must use PostgreSQL or another external database through `DATABASE_URL`.
- Vercel provides deployment URLs through `VERCEL_URL`, `VERCEL_BRANCH_URL`, and `VERCEL_PROJECT_PRODUCTION_URL`; the Django settings automatically allow those hostnames and CSRF origins.
- When you add a custom domain, add it to `DJANGO_ALLOWED_HOSTS` and add the full HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Vercel does not provide a built-in managed PostgreSQL database by default. Use Vercel Postgres, Neon, Supabase, Railway, or another hosted PostgreSQL provider.
- `MPESA_CALLBACK_URL` is optional on Vercel. If it is blank, the app builds a callback URL from Vercel's deployment hostname.

## Running tests

```powershell
python manage.py test
```
