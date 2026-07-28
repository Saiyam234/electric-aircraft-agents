"""Oversight dashboard — see what the agent ecosystem is doing, and intervene.

CLAUDE.md defines a "medium-loose hybrid" oversight tier: batched decision
requests and milestone digests reach Saiyam, safety/regulatory/irreversible-
cost issues always surface immediately, and day-to-day division work stays
internal. All of that already gets written to D1 — but until now the only way
to read any of it was querying storage.py by hand, which is not oversight.

This is deliberately read-mostly. The two things it can actually change are
the two decisions CLAUDE.md reserves for Saiyam:
  - answering a queued decision request
  - approving or rejecting a proposed requirement

It does NOT let you edit baselines, configurations, or knowledge-base entries.
Those belong to the agents by the founding principle, and a dashboard that
let a human quietly rewrite them would undermine the whole arrangement.

Run:  python3 dashboard.py     then open http://127.0.0.1:5000
"""

import html
import json
from collections import Counter

from flask import Flask, redirect, request, url_for

import storage

app = Flask(__name__)

# Event types that must surface immediately per CLAUDE.md's standing hard rule.
URGENT_EVENTS = {"escalation"}

STYLE = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; background:#0f1115; color:#e6e8eb;
       font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
header { padding:20px 28px; border-bottom:1px solid #262a33; display:flex;
         align-items:baseline; gap:16px; flex-wrap:wrap; }
h1 { font-size:19px; margin:0; font-weight:650; letter-spacing:-.01em; }
.sub { color:#8b929e; font-size:13px; }
main { padding:24px 28px; max-width:1180px; }
section { margin-bottom:34px; }
h2 { font-size:13px; text-transform:uppercase; letter-spacing:.07em;
     color:#8b929e; margin:0 0 12px; font-weight:600; }
.cards { display:flex; gap:12px; flex-wrap:wrap; }
.card { background:#161920; border:1px solid #262a33; border-radius:10px;
        padding:14px 18px; min-width:132px; }
.card .n { font-size:26px; font-weight:650; letter-spacing:-.02em; }
.card .l { color:#8b929e; font-size:12px; margin-top:2px; }
.item { background:#161920; border:1px solid #262a33; border-radius:10px;
        padding:16px 18px; margin-bottom:12px; }
.item.urgent { border-color:#7f2a2a; background:#1d1517; }
.item.action { border-color:#2f4b7f; }
.meta { color:#8b929e; font-size:12px; margin-bottom:7px;
        display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.tag { background:#222834; border-radius:5px; padding:2px 8px; font-size:11px;
       letter-spacing:.03em; }
.tag.red { background:#5c1f1f; color:#ffc9c9; }
.tag.blue { background:#1f3a5c; color:#c9e0ff; }
.tag.green { background:#1c4429; color:#c4f0d1; }
.body { white-space:pre-wrap; word-break:break-word; font-size:14px; }
form { margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
input[type=text] { flex:1; min-width:280px; background:#0f1115; color:#e6e8eb;
       border:1px solid #333945; border-radius:7px; padding:9px 11px; font-size:14px; }
button { background:#2f4b7f; color:#fff; border:0; border-radius:7px;
         padding:9px 15px; font-size:13px; font-weight:600; cursor:pointer; }
button.ok { background:#1c4429; }
button.no { background:#5c1f1f; }
button:hover { filter:brightness(1.18); }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td { text-align:left; padding:8px 10px; border-bottom:1px solid #262a33;
        vertical-align:top; }
th { color:#8b929e; font-weight:600; font-size:11px; text-transform:uppercase;
     letter-spacing:.05em; }
.empty { color:#6b7280; font-style:italic; font-size:13px; }
a { color:#7aa2e3; }
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def page(title: str, body: str) -> str:
    return (
        f"<!doctype html><meta charset=utf-8><title>{esc(title)}</title>"
        f"<style>{STYLE}</style>"
        f"<header><h1>Electric Aircraft — Agent Oversight</h1>"
        f"<span class=sub>{esc(title)} · <a href='/'>refresh</a></span></header>"
        f"<main>{body}</main>"
    )


def _parse_kv(description: str) -> dict:
    """Several agents encode structured fields into the description as
    'KEY: value | KEY: value'. Pull them back out for display."""
    out = {}
    for chunk in description.split(" | "):
        if ": " in chunk:
            key, _, val = chunk.partition(": ")
            out[key.strip()] = val.strip()
    return out


def _answered_decision_ids(events) -> set:
    """A decision is considered answered once a decision_answer event quotes
    its question text."""
    answers = [e["description"] for e in events if e["event_type"] == "decision_answer"]
    return {a.split(" || ")[0].removeprefix("RE: ").strip() for a in answers}


@app.route("/")
def index():
    events = storage.get_audit_log(limit=250)
    baselines = storage.list_baselines(limit=40)
    requirements = storage.list_requirements(limit=200)

    try:
        kb_count = len(storage.list_kb_ids())
    except Exception:
        kb_count = "?"  # Vectorize has intermittent outages; never break the page over it

    runs = [e for e in events if e["event_type"] == "agent_end"]
    proposed = [r for r in requirements if r["status"] == "proposed"]
    req_status = Counter(r["status"] for r in requirements)
    answered = _answered_decision_ids(events)

    escalations = [e for e in events if e["event_type"] in URGENT_EVENTS]
    decisions = [e for e in events if e["event_type"] == "decision_request"]
    open_decisions = [d for d in decisions if _parse_kv(d["description"]).get("QUESTION", "") not in answered]

    total_cost = 0.0
    for e in runs:
        for token in e["description"].split():
            if token.startswith("cost=$"):
                try:
                    total_cost += float(token[6:])
                except ValueError:
                    pass

    out = []

    # ---- at a glance -----------------------------------------------------
    out.append("<section><h2>At a glance</h2><div class=cards>")
    for n, label in [
        (len(runs), "agent runs"),
        (f"${total_cost:.2f}", "total spend"),
        (kb_count, "KB entries"),
        (len(baselines), "baselines"),
        (len(requirements), "requirements"),
        (len(open_decisions), "awaiting you"),
    ]:
        out.append(f"<div class=card><div class=n>{esc(n)}</div><div class=l>{esc(label)}</div></div>")
    out.append("</div></section>")

    # ---- escalations: always first, never batched -------------------------
    out.append("<section><h2>Escalations — surfaced immediately</h2>")
    if escalations:
        for e in escalations[:8]:
            out.append(
                f"<div class='item urgent'><div class=meta><span class='tag red'>ESCALATION</span>"
                f"<span>{esc(e['agent'])}</span><span>{esc(e['timestamp'][:19])}</span></div>"
                f"<div class=body>{esc(e['description'])}</div></div>"
            )
    else:
        out.append("<p class=empty>None. Safety, regulatory and irreversible-cost issues appear here the moment they are raised.</p>")
    out.append("</section>")

    # ---- decisions you owe -----------------------------------------------
    out.append("<section><h2>Decisions waiting on you</h2>")
    if open_decisions:
        for d in open_decisions[:6]:
            fields = _parse_kv(d["description"])
            question = fields.get("QUESTION", d["description"])
            out.append("<div class='item action'>")
            out.append(
                f"<div class=meta><span class='tag blue'>DECISION</span>"
                f"<span>{esc(d['agent'])}</span><span>{esc(d['timestamp'][:19])}</span></div>"
            )
            out.append(f"<div class=body><strong>{esc(question)}</strong></div>")
            if fields.get("CONTEXT"):
                out.append(f"<div class=body style='color:#9aa3b0;margin-top:8px'>{esc(fields['CONTEXT'])}</div>")
            try:
                for opt in json.loads(fields.get("OPTIONS", "[]")):
                    label = opt.get("label") or opt.get("option") or json.dumps(opt)
                    tag = opt.get("option") or opt.get("id") or "•"
                    out.append(
                        f"<div class=body style='margin-top:7px'><span class=tag>{esc(tag)}</span> {esc(label)}</div>"
                    )
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
            out.append(
                "<form method=post action='/answer'>"
                f"<input type=hidden name=question value=\"{esc(question)}\">"
                "<input type=text name=answer placeholder='Your decision — e.g. &quot;Option F: set 1.40 m absolute&quot;' required>"
                "<button type=submit>Submit decision</button></form>"
            )
            out.append("</div>")
    else:
        out.append("<p class=empty>Nothing queued. Agents batch real forks here rather than interrupting.</p>")
    out.append("</section>")

    # ---- requirements needing approval ------------------------------------
    out.append(f"<section><h2>Requirements awaiting approval ({len(proposed)})</h2>")
    if proposed:
        out.append("<p class=empty style='margin-top:-4px'>Agents propose; only you approve. Showing the 12 most recent.</p>")
        for r in proposed[:12]:
            out.append("<div class='item action'>")
            out.append(f"<div class=meta><span class=tag>#{esc(r['id'])}</span><span>{esc(r['created_at'][:19])}</span></div>")
            out.append(f"<div class=body>{esc(r['text'])}</div>")
            if r.get("impact_assessment"):
                out.append(
                    f"<div class=body style='color:#9aa3b0;margin-top:8px;font-size:13px'>"
                    f"<strong>Impact:</strong> {esc(r['impact_assessment'])}</div>"
                )
            out.append(
                f"<form method=post action='/requirement'>"
                f"<input type=hidden name=req_id value='{esc(r['id'])}'>"
                f"<button class=ok name=decision value=approved>Approve</button>"
                f"<button class=no name=decision value=rejected>Reject</button></form>"
            )
            out.append("</div>")
    else:
        out.append("<p class=empty>None pending.</p>")
    out.append("</section>")

    # ---- baselines --------------------------------------------------------
    out.append("<section><h2>Baselines</h2><table>")
    out.append("<tr><th>id</th><th>version</th><th>status</th><th>assurance sign-off</th><th>created</th></tr>")
    for b in baselines[:12]:
        try:
            stamped = storage.is_baseline_stamped(b["id"])
        except Exception:
            stamped = False
        badge = (
            "<span class='tag green'>stamped</span>"
            if stamped
            else "<span class=tag>0/3 offices</span>"
        )
        out.append(
            f"<tr><td>{esc(b['id'])}</td><td>{esc(b['version'])}</td><td>{esc(b['status'])}</td>"
            f"<td>{badge}</td><td>{esc(b['created_at'][:19])}</td></tr>"
        )
    out.append("</table>")
    out.append(
        "<p class=empty style='margin-top:8px'>No baseline can be stamped until the three Assurance Gate "
        "agents (Review &amp; Critic, Safety &amp; Risk, Regulatory) exist — none are built yet.</p>"
    )
    out.append("</section>")

    # ---- requirement status mix -------------------------------------------
    out.append("<section><h2>Requirement status</h2><div class=cards>")
    for status, n in sorted(req_status.items()):
        out.append(f"<div class=card><div class=n>{esc(n)}</div><div class=l>{esc(status)}</div></div>")
    out.append("</div></section>")

    # ---- activity ---------------------------------------------------------
    out.append("<section><h2>Recent activity</h2><table>")
    out.append("<tr><th>when</th><th>agent</th><th>event</th><th>detail</th></tr>")
    for e in events[:30]:
        detail = e["description"]
        out.append(
            f"<tr><td>{esc(e['timestamp'][:19])}</td><td>{esc(e['agent'])}</td>"
            f"<td>{esc(e['event_type'])}</td>"
            f"<td>{esc(detail[:190])}{'…' if len(detail) > 190 else ''}</td></tr>"
        )
    out.append("</table></section>")

    return page("live from D1", "".join(out))


@app.route("/answer", methods=["POST"])
def answer():
    question = request.form["question"]
    decision = request.form["answer"].strip()
    if decision:
        # Logged as Saiyam, not as an agent — the audit trail must show that a
        # human made this call, not the ecosystem deciding for itself.
        storage.log_event("Saiyam", "decision_answer", f"RE: {question} || ANSWER: {decision}")
    return redirect(url_for("index"))


@app.route("/requirement", methods=["POST"])
def requirement():
    req_id = int(request.form["req_id"])
    decision = request.form["decision"]
    if decision in {"approved", "rejected"}:
        storage.update_requirement_status(req_id, decision)
        storage.log_event("Saiyam", "requirement_decision", f"requirement #{req_id} -> {decision}")
    return redirect(url_for("index"))


if __name__ == "__main__":
    print("Dashboard → http://127.0.0.1:5000   (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False)
