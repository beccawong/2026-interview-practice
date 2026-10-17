# Google Python Style Rules (AI-Optimized)

## 1. Code Formatting
- Indentation: Use 4 spaces per level. No tabs.
- Line Length: Maximum 100 characters. Wrap long lines using explicit parentheses.
- Naming:
  - Modules/Variables/Functions/Methods: lower_with_underscores
  - Classes: CapWords
  - Constants: UPPER_WITH_UNDERSCORES

## 2. Imports
- Imports: Use full package paths (e.g., `from package.module import func`). No relative imports.
- Ordering: Group in order: 1) Standard Library, 2) Third-Party, 3) Local Modules. Alphabetize within groups.
- Location: Put imports at the top of the file, immediately after module docstrings.

## 3. Documentation & Type Hints
- Type Hints: Mandatory PEP 484 type hints for all function signatures.
- Docstrings: Use Google format with Args, Returns, and Raises sections. Example:
  """One-line summary.

  Args:
      param1: Type description.

  Returns:
      Type description.

  Raises:
      ValueError: Under condition.
  """

## 4. Error Handling & Logic
- Exceptions: Never catch broad `Exception`. Minimally scope `try` blocks.
- Execution: Always wrap main logic execution blocks in `if __name__ == "__main__":`.
- Strings: Use implicit line joining inside parentheses instead of backslashes.
