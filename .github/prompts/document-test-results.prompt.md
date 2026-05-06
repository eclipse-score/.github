---
agent: test-qa
tools: ['vscode', 'read', 'edit']
description: 'Document unit test execution results with pass/fail summary and failure analysis.'
---

Document the results of executed unit tests.

Tasks:
- Review test execution results.
- Create a report including:
  - Total test cases executed
  - Passed, failed, and skipped counts
  - Detailed failure info with error messages and stack traces
  - Common failure pattern analysis
  - Recommendations for code improvements or further testing
- Format with tables or charts for readability.
- Save at: `.stage/<JIRA-ID>/testResults.md`
