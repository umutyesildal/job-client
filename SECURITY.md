# Security Policy

## Supported version

Security fixes are applied to the latest `main` branch. Older commits and forks
are not maintained by this project.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities, leaked credentials, auth
bypasses, or data-access problems. Use **Security → Report a vulnerability** on
the GitHub repository so the report and discussion remain private.

Include the affected component, reproduction steps, impact, and a suggested
fix when possible. Please allow maintainers time to confirm and remediate the
issue before public disclosure.

## Sensitive boundaries

- Google service-account credentials and GitHub tokens are server-only.
- The browser bundle must never receive publishing credentials.
- Pull requests and forks must use sample data or their own spreadsheet.
- Only maintainers run the workflow against the canonical production Sheet.
