"""mailbox.py — two-way messages between the engineer session and the operator agent.

What existed before was one-way: the engineer could `tools/agents.py send` text and `tail` the pane,
and the operator could write a result file. The operator had no way to ASK anything - so a question
like "is this 2-pixel window visible to you or shall I park it?" could not travel back, and the
operator either guessed or stopped.

Design: append-only files with per-reader cursors, so neither side can lose a message and neither side
can overwrite the other.

    state/mail/<name>.md        messages addressed TO <name>
    state/mail/.<name>.cursor   byte offset that <name> has already read

    python3 tools/mailbox.py post --to operator --from engineer "message"
    python3 tools/mailbox.py check --as operator          # unread messages for the operator
    python3 tools/mailbox.py inbox --as operator          # everything addressed to it
"""
import argparse
import os
import time

MAILDIR = os.path.join("state", "mail")


def _path(who):
    return os.path.join(MAILDIR, f"{who}.md")


def _cursor(who):
    return os.path.join(MAILDIR, f".{who}.cursor")


def post(to, sender, text):
    os.makedirs(MAILDIR, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(_path(to), "a") as f:
        for line in text.strip().splitlines():
            f.write(f"[{stamp}] {sender}: {line}\n")
    print(f"posted to {to}")
    return 0


def check(who, advance=True):
    path = _path(who)
    if not os.path.exists(path):
        print(f"(no mailbox for {who})")
        return 0
    cur_path = _cursor(who)
    offset = int(open(cur_path).read().strip()) if os.path.exists(cur_path) else 0
    data = open(path, "rb").read()
    new = data[offset:]
    if not new:
        print(f"(no new messages for {who})")
        return 0
    print(new.decode("utf-8", "ignore").strip())
    if advance:
        with open(cur_path, "w") as f:
            f.write(str(len(data)))
    return 0


def inbox(who):
    path = _path(who)
    if not os.path.exists(path):
        print(f"(no mailbox for {who})")
        return 0
    print(open(path).read().strip())
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["post", "check", "inbox"])
    ap.add_argument("--to")
    ap.add_argument("--from", dest="sender", default="engineer")
    ap.add_argument("--as", dest="as_")
    ap.add_argument("text", nargs="?")
    a = ap.parse_args()
    if a.action == "post":
        if not a.to or not a.text:
            print("post needs --to and TEXT")
            return 2
        return post(a.to, a.sender, a.text)
    if a.action == "check":
        return check(a.as_ or "operator")
    return inbox(a.as_ or "operator")


if __name__ == "__main__":
    raise SystemExit(main())
