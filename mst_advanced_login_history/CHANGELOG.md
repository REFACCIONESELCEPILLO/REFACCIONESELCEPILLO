Changelog
=========

18.0.1.1.0 - ICKAB Edition
--------------------------
- Preserved the user's Spanish (Mexico) translation work.
- Changed commercial branding and maintainer metadata to ICKAB.
- Model Log Configuration now controls which models are actually audited.
- Disabled indiscriminate global create/write/unlink logging for unconfigured models.
- Added Stock Picking related-model resolution for `stock.move` and `stock.move.line`.
- Restricted login and audit information to system administrators.
- Restricted the root audit menu and Advanced Logs menu to system administrators.
- Corrected simultaneous-session handling so a new login does not close other sessions.
- Corrected logout lookup to avoid closing another session when a session id is present.
- Kept historical logs intact; no automatic purge is introduced in this release.

## 18.0.1.2.0 - ICKAB access control

- Added the dedicated security group **Full Access to ICKAB Audit History**.
- The application is visible only to users assigned to this group.
- Group members can view Dashboard, Login Logs, Failed Login Logs, Advanced Logs and Model Logs.
- Group members can create and maintain Model Log Configuration records.
- Users without the group cannot access the audit models through the UI or RPC ACLs.
- Dashboard controller now validates the ICKAB audit group instead of the global Odoo Settings administrator group.
- Kill All Sessions now performs a server-side permission check.
