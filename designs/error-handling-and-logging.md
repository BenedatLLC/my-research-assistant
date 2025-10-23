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
    should be written to the file.
```

The `argparse` module should be used for command line argument parsing.

### Log message formats
When written to the terminal, log messages should contain a one character level indicator (E, W, I, D)
followed by a space, and then the actual log message content. For example:
```
E An error occurred during summarizing: Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-U10C2*************0yZg.
```

When written to a log file, log messages should contain an iso-formatted timestamp followed by a log level code, and then the message.

When an error occurs, the full stack trace should be logged.

### Log levels
The existing code needs to be instrumented with logging. The general guidelines are:
- ERROR   - for all errors. Errors should include stack traces
- WARNING - for unusual situations that the user should be aware of
- INFO    - for progress information during normal operation. Also, log user commands at this level.
- DEBUG   - for very detailed debugging information

