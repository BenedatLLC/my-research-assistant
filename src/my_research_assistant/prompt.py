"""
Handling of LLM prompts. We store the prompts as markdown template files in the
directory ./prompts. A prompt can have template variables of the form {{VAR_NAME}}.
These then must be passed in to subst_prompt() and subst_prompts() to instantiate
the prompt(s).

INVARIANT: Prompt Variable Syntax
All prompt templates MUST use double-brace syntax {{variable_name}} for variable substitution.
Single braces {variable_name} will not be substituted and will appear as literal text in the prompt.
This is enforced by the subst_prompt() function below.
"""
from os.path import join, exists
import re

from importlib import resources
import my_research_assistant

class PromptFileError(Exception):
    pass

class PromptVarError(Exception):
    """Thrown when a prompt variable is reference in a prompt, but not provided in the keyword arguments"""
    pass


PROMPT_VAR_RE=re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')

def subst_prompt(prompt_name:str,
                 **kwargs) -> str:
    """Load the specified prompt from its file and substitute any prompt variables of the form '{{identifier}}'
    from the keyword arguments. Values for the prompt variables come from the keyword
    arguments. If a prompt variable referenced in the prompt is not provided,
    throws PromptVarError.

    INVARIANT: Only double-brace {{variable}} syntax is recognized for substitution.
    Single-brace {variable} syntax will NOT be substituted."""
    try:
        with resources.files(my_research_assistant).joinpath(f"prompts/{prompt_name}.md").open() as f:
            prompt_template = f.read()
    except Exception as e:
        raise PromptFileError(f"Clould not load prompt {prompt_name}") from e
    # do the substitution of keywords
    def replace_var(match):
        var_name = match.group(1)
        if var_name not in kwargs:
            raise PromptVarError(f"Prompt variable '{var_name}' referenced in prompt but not provided in keyword arguments")
        return str(kwargs[var_name])
    
    return PROMPT_VAR_RE.sub(replace_var, prompt_template)


def subst_prompts(prompt_names:list[str],
                  **kwargs) -> str:
    """Load the specified prompts from their file and substitute any prompt variables of the form '{{identifier}}'
    from the keyword arguments. Values for the prompt variables come from the keyword
    arguments. If a prompt variable referenced in the prompt is not provided,
    throws PromptVarError.
    This returns the concatenation of all the prompts, in the order specified"""
    return '\n'.join([subst_prompt(prompt_name, **kwargs)
                      for prompt_name in prompt_names])

