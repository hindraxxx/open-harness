# Security and Reliability Checklist

## Input/Output Safety

- XSS, injection, SSRF, and path traversal
- Unsafe object merges and prototype pollution

## AuthN/AuthZ

- Missing tenant or ownership checks
- Trusting client-provided roles, flags, or IDs

## Secrets and PII

- Credentials or tokens in code, config, logs, or responses
- Excessive logging of sensitive payloads

## Runtime Risks

- Unbounded loops or buffers
- Missing timeouts, retries, or rate limits

## Race Conditions

- Shared state without synchronization
- Check-then-act and read-modify-write patterns
- Missing DB locking or atomic updates
