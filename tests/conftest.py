# pytest configuration to ensure 'my_research_assistant' is importable
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
