---
status: implemented
---

# Design for error handling and logging
Goals for this design:
- Provide consistency in the errors reported to users (enough to get a sense of what's
  happening, but not too much detail).
- Consistently log details about errors with stack traces
- Provide a command line option to enable detailed logging

## Error reporting to the user
Error messages should always start with "❌". They should provide the following information:
- What (sub)task failed. For example, the `summarize` command has several steps - downloading,
  extracting text, etc. The error message should indicate which of these steps failed.
- Some sense of what went wrong. This may be the specific exception thrown or part of the error message.

The full error message should be between one and three lines. For more detail, the user can refer to the
logs (see below).

### Examples
#### Scenario 1: Unknown command error
This is a good error:
```
❌ Unknown command '1'. Type 'help' to see available commands.
```

#### Scenario 2: Summarization errors
This is not a good error:
```
Generating summary for text of 115356 characters...
❌ Failed to generate summary
```

A better error would be:
```
❌ An unexpected error occurred when generating summary. Run with logging for more details.
```
Even better would be to provide some explanation about what went wrong

#### Scenario 3: Improve error
This is a pretty good error:
```
❌ Improve failed: Summary improvement failed: An error occurred during summarizing: Error code: 401 - {'error':
{'message': 'Incorrect API key provided: sk-U10C2*************0yZg. You can find your API key at
https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'param': None, 'code':
'invalid_api_key'}}
```

## Logging
More detailed error and progress information should be written to the logs. By default, logs are not captured
at all. Via command line options, the user can either enable more logging to be printed to the terminal or
written to a file.

### Command line options
We will support two command line options for logging:
```
  --loglevel ERROR|WARNING|INFO|DEBUG
    This sets the level of logging to be printed to the terminal. For example, If the user specifies
    INFO, log messages with levels ERROR, WARNING, and INFO will be printed. If this option is not
    specified, no log messages are printed to the terminal.

  --logfile FILENAME
    This specifies a file to which log messages should be written. If enabled, all levels of log messages
    should be written to the file. If not specified, defaults to current directory.
```

The `argparse` module should be used for command line argument parsing. Command line argument parsing
is only needed for the `chat` command entry point.

### Logging initialization
Logging should be initialized in the chat command entry point (`src/my_research_assistant/chat.py`),
after parsing command line arguments and before starting the chat interface.

### Integration with Rich library
The project uses the `rich` library for terminal UI. Logging to the terminal should use Rich's formatting
APIs to maintain consistent visual style. When `--loglevel` is specified, log messages should appear inline
with chat responses (not in a separate panel).

During live displays (progress bars, status indicators), log messages should be buffered and displayed
after the live display completes to avoid visual conflicts.

### LlamaIndex logging
LlamaIndex has its own verbose logging system. This should be suppressed/disabled to avoid cluttering
the output.

### Log file behavior
- Log files should be **appended to** on each run (not overwritten)
- Each new run should write a delimiter line to the log file indicating the start of a new session
- Default log location is the current directory if `--logfile` is specified without a path
- No log rotation is needed

### Log message formats
When written to the terminal, log messages should contain a one character level indicator (E, W, I, D)
followed by a space, and then the actual log message content. For example:
```
E An error occurred during summarizing: Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-U10C2*************0yZg.
```
Timestamps should **not** be included in terminal output.

When written to a log file, log messages should contain an iso-formatted timestamp followed by a log level code, and then the message.

When an error occurs, the full stack trace should be logged.

### Error context
For errors that occur during multi-step operations or paper processing, log messages should include:
- Which paper is being processed (ArXiv ID or number reference)
- Current workflow state (e.g., "select-new", "summarized", "sem-search")
- The specific substep that failed (e.g., "downloading PDF", "extracting text", "generating summary")

This context should be included in log messages but not necessarily in user-facing error messages (which should remain concise).

### Log levels
The existing code needs to be instrumented with logging. The general guidelines are:
- ERROR   - for all errors. Errors should include stack traces
- WARNING - for unusual situations that the user should be aware of
- INFO    - for progress information during normal operation. Also, log user commands at this level.
          Progress should be logged even if it duplicates terminal output (important context for log files).
- DEBUG   - for very detailed debugging information

### Exception handling patterns
When catching and re-raising exceptions, use the `raise ... from ...` pattern to preserve the exception chain:
```python
try:
    # some operation
except SomeException as e:
    logger.error("Failed to do X", exc_info=True)
    raise CustomError("Higher-level description") from e
```

Logging should happen at **catch sites** rather than at raise sites for custom exceptions.

### Sensitive information
Sensitive information (API keys, credentials) should be redacted when logging. This applies to:
- OpenAI API keys
- Google Search API keys
- Any other credentials in error messages from external services

Use pattern matching to identify and redact partial API keys (e.g., `sk-U10C2*************0yZg`).

### API and external service errors
Errors from external services should be included in user-facing error messages since they often contain
actionable information (e.g., invalid API key, rate limits, service unavailable). These should include:
- Google Custom Search API errors
- OpenAI/LLM API errors
- ArXiv API errors

Other internal errors should use the concise format described in the "Error reporting to the user" section.

### Testing implications
Existing tests that assert on specific error message content will need to be updated to match the new
error message format (starting with "❌"). No specific tests for logging behavior are required.

## Implementation Plan

### Summary
This implementation adds comprehensive logging infrastructure and standardizes error reporting across the research assistant chatbot. The approach involves:
1. Creating a centralized logging configuration module
2. Adding command-line arguments for logging control
3. Integrating Rich's RichHandler for terminal logging
4. Instrumenting all major modules with appropriate log levels
5. Standardizing error messages with the "❌" prefix
6. Implementing API key redaction for sensitive information
7. Updating tests to match new error message formats

### Files to Create/Modify

**New Files:**
- `src/my_research_assistant/logging_config.py` - Centralized logging configuration module

**Modified Files:**
- `src/my_research_assistant/chat.py` - Add CLI argument parsing and logging initialization
- `src/my_research_assistant/state_machine.py` - Add logging for state transitions and errors
- `src/my_research_assistant/workflow.py` - Add logging for workflow operations
- `src/my_research_assistant/arxiv_downloader.py` - Add logging for download operations
- `src/my_research_assistant/google_search.py` - Add logging for search operations
- `src/my_research_assistant/summarizer.py` - Add logging for summarization operations
- `src/my_research_assistant/vector_store.py` - Add logging for indexing operations
- `src/my_research_assistant/paper_removal.py` - Add logging for removal operations
- `src/my_research_assistant/result_storage.py` - Add logging for result storage operations
- `src/my_research_assistant/validate_store.py` - Add logging for validation operations
- Multiple test files - Update error message assertions to expect "❌" prefix

### Step-by-Step Plan

#### Step 1: Create logging configuration module
- Create `logging_config.py` with functions:
  - `configure_logging(loglevel: Optional[str], logfile: Optional[str])` - Main configuration function
  - `_create_console_handler()` - Creates Rich-based terminal handler
  - `_create_file_handler(logfile: str)` - Creates file handler with appropriate formatting
  - `_write_session_delimiter(logfile: str)` - Writes session start marker to log file
  - `redact_api_key(text: str) -> str` - Redacts API keys (show first 6 and last 4 chars)
  - Custom log formatter for file output (ISO timestamp + level + message)
  - Custom log formatter for terminal output (level char + message, no timestamp)
- Configure LlamaIndex logging to WARNING level
- Set up root logger with appropriate handlers based on arguments

#### Step 2: Update chat.py entry point
- Add argparse for `--loglevel` and `--logfile` options
- Call `configure_logging()` before creating ChatInterface
- Update error messages to use "❌" prefix
- Add INFO-level logging for user commands

#### Step 3: Instrument state_machine.py
- Add logger creation: `logger = logging.getLogger(__name__)`
- Log state transitions at INFO level: "State transition: {from_state} -> {to_state}"
- Log errors at ERROR level with exc_info=True
- Update all error messages to start with "❌"
- Add context logging for paper operations (paper ID, state, substep)

#### Step 4: Instrument workflow.py
- Add logger creation
- Log workflow events at INFO level: "Starting {operation} for paper {arxiv_id}"
- Log errors at ERROR level with full context
- Update error messages to start with "❌"
- Add substep logging (e.g., "Downloading PDF", "Extracting text", "Generating summary")

#### Step 5: Instrument core modules
For each of arxiv_downloader.py, google_search.py, summarizer.py, vector_store.py:
- Add logger creation
- Add INFO logging for operations start/completion
- Add ERROR logging for failures with exc_info=True
- Add DEBUG logging for detailed information
- Update error messages to start with "❌"
- Add API key redaction where external service errors are logged

#### Step 6: Instrument utility modules
For paper_removal.py, result_storage.py, validate_store.py:
- Add logger creation
- Add INFO logging for operations
- Add ERROR logging for failures
- Update error messages to start with "❌"

#### Step 7: Update test files
Update assertion patterns in these test files:
- `tests/test_state_machine.py` - Update error message assertions
- `tests/test_chat.py` - Update error message assertions
- `tests/test_paper_argument_parsing.py` - Update error message assertions
- `tests/test_paper_removal.py` - Update error message assertions
- `tests/test_open_command.py` - Update error message assertions
- Any other tests that assert on error message content

### Testing Strategy

**Unit Tests:**
- Test `redact_api_key()` function with various API key formats (OpenAI sk-*, Google API keys)
- Test log formatter output formats (terminal vs file)
- Test session delimiter format

**Integration Tests:**
- Test logging configuration with different CLI argument combinations
- Test that error messages start with "❌" in actual command execution
- Test that log messages appear in correct format (terminal vs file)
- Test API key redaction in actual error scenarios
- Test LlamaIndex logging suppression

**End-to-End Test Scenarios:**
Based on user workflows in the design:

1. **Error reporting workflow:**
   - Execute command that triggers error (e.g., invalid API key)
   - Verify error message starts with "❌" and is concise (1-3 lines)
   - Verify full details are in log file (if enabled)
   - Verify API keys are redacted in both terminal and log file

2. **Logging levels workflow:**
   - Run with `--loglevel INFO`
   - Verify INFO, WARNING, ERROR messages appear on terminal
   - Verify DEBUG messages do not appear
   - Run with `--loglevel DEBUG`
   - Verify all messages including DEBUG appear

3. **Log file workflow:**
   - Run with `--logfile research-assistant.log`
   - Verify log file created with session delimiter
   - Run again with same logfile
   - Verify second session appended (not overwritten)
   - Verify log file contains ISO timestamps

4. **Multi-step operation logging:**
   - Execute `summarize` command
   - Verify substep logging appears (download, extract, summarize)
   - Verify paper ID context in log messages
   - If error occurs, verify which substep failed is clear

**Testability Considerations:**
- Logging configuration is API-level testable (no terminal I/O needed)
- Error message format changes are testable via existing test assertions
- API key redaction is pure function (easily testable)
- Log file output can be tested by reading file contents
- Use caplog fixture for testing log message content in pytest

### Risk Areas

**Backward Compatibility:**
- Existing tests that assert on error messages will break - need systematic updates
- Error message format changes could impact user scripts parsing output (low risk)

**Performance:**
- Logging overhead should be minimal at INFO level
- File I/O for logging could impact performance on slow filesystems (unlikely)
- Rich console handler may have overhead but should be acceptable

**Integration:**
- Rich handler interaction with live displays (progress bars, status) needs careful handling
- LlamaIndex logging suppression may not catch all verbose output
- Multiple modules logging could create race conditions in file handler (Python logging handles this)

**Error Handling:**
- Log file write failures need handling (disk full, permissions)
- Invalid log level arguments need validation
- API key redaction regex must handle various formats

**Testing:**
- Many test files need updates - must ensure all are found and updated
- Log message assertions in tests could become brittle
- Need to ensure logging doesn't interfere with test assertions

### Documentation Updates

**README.md:**
- Add documentation for `--loglevel` and `--logfile` options
- Add example usage with logging enabled
- Add note about log file location and format

**CLAUDE.md:**
- Add logging configuration to architecture overview
- Document logging module and its responsibilities
- Add logging conventions to development notes
- Update error handling section with new patterns

**devlog.md:**
- Add entry describing error handling and logging implementation
- Include original user prompt as requested in CLAUDE.md

