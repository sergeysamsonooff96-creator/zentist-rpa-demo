from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


class RetryableUiError(Exception):
    pass


def ui_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(RetryableUiError),
    )