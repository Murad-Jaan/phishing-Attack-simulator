#!/usr/bin/env bash
# Security checks for the Phishing Attack Simulator.
# Usage: bash scripts/security-check.sh [index.html]
set -u
F="${1:-index.html}"; fail=0
bad(){ echo "FAIL: $1"; fail=1; }
ok(){ echo "ok:   $1"; }
chk(){ # $1 = description, $2 = regex that must NOT appear
  if grep -nE "$2" "$F" >/dev/null; then bad "$1"; grep -nE "$2" "$F" | cut -c1-140 | head -3; else ok "$1"; fi; }

chk "no eval() or new Function()"            '(^|[^a-zA-Z_.])eval\(|new Function\('
chk "no document.write()"                    'document\.write\('
chk "no network calls (fetch/XHR/WebSocket)" 'fetch\(|XMLHttpRequest|WebSocket|sendBeacon'
chk "no external scripts or stylesheets"     '<script[^>]+src=|<link[^>]+href=["'"'"']?https?:'
chk "no hard-coded secrets or private keys"  'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|token)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9_-]{12,}'

if grep -n 'type="password"' "$F" | grep -v disabled >/dev/null; then
  bad "an enabled password field exists (the simulator must never collect credentials)"
else ok "password fields are disabled (no credential collection)"; fi

if grep -q 'Content-Security-Policy' "$F" && grep -q "default-src 'none'" "$F"; then
  ok "Content-Security-Policy blocks all network and external resources"
else bad "Content-Security-Policy (default-src 'none') is missing"; fi

echo "info: innerHTML used $(grep -o 'innerHTML' "$F" | wc -l) times. Any text from users or emails must go through esc()."
[ $fail -eq 0 ] && echo "RESULT: all checks passed" || echo "RESULT: some checks failed"
exit $fail
