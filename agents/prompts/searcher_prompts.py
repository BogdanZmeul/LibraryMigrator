LIBRARY_API_PROMPT = """Search and list ALL public functions, classes and methods for {library} version {version}. Instructions: 1. Provide a comprehensive list including all submodules, public functions, classes and methods."""

MIGRATION_ADVICE_PROMPT = """ Task: Analyze the migration of '{element}' in library '{library}' from version {old_v} to {new_v}. Instructions: 1. Check if '{element}' is actually a part of {library} or a general function (like numpy or builtin). 2. If it's a general function not related to {library} migration, set status to 'Active' and instruction to 'Standard usage'. 3. Identify the exact status: Active, Deprecated, Removed, or Changed. 4. Provide a concrete code example for the migration. Required Output Format: **Status**: [status] **Instruction**: [instruction] **Example**: ```python # Before ... # After ... """

REFINE_API_LIST_PROMPT = """
Extract all technical names of public classes and methods from the provided documentation.
Pay special attention to methods listed in 'APIDOC' blocks (e.g., concat, DataFrame, read_csv, abs, add).
Return ONLY a comma-separated list of names. No descriptions.
    
Documentation: {raw_text}
"""

REFINE_MIGRATION_JSON_PROMPT = """
Convert this documentation into a valid JSON object. 
IMPORTANT: If the text describes a generic function (not library-specific), maintain its Active status.
{{ 
"status": "Active/Deprecated/Removed/Changed", 
"instruction": "...", 
"example": {{ 
    "before": "...", 
    "after": "..." 
    }} 
}}

Text: {raw_text}
"""

SEARCH_USAGES_SYSTEM_PROMPT = """You are an expert static code analysis tool.
Your task is to analyze the provided source code and find ALL usages of the library '{library_name}'.

INSTRUCTIONS:
1. Identify how the library is imported (e.g., `import {library_name} as alias`).
2. Scan the code for any function calls, class instantiations, or attribute accesses related to that library alias.
3. Extract the specific method name (e.g., from `pd.read_csv(...)` extract `read_csv`).
4. Extract the exact line of code as a pattern.

Ignore comments unless they contain relevant code.
Return the result strictly in JSON format matching the schema."""