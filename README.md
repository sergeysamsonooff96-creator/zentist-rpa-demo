<!-- schema-ref: zentist-r7 -->

# Zentist RPA Demo

This project automates two portals on a shared Python codebase:

- OrangeHRM — employee processing and data update flow.
- Sauce Demo — end-to-end purchase flow for all required accounts.

The solution is built around reusable shared layers for configuration, retries, persistence, reporting, and email delivery. It stores per-item outcomes in SQLite, generates a structured JSON report after each run, and can send an HTML summary email with the report attached. [file:243]

## Implemented portals

### OrangeHRM

The OrangeHRM runner:

- logs in once with configured credentials;
- processes a batch of employees from input data;
- checks whether an employee already exists;
- creates the employee if missing;
- updates Job Title and Employment Status to target values from input;
- uploads a salary attachment if it is not already present.

The run is idempotent at the result-storage level for the same day: repeated processing updates the stored outcome for the same item instead of inserting duplicates. [file:243]

### Sauce Demo

The Sauce Demo runner:

- processes all required accounts;
- logs in with `secret_sauce`;
- adds three products to the cart;
- completes checkout;
- captures order details for successful accounts;
- records failures without aborting the rest of the batch.

This matches the required mixed-outcome behavior where some accounts may fail while the job still produces a coherent final report. [file:243]

## Features

- Shared runner architecture with portal-specific implementations.
- Reusable retry and browser layers.
- SQLite persistence for per-item outcomes.
- JSON report generation after each run.
- HTML email report with JSON attachment.
- Structured logs and partial-failure tolerance.
- Same-day upsert behavior for item results.

## Installation

```bash
git clone <repository_url>
cd <repository_folder>

python -m venv .venv
```

Activate the virtual environment:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install
```

## Configuration

Application settings are loaded from environment variables. A local `.env` file can be used for convenience.

See `.env.example` for a sample configuration.

### Required environment variables

- `APP_ENV` — environment name, for example `local`, `dev`, or `ci`.
- `PORTAL_NAME` — portal to run: `orangehrm` or `saucedemo`.
- `DB_PATH` — path to the SQLite database file.
- `REPORT_EMAIL` — recipient email for the final report.
- `ORANGEHRM_URL` — OrangeHRM base URL.
- `ORANGEHRM_USERNAME` — OrangeHRM username.
- `ORANGEHRM_PASSWORD` — OrangeHRM password.
- `SAUCEDEMO_URL` — Sauce Demo base URL.
- `SAUCEDEMO_PASSWORD` — password for Sauce Demo accounts.
- `SMTP_HOST` — SMTP host.
- `SMTP_PORT` — SMTP port.
- `SMTP_USERNAME` — SMTP username.
- `SMTP_PASSWORD` — SMTP password or app password.
- `SMTP_USE_TLS` — whether to use STARTTLS.
- `SMTP_FROM` — sender email address.

## Gmail setup

For Gmail, use an app password instead of the main account password.

1. Enable two-factor authentication on the Google account.
2. Create an App Password in Google security settings.
3. Put that value into `SMTP_PASSWORD`.
4. Use the same Gmail address for both `SMTP_USERNAME` and `SMTP_FROM`.
5. Typical Gmail SMTP settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## Running the project

One run processes one portal. Select the portal with `PORTAL_NAME`.

```bash
python -m src.app.main
```

During a run, the application:

1. loads configuration;
2. initializes the SQLite schema if needed;
3. selects the correct runner from the portal registry;
4. processes all items for that portal;
5. stores per-item outcomes in `item_results`;
6. generates a JSON report in `reports/`;
7. sends an HTML email report when SMTP is configured.

## Reports

After each run, a JSON report is created in the `reports/` directory.

The report contains:

- `portal` — portal name;
- `run_id` — unique run identifier;
- `generated_at` — report generation timestamp;
- `statistics` — total / success / failed counters;
- `items` — processed items with status and reason;
- `logs` — structured run-level and item-level events.

The JSON report is saved even if email delivery is unavailable or fails. This ensures the run still produces a coherent output for inspection. [file:243]

## Email report

When SMTP is configured, the application sends an HTML email summary to `REPORT_EMAIL`.

The email includes:

- run metadata;
- total / success / failed statistics;
- successful transactions table;
- failed transactions table;
- the JSON report as an attachment.

A mail delivery problem does not remove the saved JSON report and does not invalidate the run result.

## Persistence and idempotency

Results are stored in SQLite in the `item_results` table.

The repository uses a same-day uniqueness rule on:

- `portal`
- `run_date`
- `item_key`

This means a same-day rerun updates the stored result for the same item instead of creating duplicates, which supports the requirement that reruns should not corrupt reporting or duplicate outcomes. [file:243]

## Project structure

```text
src/
  app/
    __init__.py
    main.py
    config.py
    logging.py

    connectors/
      __init__.py
      email_connector.py
      report_connector.py

    core/
      __init__.py
      base_runner.py
      browser.py
      retry.py

    db/
      __init__.py
      sqlite.py
      repo.py

    portals/
      __init__.py
      registry.py

      orangehrm/
        __init__.py
        data.py
        runner.py

      saucedemo/
        __init__.py
        data.py
        runner.py
```

### Main components

- `main.py` — application entry point.
- `config.py` — runtime configuration loading.
- `connectors/` — shared connectors for reporting and email.
- `core/` — reusable execution, browser, and retry logic.
- `db/` — SQLite schema and repository layer.
- `portals/` — portal-specific runners and input data.
- `registry.py` — maps portal names to runner classes.

The shared base runner is named `BasePortalRunnerZX` as required by the task. [file:243]

## Adding a new portal

To add a third portal:

1. create a new runner that inherits from `BasePortalRunnerZX`;
2. implement `portal_name`, `iter_items()`, and `process_item(...)`;
3. keep portal-specific selectors and workflow inside that runner;
4. reuse the shared repository, reporting, retry, and email layers;
5. register the new runner in `src/app/portals/registry.py`;
6. extend configuration if the portal needs additional credentials or URLs.

This keeps shared logic unchanged while isolating portal-specific behavior in a dedicated implementation, which is one of the explicit requirements of the task. [file:243]

## Logging and failure handling

The application emits structured operational events at both run and item level.

Behavioral guarantees:

- one failed item does not abort the rest of the batch;
- each processed item gets an outcome;
- failures include a readable reason;
- a report is still produced after partial failure;
- email delivery is handled as a separate step.

This supports the requirement that a human should be able to understand what happened in the run without digging through raw stack traces. [file:243]

## Tests

Run tests with:

```bash
python -m pytest -q
```

Current tests cover:

- configuration loading;
- SQLite result persistence;
- same-day upsert behavior for item outcomes;
- JSON report generation;
- email sending through mocked SMTP.

## Notes

- Some target values in OrangeHRM may not exist in the live dropdown at runtime. In that case, the run records a failure reason for the affected employee and continues.
- Sauce Demo intentionally includes accounts with unstable or failing behavior. These failures are expected and are captured as per-item outcomes rather than crashing the batch. [file:243]