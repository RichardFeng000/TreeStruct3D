# Security policy

TreeStruct3D executes generated Blender Python programs. Treat generated code as
untrusted and run it only in an isolated environment with access limited to the
files and credentials required for the experiment.

Never place API keys in tracked YAML files, logs, generated programs, issues, or
pull requests. Use environment variables and the ignored local configuration
described in the documentation.

For a suspected vulnerability, use GitHub's private vulnerability reporting
for this repository. Do not publish credentials, exploit details, or other
sensitive information in a public issue.
