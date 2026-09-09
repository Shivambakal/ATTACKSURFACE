# Privacy Policy

## Data Collection

AttackSurface Timeline collects:
- **User account data**: Email, hashed password, profile information you provide
- **Target observations**: Public webpage content from domains you authorize
- **Research data**: Notes, tasks, findings, and bookmarks you create

## Data Storage

- All data stored in a self-hosted PostgreSQL database
- Passwords are hashed with bcrypt and never stored in plaintext
- Session tokens are hashed before storage
- Evidence records are immutable and include provenance

## Data Sharing

- **No telemetry** by default
- **No analytics** by default
- **No third-party data sharing** by default
- AI providers (Gemini, NVIDIA) receive only sanitized content excerpts for analysis — never credentials, session tokens, or private research data

## Data Retention

- User data is retained until account deletion
- Evidence records are immutable for audit trail integrity
- Sessions expire after 7 days

## User Rights

- **Export**: Export all your data
- **Delete**: Delete individual targets or your entire account
- **Control**: Configure privacy settings per preference

## Conservative Defaults

All privacy settings default to the most conservative option:
- Public profile: disabled
- Telemetry: disabled
- Analytics: disabled
- Data sharing: disabled
