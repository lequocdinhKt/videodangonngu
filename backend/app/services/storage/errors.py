"""Map storage backend errors to HTTP exceptions."""

from fastapi import HTTPException


def storage_http_exception(exc: Exception) -> HTTPException:
    try:
        from botocore.exceptions import ClientError

        if isinstance(exc, ClientError):
            err = exc.response.get("Error", {})
            code = err.get("Code", "")
            message = err.get("Message") or str(exc)
            if code in ("EntityTooLarge", "413"):
                return HTTPException(status_code=413, detail=message)
            if code in ("AccessDenied", "403"):
                return HTTPException(status_code=403, detail=f"Storage access denied: {message}")
            return HTTPException(status_code=502, detail=f"Storage upload failed: {message}")
    except ImportError:
        pass

    try:
        from storage3.exceptions import StorageApiError

        if isinstance(exc, StorageApiError):
            detail = str(exc)
            if "413" in detail or "Payload too large" in detail:
                return HTTPException(status_code=413, detail="File exceeds storage provider size limit")
            return HTTPException(status_code=502, detail=f"Storage upload failed: {detail}")
    except ImportError:
        pass

    return HTTPException(status_code=502, detail=f"Storage error: {exc}")
