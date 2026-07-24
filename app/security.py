import re
import shlex
from typing import Tuple

ALLOWED_LEADING_PROGRAMS = {
    "python",
    "python3",
    "pypy3",
    "g++",
    "gcc",
    "cc",
    "clang",
    "clang++",
    "java",
    "javac",
    "rustc",
    "cargo",
    "go",
    "ruby",
    "node",
}

FORBIDDEN_META_SUBSTRINGS = (
    ";",
    "&&",
    "||",
    "|",
    ">",
    ">>",
    "<",
    "<<",
    "`",
    "$(",
    "${",
    "&",
    "\n",
    "\r",
    "\t",
)

FORBIDDEN_BINARIES = {
    "sh",
    "bash",
    "dash",
    "zsh",
    "fish",
    "csh",
    "tcsh",
    "curl",
    "wget",
    "nc",
    "ncat",
    "netcat",
    "ssh",
    "scp",
    "sftp",
    "telnet",
    "rm",
    "rmdir",
    "dd",
    "mkfs",
    "fdisk",
    "chmod",
    "chown",
    "chgrp",
    "sudo",
    "su",
    "doas",
    "kill",
    "killall",
    "pkill",
    "mount",
    "umount",
    "reboot",
    "shutdown",
    "poweroff",
    "systemctl",
    "service",
    "apt",
    "apt-get",
    "pip",
    "pip3",
    "conda",
    "docker",
    "nsenter",
    "unshare",
    "setcap",
    "capsh",
}

FORBIDDEN_FLAGS = {
    "-c",
    "--command",
    "-wrapper",
    "--wrapper",
    "--to-python",
}

FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"(^|/)\.\.($|/)"),
    re.compile(r"^/"),
    re.compile(r"/etc/"),
    re.compile(r"/proc/"),
    re.compile(r"/sys/"),
    re.compile(r"/dev/"),
    re.compile(r"/root(/|$)"),
    re.compile(r"/var/"),
    re.compile(r"/tmp/"),
)

MAX_COMMAND_LENGTH = 1024
MAX_TOKENS = 32

REQUIRED_PLACEHOLDERS = {
    "compile": ("{src}", "{exe}"),
    "run": (),
}
RUN_ALLOWED_PLACEHOLDERS = ("{file}", "{exe}")

def _has_forbidden_meta(cmd: str) -> Tuple[bool, str]:
    for meta in FORBIDDEN_META_SUBSTRINGS:
        if meta in cmd:
            return True, meta
    return False, ""

def _tokenize(cmd: str) -> Tuple[bool, list, str]:
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError as e:
        return False, [], f"unterminated quote: {e}"
    return True, tokens, ""

def _check_leading_program(tokens: list) -> Tuple[bool, str]:
    if not tokens:
        return False, "empty command"
    head = tokens[0]
    if head.startswith("./"):
        return True, ""
    if head in ALLOWED_LEADING_PROGRAMS:
        return True, ""
    return False, f"leading program not allowed: {head!r}"

def _check_blacklisted_tokens(tokens: list) -> Tuple[bool, str]:
    for tok in tokens:
        if tok in FORBIDDEN_BINARIES:
            return False, f"forbidden binary in command: {tok!r}"
        if tok in FORBIDDEN_FLAGS:
            return False, f"forbidden flag in command: {tok!r}"
        for pat in FORBIDDEN_PATH_PATTERNS:
            if pat.search(tok):
                return False, f"forbidden path reference in command: {tok!r}"
    return True, ""

def _check_placeholders(cmd: str, kind: str) -> Tuple[bool, str]:
    required = REQUIRED_PLACEHOLDERS.get(kind, ())
    for ph in required:
        if ph not in cmd:
            return False, f"missing required placeholder {ph!r} for {kind} command"
    if kind == "run":
        present = [ph for ph in RUN_ALLOWED_PLACEHOLDERS if ph in cmd]
        if not present:
            return False, "run command must reference {file} or {exe}"
    return True, ""

def validate_command(cmd: str, kind: str) -> Tuple[bool, str]:
    if kind not in REQUIRED_PLACEHOLDERS:
        return False, f"unknown command kind: {kind!r}"
    if not isinstance(cmd, str) or not cmd or not cmd.strip():
        return False, "empty command"
    if len(cmd) > MAX_COMMAND_LENGTH:
        return False, f"command too long (>{MAX_COMMAND_LENGTH} chars)"
    ok, reason = _check_placeholders(cmd, kind)
    if not ok:
        return False, reason
    bad, meta = _has_forbidden_meta(cmd)
    if bad:
        return False, f"forbidden shell meta-character: {meta!r}"
    ok, tokens, reason = _tokenize(cmd)
    if not ok:
        return False, reason
    if len(tokens) > MAX_TOKENS:
        return False, f"command has too many tokens (>{MAX_TOKENS})"
    ok, reason = _check_leading_program(tokens)
    if not ok:
        return False, reason
    ok, reason = _check_blacklisted_tokens(tokens)
    if not ok:
        return False, reason
    return True, ""


def validate_rendered_command(cmd: str) -> Tuple[bool, str]:
    if not isinstance(cmd, str) or not cmd or not cmd.strip():
        return False, "empty rendered command"
    if len(cmd) > MAX_COMMAND_LENGTH:
        return False, f"command too long (>{MAX_COMMAND_LENGTH} chars)"
    bad, meta = _has_forbidden_meta(cmd)
    if bad:
        return False, f"forbidden shell meta-character: {meta!r}"
    ok, tokens, reason = _tokenize(cmd)
    if not ok:
        return False, reason
    if len(tokens) > MAX_TOKENS:
        return False, f"command has too many tokens (>{MAX_TOKENS})"
    if not tokens:
        return False, "empty command"
    head = tokens[0]
    if not head.startswith("./") and head not in ALLOWED_LEADING_PROGRAMS:
        return False, f"leading program not allowed: {head!r}"
    ok, reason = _check_blacklisted_tokens(tokens)
    if not ok:
        return False, reason
    return True, ""