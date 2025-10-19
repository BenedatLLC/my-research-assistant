---
status: draft
---

# Design for error handling and logging
Goals for this design:
- Provide consistency in the errors reported to users (enough to get a sense of what's
  happening, but not too much detail).
- Consistently log details about errors with stack traces
- Provide a command line option to enable detailed logging

## Error reporting to the user

### Examples
This is a good error:
```
❌ Unknown command '1'. Type 'help' to see available commands.
```

This is not a good error:
```
Generating summary for text of 115356 characters...
❌ Failed to generate summary
```

A better error would be:
```
❌ An unexpected error occurred when generating summary. Running with logging for more details.
```
