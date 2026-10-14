# RoadRent - Online Car Rental System (multi-page)

MCA (Second Year) project: **Flask + Jinja2 templates + SQLite + REST API + JavaScript**.

## Pages (one page per purpose)
| URL | Page | Purpose |
|---|---|---|
| `/` | home.html | Quick search, stats, how it works, popular cars |
| `/cars` | cars.html | Filter by dates, type, seats, price; live availability |
| `/book?car=ID` | book.html | Booking form with live price and availability check |
| `/confirmation?ref=RR1001` | confirmation.html | Printable booking ticket |
| `/my-bookings` | mine.html | Find and cancel bookings by phone number |
| `/about` | about.html | About, rental policies, contact |
| `/login` | login.html | Log in (customers and admin use the same page) |
| `/register` | register.html | Create a customer account |
| `/admin` | admin.html | All bookings, stats, cancel any booking |
| `/admin/fleet` | fleet.html | Add cars and view the fleet |

All pages extend `base.html` (shared navigation and footer) using Jinja2 template inheritance. Admin pages redirect to the login page unless the admin session is active.

## Accounts and security
- Passwords are stored as salted hashes (`werkzeug.security`), never as plain text.
- Login uses a Flask session cookie. Wrong email and wrong password give the same message.
- Roles: `customer` and `admin`. Booking, My bookings and Confirmation need a login; `/admin` pages and admin APIs need the admin role.
- Customers can only see and cancel their own bookings. Visiting a protected page sends you to `/login?next=...` and back after login.
- Demo admin account: `admin@roadrent.com` / `admin123` (change with `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables, and set `SECRET_KEY`).

## Key logic
- **Double-booking prevention:** two bookings clash when `start1 <= end2 AND end1 >= start2`.
- **Pricing:** 5% off for 3-6 days, 10% off for 7+ days, calculated on the server.
- **Validation:** name, Indian mobile number, no past dates, 1-30 days.
- **Security:** admin login uses a Flask session cookie; admin APIs return 401 without it; all output is HTML-escaped in JavaScript.

## Run
Keep all files in ONE folder.
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. The database file is `roadrent_v2.db` (created on first run).

## REST API
`GET /api/cars`, `GET /api/cars/<id>`, `POST /api/bookings`, `GET /api/bookings?phone=`, `GET /api/bookings/<ref>`, `POST /api/bookings/<id>/cancel`, `POST /api/register`, `POST /api/login`, `GET /api/me`, `GET /api/admin/bookings`, `POST /api/admin/cars`, `GET /api/stats`

## Database
- `users(id, name, email UNIQUE, phone, password_hash, role)`
- `cars(id, name, type, seats, transmission, fuel, price_per_day)`
- `bookings(id, car_id -> cars.id, user_id -> users.id, customer, phone, start_date, end_date, days, discount, total, status, created_at)`

## Future scope
Email verification and OTP login, password reset, login rate limiting, online payments, licence upload, car photos, email/SMS alerts, PostgreSQL deployment.

## Deployment
**Static demo on GitHub Pages** (sample data, no server): the `docs/` folder holds a browser-only copy of the site, and `.github/workflows/pages.yml` publishes it. In the repo go to Settings > Pages > Source and choose **GitHub Actions**. Do not choose "Deploy from a branch", which runs Jekyll and fails.

**Full working app on Render** (Flask + database): create a new Web Service from this repo (Render reads `render.yaml`), or set Build command `pip install -r requirements.txt` and Start command `gunicorn app:app`. Set the `SECRET_KEY` and `ADMIN_PASSWORD` environment variables. Free plans may reset the SQLite file on restart.
