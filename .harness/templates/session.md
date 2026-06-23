---
session_id: "{{SESSION_ID}}"
status: "start"
planning_approved: "false"
planning_approved_by: ""
planning_approved_at: ""
planning_approved_hash: ""
review_approved: "false"
review_approved_by: ""
review_approved_at: ""
quality_approved: "false"
quality_approved_by: ""
quality_approved_at: ""
recovery_attempts: "0"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
---

# Harness Session: {{SESSION_ID}}

## Requirement Summary

TBD

## Acceptance Criteria

- [ ] TBD

## Validation Plan

- [ ] TBD

## Implementation Guidance

TBD

### Overall Flow

```mermaid
sequenceDiagram
    participant Client
    participant FileA_Controller
    participant FileB_Service
    participant FileC_RepositoryOrGateway
    Client->>FileA_Controller: request
    FileA_Controller->>FileB_Service: command/query
    FileB_Service->>FileC_RepositoryOrGateway: persistence or external call
    FileC_RepositoryOrGateway-->>FileB_Service: result
    FileB_Service-->>FileA_Controller: response model
    FileA_Controller-->>Client: response
```

### Implementation Sketch

TBD

### Decision Flow

```mermaid
flowchart TD
    Start([Input or event]) --> Check{Decision condition}
    Check -->|Case A| CaseA[Expected behavior A]
    Check -->|Case B| CaseB[Expected behavior B]
    CaseA --> Result[Observable result]
    CaseB --> Result
```

### Code Anchors

TBD

## Implementation Checklist

- [ ] TBD

## Planning Approval

TBD

## Review

### AI Review

TBD

### Human Review

TBD

### Required Fixes

- [ ] TBD

## Quality Check

### Commands Run

TBD

### Proof

- [ ] TBD

### Manual Validation

TBD

## Final Approval

TBD

## Notes

TBD
