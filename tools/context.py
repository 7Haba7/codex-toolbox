"""Print a bounded overview of the current Git working tree."""
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=8_000_000_000,
                        help="maximum output characters (default: %(default)s)")
    parser.add_argument("--path", help="limit the summary to a literal repository path")
    args = parser.parse_args()
    if args.limit < 100:
        parser.error("--limit must be at least 100")
    scope = ["--", args.path] if args.path is not None else []
    sections = []
    for label, command in [
        ("Working tree", ["status", "--short", "--branch"]),
        ("Unstaged changes", ["diff", "--stat"]),
        ("Staged changes", ["diff", "--cached", "--stat"]),
    ]:
        result = subprocess.run(["git", "--literal-pathspecs", *command, *scope], capture_output=True, text=True, errors="replace")
        if result.returncode:
            sys.exit(result.stderr.strip() or "Git command failed")
        sections.append(label + "\n" + (result.stdout.strip() or "(none)"))
    report = "\n\n".join(sections) + "\n"
    suffix = "\n[truncated]\n"
    if len(report) > args.limit:
        report = report[:args.limit - len(suffix)] + suffix
    sys.stdout.write(report)


if __name__ == "__main__":
    main()
