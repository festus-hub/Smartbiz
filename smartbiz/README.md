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
$env:EMAIL_HOST_USER="your-email@example.com"
$env:EMAIL_HOST_PASSWORD="your-email-app-password"
$env:MPESA_ENV="sandbox"
$env:MPESA_CONSUMER_KEY="your-mpesa-consumer-key"
$env:MPESA_CONSUMER_SECRET="your-mpesa-consumer-secret"
$env:MPESA_SHORTCODE="174379"
$env:MPESA_PASSKEY="your-mpesa-passkey"
$env:MPESA_CALLBACK_URL="https://your-public-domain/api/payments/mpesa/callback/"
```

Notes:

- Leave the M-Pesa values blank if you are not testing M-Pesa yet.
- `MPESA_CALLBACK_URL` must be a public HTTPS URL in real callback testing.
- Use an app password for Gmail SMTP, not your normal account password.

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
7. Run `python manage.py createsuperuser`.
8. Set `DJANGO_DEBUG=false`.
9. Set `DJANGO_ALLOWED_HOSTS` to the real domain.
10. Serve Django with a production server and reverse proxy.

## Running tests

```powershell
python manage.py test
```
