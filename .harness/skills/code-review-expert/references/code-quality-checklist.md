# Code Quality Checklist

## Error Handling

- **Swallowed exceptions**: Empty catch blocks or catch with only logging
- **Overly broad catch**: Catching base exception types instead of specific ones
- **Error information leakage**: Stack traces or internals exposed to users
- **Missing error handling**: No boundary for fallible I/O, network, or parsing
- **Async error handling**: Unhandled promise rejections or missing error propagation

## Performance & Caching

- **Expensive operations in hot paths**: Repeated parsing, crypto, or regex compilation
- **N+1 queries**: Per-item DB calls instead of batching
- **Missing cache**: Repeated expensive work without TTL or invalidation
- **Unbounded memory**: Collections that can grow without limit

## Boundary Conditions

- **Missing null checks**: Property access on nullable objects
- **Empty collections**: First or last element access without length checks
- **Numeric boundaries**: Division by zero, negative values, off-by-one errors
- **String boundaries**: Empty, whitespace-only, or very long strings
