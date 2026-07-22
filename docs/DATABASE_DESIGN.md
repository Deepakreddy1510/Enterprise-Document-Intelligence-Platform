# DATABASE DESIGN

See [README](../README.md) and [implementation plan](IMPLEMENTATION_PLAN.md). This project stores all user data and 384-dimensional normalized embeddings in PostgreSQL with pgvector. All records are ownership-scoped by the authenticated JWT user. Uploaded PDFs are untrusted input; Gemini receives explicit instructions not to obey source instructions. Run cd backend && pytest; npm --prefix frontend run test
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /workspace/Enterprise-Document-Intelligence-Platform/backend
configfile: pyproject.toml
testpaths: tests
collected 0 items / 2 errors

==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_config.py _____________________
ImportError while importing test module '/workspace/Enterprise-Document-Intelligence-Platform/backend/tests/test_config.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.14.4/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_config.py:3: in <module>
    from app.core.config import Settings
E   ModuleNotFoundError: No module named 'app'
______________________ ERROR collecting tests/test_pdf.py ______________________
ImportError while importing test module '/workspace/Enterprise-Document-Intelligence-Platform/backend/tests/test_pdf.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.14.4/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_pdf.py:2: in <module>
    from app.services.pdf import chunk_pages, clean_text
E   ModuleNotFoundError: No module named 'app'
=============================== warnings summary ===============================
../../../root/.pyenv/versions/3.14.4/lib/python3.14/site-packages/_pytest/config/__init__.py:1434
  /root/.pyenv/versions/3.14.4/lib/python3.14/site-packages/_pytest/config/__init__.py:1434: PytestConfigWarning: Unknown config option: asyncio_mode
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR tests/test_config.py
ERROR tests/test_pdf.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
========================= 1 warning, 2 errors in 0.24s ========================= and Docker Compose for local verification.
