---
status: draft
---
# Design: [Feature Name]

_One-sentence description of what this feature does._

## Problem / Goal

What problem does this solve? Why is this needed?

## Use Cases

1. **Use Case 1**: User wants to...
   - User action: ...
   - System response: ...
   - Outcome: ...

2. **Use Case 2**: User wants to...
   - User action: ...
   - System response: ...
   - Outcome: ...

## Requirements (optional)

What the system needs to do:
- The system shall...
- When [condition], the system should...
- Performance: ...
- Reliability: ...

## Design

How does it work? Cover what's relevant:
- Data flow / architecture (ASCII diagrams welcome)
- Key components, functions, or modules
- Command syntax and output
- State changes (if applicable)
- Error handling
- Edge cases

```
Example data flow:
User → Command → Process → Result
```

```python
# Example data structure (if needed)
class NewStructure:
    field1: str
    field2: int
```

## Examples

Show concrete interactions - this is often the most valuable section.

### Example 1: Happy path
```chat
You: command arg
Response: ...
```

### Example 2: Error case
```chat
You: command invalid-arg
❌ Error message explaining what went wrong
```

### Example 3: Edge case (if interesting)
```chat
You: command edge-case
Response: ...
```

## Testing (optional)

What needs to be tested:
- Happy path scenarios
- Error cases
- Edge cases
- End-to-end user workflows

Example flow to test:
1. User runs `command1 arg`
2. System shows results
3. User runs `command2 number`
4. System processes and displays output

## Open Questions

- [ ] Question 1: ...

---

## Implementation Plan

_Added by design-implementer before coding begins._

### Approach

High-level overview of how to implement this.

### Files to Create/Modify

- `src/module1.py` - Add function X, modify function Y
- `src/module2.py` - Create class Z
- `tests/test_module1.py` - Unit tests for X and Y
- `tests/test_integration.py` - E2E tests

### Steps

1. **Step 1**: Create data structures
2. **Step 2**: Implement core logic
3. **Step 3**: Add command interface
4. **Step 4**: Write tests (unit, integration, E2E)
5. **Step 5**: Update documentation

### Testing Strategy

**Unit Tests**: Test individual functions and edge cases
**Integration Tests**: Test command integration with state machine
**E2E Tests**: Test complete user workflows from Use Cases

**Testability**: Use API-level testing, temp_file_locations fixture, mock external dependencies

### Risks

- **Risk 1**: Performance with large datasets → Mitigation: ...
- **Risk 2**: Backward compatibility → Mitigation: ...

### Documentation

- README.md - Add command reference
- CLAUDE.md - Update architecture
- devlog.md - Add implementation entry

---

## Implementation

_Added by design-implementer after completion._

### Summary

Brief description of what was actually built.

### Key Decisions

- **Decision 1**: Chose X over Y because...
- **Decision 2**: Added helper Z for testability

### Deviations from Plan

- Changed step 2 approach because...
- Or: "No significant deviations"

### Test Coverage

- Unit tests: 8 tests
- Integration tests: 4 tests
- E2E tests: 3 tests
- **Total**: 15 new tests, all passing

### Files Changed

- Created: `src/new_module.py` (150 lines)
- Modified: `src/existing.py` (+80 lines)
- Created: `tests/test_new.py` (8 tests)

### Known Limitations

- [ ] Performance optimization for large datasets (future work)
- Or: "None"

### Documentation

- ✓ README.md
- ✓ CLAUDE.md
- ✓ devlog.md
- ✓ tests/TESTING_SUMMARY.md
