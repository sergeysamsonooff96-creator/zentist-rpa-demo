<!-- schema-ref: zentist-r7 -->

# Zentist RPA demo

This project automates **OrangeHRM** and **Sauce Demo** on a shared Python codebase.

During execution, the application:

- processes the input data for the selected portal;
- stores per-item results in SQLite;
- generates a JSON report;
- sends an HTML summary email when email settings are configured;
- keeps the run completed even if email delivery fails, while the report remains available in **reports/**.

## Installation

```bash
git clone https://github.com/sergeysamsonooff96-creator/zentist-rpa-demo.git
cd zentist-rpa-demo

python -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install runtime dependencies and Playwright browser support:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Configuration

The application reads settings from environment variables. For local development, it is convenient to use a `.env` file.

See **.env.example** for a sample configuration.

Example **.env.example**:

```env
APP_ENV=local
DB_PATH=./data/app.db

PORTAL_NAME=orangehrm
# PORTAL_NAME=saucedemo

ORANGEHRM_URL=https://opensource-demo.orangehrmlive.com/web/index.php/auth/login
ORANGEHRM_USERNAME={orangehrm_username}
ORANGEHRM_PASSWORD={orangehrm_password}

SAUCEDEMO_URL=https://www.saucedemo.com
SAUCEDEMO_PASSWORD={saucedemo_password}

REPORT_EMAIL={report_recipient_email}

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME={smtp_username}
SMTP_PASSWORD={smtp_password_or_app_password}
SMTP_USE_TLS=true
SMTP_FROM={smtp_from_email}
```

Main variables:

- **APP_ENV** — environment name, for example **local**, **dev**, or **ci**.
- **PORTAL_NAME** — portal to run: **orangehrm** or **saucedemo**.
- **DB_PATH** — path to the SQLite database file.
- **REPORT_EMAIL** — recipient email address for the final report.
- **ORANGEHRM_URL** — OrangeHRM login URL.
- **ORANGEHRM_USERNAME** — OrangeHRM username.
- **ORANGEHRM_PASSWORD** — OrangeHRM password.
- **SAUCEDEMO_URL** — Sauce Demo base URL.
- **SAUCEDEMO_PASSWORD** — password for Sauce Demo accounts.
- **SMTP_HOST** — SMTP host.
- **SMTP_PORT** — SMTP port.
- **SMTP_USERNAME** — SMTP account username.
- **SMTP_PASSWORD** — SMTP password or app password.
- **SMTP_USE_TLS** — whether to use STARTTLS.
- **SMTP_FROM** — sender email address.

Credentials are kept outside the repository and are not hardcoded in the application code, which matches the task requirements. [file:243]

## Gmail setup

For Gmail, it is recommended to use an app password instead of the main account password.

1. Enable two-factor authentication on the Google account.
2. Create an App Password in Google security settings.
3. Put that value into **SMTP_PASSWORD**.
4. Use the same Gmail address for both **SMTP_USERNAME** and **SMTP_FROM**.
5. Use the following SMTP settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## Running the application

The application runs one portal per execution. The target portal is selected through **PORTAL_NAME**.

```bash
python -m src.app.main
```

During execution, the application:

1. loads configuration;
2. creates a SQLite connection;
3. initializes the database schema when needed;
4. selects the required runner by portal name;
5. processes all items from the input set;
6. stores per-item outcomes in the **item_results** table;
7. generates a JSON report;
8. sends an HTML email if SMTP is configured.

## Supported portals

### OrangeHRM

The **OrangeHRM** scenario:

- logs into the portal;
- processes the input employee list;
- checks whether an employee already exists;
- creates the employee if missing;
- updates **Job Title** and **Employment Status**;
- uploads a salary attachment when it is not already present.

The implementation is designed to be idempotent for repeated same-day runs, so reruns do not create duplicate stored results and keep the target employee state aligned with the intended values. [file:243]

### Sauce Demo

The **Sauce Demo** scenario:

- processes the required test accounts;
- logs into the portal;
- adds three items to the cart;
- completes the checkout flow;
- stores the result for each account;
- continues the batch even if one of the accounts fails.

Each account is processed independently, and failures are recorded with a reason instead of aborting the full batch. [file:243]

## Reporting

After each run, the application creates a JSON file in the **reports/** directory.

The report contains:

- **portal** — portal name;
- **run_id** — run identifier;
- **generated_at** — report generation timestamp;
- **statistics** — **total / success / failed**;
- **items** — processed items with their result;
- **logs** — structured event log for the run.

The JSON report is saved regardless of whether email delivery is enabled.

## Email report

After generating the JSON report, the application can send an HTML email to the address specified in **REPORT_EMAIL**.

The email contains:

- run information;
- summary statistics;
- a **Successful transactions** section;
- a **Failed transactions** section;
- the JSON report as an attachment.

If email sending is disabled, not configured, or fails, this does not affect result persistence. The main report always remains available in **reports/**.

## Result storage

Results are stored in SQLite in the **item_results** table.

For the same item within the same day, the existing row is updated instead of inserting a duplicate. This makes reruns safe and keeps the stored results consistent, which directly addresses the same-day rerun requirement from the task. [file:243]

## Project structure

```text
src/
  app/
    main.py
    config.py
    logging.py

    connectors/
      email_connector.py
      report_connector.py

    core/
      base_runner.py
      browser.py
      retry.py

    db/
      sqlite.py
      repo.py

    portals/
      registry.py

      orangehrm/
        data.py
        runner.py

      saucedemo/
        data.py
        runner.py

tests/
  conftest.py
  test_config.py
  test_email_connector.py
  test_repo.py
  test_report_connector.py
```

Main components:

- **main.py** — application entry point.
- **config.py** — runtime configuration loading.
- **logging.py** — logging setup.
- **connectors/** — shared components for reporting and email.
- **core/** — shared execution, browser, and retry logic.
- **db/** — persistence layer.
- **portals/** — portal-specific logic.
- **registry.py** — mapping between portal names and runner classes.

The base portal runner class is **BasePortalRunnerZX**, as required by the task. [file:243]

## Adding a new portal

1. Create a new runner that inherits from **BasePortalRunnerZX**.
2. Implement the portal-specific processing steps.
3. Reuse the shared connectors for persistence, reporting, and email delivery.
4. Register the new runner in **src/app/portals/registry.py**.
5. Add any required environment variables to **.env.example** and local **.env**.
6. Add tests for the new portal-specific behavior and any new shared logic.

This keeps the shared layer unchanged while isolating portal-specific behavior in a separate runner implementation, which is the intended extension model for adding a third portal. [file:243]

## Logging and resilience

During a run, the application writes application-level and item-level events. Each processed item is stored with a **success** or **failed** outcome, and failures include a readable reason.

A partial failure does not stop the whole batch. Even if a specific item or the email step fails, the run still completes and produces a final report. Retry and timeout handling are implemented in the reusable shared layer rather than duplicated inside each portal runner. [file:243]

## Tests

Run tests with:

```bash
python -m pytest -q
```

Current test coverage includes:

- configuration loading;
- SQLite result persistence;
- upsert logic for repeated item results;
- JSON report generation;
- email sending through mocked SMTP.

## CI

GitHub Actions is configured for this repository and runs on pushes and pull requests to **main**.

The CI workflow:

- sets up Python;
- installs runtime and development dependencies;
- installs Playwright browser support;
- runs **ruff**;
- runs the **pytest** suite.

This satisfies the task requirement for a PR pipeline that installs dependencies, runs linting, and executes tests. [file:243]

## Development workflow

Typical local development flow:

1. create and activate a virtual environment;
2. install runtime and development dependencies;
3. configure a local `.env`;
4. run the selected portal with `python -m src.app.main`;
5. run `python -m pytest -q`;
6. run `ruff check .`.

## Development tools

Development dependencies are stored in **requirements-dev.txt**.

Current development tools:

- **pytest**
- **pytest-asyncio**
- **ruff**