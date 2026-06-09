from src.app.config import get_settings


def test_get_settings_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DB_PATH", "./data/test.db")
    monkeypatch.setenv("PORTAL_NAME", "orangehrm")
    monkeypatch.setenv("REPORT_EMAIL", "report@example.com")
    monkeypatch.setenv("ORANGEHRM_URL", "https://example.com/orangehrm")
    monkeypatch.setenv("ORANGEHRM_USERNAME", "Admin")
    monkeypatch.setenv("ORANGEHRM_PASSWORD", "admin123")
    monkeypatch.setenv("SAUCEDEMO_URL", "https://example.com/saucedemo")
    monkeypatch.setenv("SAUCEDEMO_PASSWORD", "secret_sauce")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")

    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.db_path == "./data/test.db"
    assert settings.portal_name == "orangehrm"
    assert settings.report_email == "report@example.com"
    assert settings.smtp_host == "smtp.gmail.com"
    assert settings.smtp_port == 587
    assert settings.smtp_use_tls is True