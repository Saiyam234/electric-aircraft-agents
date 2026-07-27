"""Agent scripts for the electric-aircraft-agents project.

This is a package (rather than a bare directory) so agents can be run as
`python3 -m agents.<name>` from the repo root. That keeps the repo root on
sys.path, which is what makes each agent's `import storage` /
`import agent_runtime` resolve. Running a script directly as
`python3 agents/<name>.py` puts `agents/` on sys.path instead and those
imports fail.
"""
