"""
Command-line tool to check that LLM and embedding models are configured correctly.
"""
import os
import sys
import argparse
import traceback
import threading
from typing import Callable, Any

# Import Settings early so tests can mock it before main() is called
# This needs to be imported before models.py sets Settings.embed_model
from llama_index.core import Settings


class TimeoutError(Exception):
    """Raised when a function call times out."""
    pass


def _run_with_timeout(func: Callable[[], Any], timeout: float) -> Any:
    """Run a function with a timeout.

    Args:
        func: Function to run (should take no arguments)
        timeout: Timeout in seconds

    Returns:
        The result of the function

    Raises:
        TimeoutError: If the function doesn't complete within the timeout
        Exception: Any exception raised by the function
    """
    result = [None]
    exception = [None]

    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout} seconds")

    if exception[0] is not None:
        raise exception[0]

    return result[0]


def _get_error_suggestions(error: Exception, model_api_base: str) -> str:
    """Get helpful suggestions based on the error type.

    Args:
        error: The exception that was raised
        model_api_base: The API base URL being used

    Returns:
        String with newline-separated suggestions
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    suggestions = []

    # Timeout issues
    if isinstance(error, TimeoutError) or 'timeout' in error_str:
        suggestions.append("The request timed out - this may indicate network issues")
        suggestions.append("Check your internet connection")
        if model_api_base != 'https://api.openai.com/v1':
            suggestions.append(f"Verify MODEL_API_BASE is reachable: {model_api_base}")
        suggestions.append("Try increasing the timeout with --timeout option")

    # API key issues
    if 'api key' in error_str or 'authentication' in error_str or 'unauthorized' in error_str:
        suggestions.append("Check that OPENAI_API_KEY environment variable is set correctly")
        suggestions.append("Verify your API key is valid and has not expired")

    # Connection issues
    if 'connection' in error_str or 'network' in error_str:
        suggestions.append("Check your internet connection")
        if model_api_base != 'https://api.openai.com/v1':
            suggestions.append(f"Verify MODEL_API_BASE is correct: {model_api_base}")

    # Model not found
    if 'model' in error_str and ('not found' in error_str or 'does not exist' in error_str):
        default_model = os.environ.get('DEFAULT_MODEL', 'gpt-4o')
        suggestions.append(f"Check that model '{default_model}' is valid")
        suggestions.append("Try setting DEFAULT_MODEL environment variable to a known model (e.g., 'gpt-4o')")

    # Rate limiting
    if 'rate limit' in error_str or 'quota' in error_str:
        suggestions.append("You may have exceeded your API rate limit or quota")
        suggestions.append("Wait a moment and try again, or check your API usage")

    # Generic suggestions if no specific ones found
    if not suggestions:
        suggestions.append("Check your OPENAI_API_KEY environment variable")
        suggestions.append("Verify MODEL_API_BASE is correct (currently: " + model_api_base + ")")

    return "\n  ".join(suggestions)


def main():
    """Test that LLM and embedding models are configured correctly."""
    parser = argparse.ArgumentParser(description='Check that models are configured and working')
    parser.add_argument('--verbose', action='store_true',
                       help='Show full stack traces on errors')
    parser.add_argument('--timeout', type=float, default=20.0,
                       help='Timeout in seconds for each test (default: 20)')
    parser.add_argument('--loglevel', type=str, choices=['ERROR', 'WARNING', 'INFO', 'DEBUG'],
                       help='Enable logging at specified level')
    args = parser.parse_args()

    # Configure logging if requested (BEFORE importing other modules)
    if args.loglevel:
        from my_research_assistant.logging_config import configure_logging
        configure_logging(loglevel=args.loglevel, keep_all_loggers=True)

    # Import Settings early so tests can mock it before main() is called
    # This needs to be imported before models.py sets Settings.embed_model
    from llama_index.core import Settings
   
    # Save current embed_model before importing models.py
    # (tests may have set it to a mock, and we don't want models.py to overwrite it)
    saved_embed_model = Settings.embed_model

    # Import non-standard library modules AFTER logging is configured
    from my_research_assistant.models import get_default_model, DEFAULT_MODEL, DEFAULT_EMBEDDING_MODEL, MODEL_API_BASE

    # Restore the saved embed_model (in case it was mocked in tests)
    Settings.embed_model = saved_embed_model

    # Track overall success
    all_passed = True

    # Test LLM
    print(f"Testing LLM (model: {DEFAULT_MODEL}, api_base: {MODEL_API_BASE}, timeout: {args.timeout}s)...")
    try:
        def test_llm():
            llm = get_default_model()
            response = llm.complete("Say 'test'")
            return response

        response = _run_with_timeout(test_llm, args.timeout)
        if response and response.text:
            print(f"✓ LLM is working correctly")
            if args.verbose:
                print(f"  Response: {response.text[:100]}")
        else:
            print(f"❌ LLM returned empty response")
            all_passed = False
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        suggestions = _get_error_suggestions(e, MODEL_API_BASE)
        print(f"  Suggestions:\n  {suggestions}")
        if args.verbose:
            print("\nFull traceback:")
            traceback.print_exc()
        all_passed = False

    print()  # Blank line between tests

    # Test embedding model
    print(f"Testing embedding model (model: {DEFAULT_EMBEDDING_MODEL}, api_base: {MODEL_API_BASE}, timeout: {args.timeout}s)...")
    try:
        # Get embed_model from Settings (imported at module level)
        embed_model = Settings.embed_model

        def test_embedding():
            # Use embed_model from outer scope to avoid re-importing
            embeddings = embed_model.get_text_embedding("test")
            return embeddings

        embeddings = _run_with_timeout(test_embedding, args.timeout)
        if embeddings and len(embeddings) > 0:
            print(f"✓ Embedding model is working correctly")
            if args.verbose:
                print(f"  Embedding dimension: {len(embeddings)}")
        else:
            print(f"❌ Embedding model returned empty result")
            all_passed = False
    except Exception as e:
        print(f"❌ Embedding model test failed: {e}")
        suggestions = _get_error_suggestions(e, MODEL_API_BASE)
        print(f"  Suggestions:\n  {suggestions}")
        if args.verbose:
            print("\nFull traceback:")
            traceback.print_exc()
        all_passed = False

    print()  # Blank line before summary

    # Final summary
    if all_passed:
        print("✓ All model checks passed!")
        sys.exit(0)
    else:
        print("❌ Some model checks failed. See errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
