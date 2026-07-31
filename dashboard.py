"""Oversight dashboard — see what the agent ecosystem is doing, and intervene.

CLAUDE.md defines a "medium-loose hybrid" oversight tier: batched decision
requests and milestone digests reach Saiyam, safety/regulatory/irreversible-
cost issues always surface immediately, and day-to-day division work stays
internal. All of that already gets written to D1 — this is the human-facing
window onto it.

This is deliberately read-mostly. The two things it can actually change are
the two decisions CLAUDE.md reserves for Saiyam:
  - answering a queued decision request
  - approving or rejecting a proposed requirement

It does NOT let you edit baselines, configurations, or knowledge-base entries,
create agents, or trigger agent runs. Those belong to the agents/CLI by the
founding principle and by cost/safety — a dashboard button that silently
spent real money or let a human quietly rewrite agent output would undermine
the whole arrangement. Every number on this page is read live from D1 or
Vectorize; nothing here is mocked or hand-typed.

Run:  python3 dashboard.py     then open http://127.0.0.1:5000
      (or PORT=8080 python3 dashboard.py to use a different port)
"""

import html
import json
import os
from collections import Counter
from datetime import datetime

from flask import Flask, redirect, request, url_for

import storage

app = Flask(__name__)

# Event types that must surface immediately per CLAUDE.md's standing hard rule.
URGENT_EVENTS = {"escalation"}

# The 19 fixed agents per CLAUDE.md's roster (division, display name, script
# filename under agents/ or None if unbuilt, AGENT_NAME string used in the
# audit log's `agent` column or None if unbuilt). Hand-maintained — there is
# no other single source of truth to derive it from automatically.
ROSTER = [
    ("Orchestrator", "Orchestrator", "orchestrator_agent.py", "Orchestrator"),
    ("Knowledge Base", "Foundational Research Agent", "foundational_research_agent.py", "FoundationalResearchAgent"),
    ("Knowledge Base", "KB Manager", "kb_manager_agent.py", "KBManager"),
    ("Innovation", "Innovation Validator", "innovation_validator_agent.py", "InnovationValidator"),
    ("Concurrent Engineering Cluster", "Systems Engineer", "systems_engineer_agent.py", "SystemsEngineer"),
    ("Concurrent Engineering Cluster", "Configuration Synthesis Lead", "configuration_synthesis_lead_agent.py", "ConfigurationSynthesisLead"),
    ("Concurrent Engineering Cluster", "Math & Physics Engine", "math_physics_engine_agent.py", "MathPhysicsEngine"),
    ("Concurrent Engineering Cluster", "Airframe Engineer", "airframe_engineer_agent.py", "AirframeEngineer"),
    ("Concurrent Engineering Cluster", "Propulsion & Power Engineer", "propulsion_power_engineer_agent.py", "PropulsionPowerEngineer"),
    ("Concurrent Engineering Cluster", "Chief Integration Agent", "chief_integration_agent.py", "ChiefIntegrationAgent"),
    ("Concurrent Engineering Cluster", "Software Engineer", "software_engineer_agent.py", "SoftwareEngineer"),
    ("Concurrent Engineering Cluster", "Design Realization Agent", "design_realization_agent.py", "DesignRealizationAgent"),
    ("Manufacturing", "Manufacturing Manager", None, None),
    ("Verification & Validation", "Simulation Agent", "simulation_agent.py", "SimulationAgent"),
    ("Verification & Validation", "Physical Testing Agent", None, None),
    ("Assurance Gate", "Review & Critic", None, None),
    ("Assurance Gate", "Safety & Risk", None, None),
    ("Assurance Gate", "Regulatory", None, None),
    ("Literature", "Literature Agent", None, None),
]

ICONS = {
    "overview": '<svg viewBox="0 0 20 20" fill="none"><rect x="2.5" y="2.5" width="6.5" height="6.5" rx="1.6" stroke="currentColor" stroke-width="1.6"/><rect x="11" y="2.5" width="6.5" height="6.5" rx="1.6" stroke="currentColor" stroke-width="1.6"/><rect x="2.5" y="11" width="6.5" height="6.5" rx="1.6" stroke="currentColor" stroke-width="1.6"/><rect x="11" y="11" width="6.5" height="6.5" rx="1.6" stroke="currentColor" stroke-width="1.6"/></svg>',
    "agents": '<svg viewBox="0 0 20 20" fill="none"><rect x="4" y="6.5" width="12" height="9" rx="2.2" stroke="currentColor" stroke-width="1.6"/><path d="M10 6.5V3.5M7.2 3.5h5.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="7.6" cy="11" r="1.1" fill="currentColor"/><circle cx="12.4" cy="11" r="1.1" fill="currentColor"/><path d="M7.5 13.6h5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
    "decisions": '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.2" stroke="currentColor" stroke-width="1.6"/><path d="M7.9 7.7c.2-1 1-1.7 2.1-1.7 1.2 0 2.1.8 2.1 1.9 0 1.6-2 1.4-2.1 3.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="10" cy="13.6" r=".95" fill="currentColor"/></svg>',
    "requirements": '<svg viewBox="0 0 20 20" fill="none"><rect x="3.5" y="3" width="13" height="14" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M6.5 8.2l1.6 1.6 2.8-2.9M6.5 13.2h6.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "baselines": '<svg viewBox="0 0 20 20" fill="none"><path d="M10 2.8l7 3.6-7 3.6-7-3.6 7-3.6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M3 10l7 3.6 7-3.6M3 13.6l7 3.6 7-3.6" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>',
    "kb": '<svg viewBox="0 0 20 20" fill="none"><path d="M4 4.3c1.6-.9 3.6-.9 6 0v11.4c-2.4-.9-4.4-.9-6 0V4.3zM16 4.3c-1.6-.9-3.6-.9-6 0v11.4c2.4-.9 4.4-.9 6 0V4.3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    "logs": '<svg viewBox="0 0 20 20" fill="none"><path d="M3 10.5h3.4l1.6-4.3 2.6 8 1.7-4.9H17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "search": '<svg viewBox="0 0 20 20" fill="none"><circle cx="8.8" cy="8.8" r="5.3" stroke="currentColor" stroke-width="1.6"/><path d="M16.2 16.2l-3.5-3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    "bell": '<svg viewBox="0 0 20 20" fill="none"><path d="M5.5 8.6a4.5 4.5 0 0 1 9 0c0 3.6 1.1 4.6 1.1 4.6H4.4s1.1-1 1.1-4.6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8.3 15.8a1.8 1.8 0 0 0 3.4 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    "sun": '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="3.4" stroke="currentColor" stroke-width="1.6"/><path d="M10 2.6v1.7M10 15.7v1.7M17.4 10h-1.7M4.3 10H2.6M15.2 4.8l-1.2 1.2M6 14l-1.2 1.2M15.2 15.2L14 14M6 6 4.8 4.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    "moon": '<svg viewBox="0 0 20 20" fill="none"><path d="M16.5 12.3A6.8 6.8 0 1 1 7.7 3.5a5.4 5.4 0 0 0 8.8 8.8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    "collapse": '<svg viewBox="0 0 20 20" fill="none"><rect x="2.8" y="3.2" width="14.4" height="13.6" rx="2.4" stroke="currentColor" stroke-width="1.5"/><path d="M8 3.2v13.6" stroke="currentColor" stroke-width="1.5"/><path d="M5.6 8l-1.4 2 1.4 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "command": '<svg viewBox="0 0 20 20" fill="none"><path d="M7 6.2A1.8 1.8 0 1 1 8.8 8H6.2A1.8 1.8 0 1 1 8 6.2v7.6A1.8 1.8 0 1 1 6.2 12h7.6a1.8 1.8 0 1 1-1.8 1.8V6.2A1.8 1.8 0 1 1 13.8 8H6.2" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    "spark": '<svg viewBox="0 0 20 20" fill="none"><path d="M10 2.5l1.6 4.9 5.1.2-4.1 3.1 1.6 4.9-4.2-3-4.2 3 1.6-4.9-4.1-3.1 5.1-.2z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
    "chevron": '<svg viewBox="0 0 20 20" fill="none"><path d="M7.5 5l5 5-5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "clock": '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.2" stroke="currentColor" stroke-width="1.5"/><path d="M10 6v4.2l3 1.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}

NAV = [
    ("overview", "Overview", "overview"),
    ("agents", "Agents", "agents"),
    ("decisions", "Decisions", "decisions"),
    ("requirements", "Requirements", "requirements"),
    ("baselines", "Baselines", "baselines"),
    ("kb", "Knowledge Base", "kb"),
    ("logs", "Logs", "logs"),
]

STYLE = """
:root {
  --bg:#FAFAF8; --bg-subtle:#F2F1ED; --surface:#FFFFFF; --surface-hover:#FCFCFB;
  --border:#E8E6E1; --border-strong:#D9D6CF;
  --text:#191916; --text-secondary:#6B6963; --text-muted:#9C9A92;
  --accent:#3355E0; --accent-hover:#2846C9; --accent-soft:#EBEFFD; --accent-text:#2A44C4;
  --success:#187A56; --success-soft:#E6F5EE;
  --warning:#A96A0B; --warning-soft:#FBF0DB;
  --danger:#C13A2E; --danger-soft:#FBEAE8;
  --shadow-sm:0 1px 2px rgba(25,25,20,.05);
  --shadow-md:0 6px 16px rgba(25,25,20,.06);
  --shadow-lg:0 20px 48px rgba(25,25,20,.12);
  --radius-sm:8px; --radius-md:12px; --radius-lg:20px;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --ease:cubic-bezier(.16,1,.3,1);
  color-scheme: light;
}
:root[data-theme="dark"] {
  --bg:#0A0B0D; --bg-subtle:#0F1113; --surface:#151719; --surface-hover:#1A1D20;
  --border:#232629; --border-strong:#2E3236;
  --text:#F1F0EC; --text-secondary:#9B9994; --text-muted:#68665F;
  --accent:#6E86FF; --accent-hover:#8298FF; --accent-soft:#171B33; --accent-text:#AEBBFF;
  --success:#33C088; --success-soft:#0E271D;
  --warning:#E1A73F; --warning-soft:#2C2210;
  --danger:#E9776C; --danger-soft:#301715;
  --shadow-sm:0 1px 2px rgba(0,0,0,.35);
  --shadow-md:0 6px 20px rgba(0,0,0,.4);
  --shadow-lg:0 24px 56px rgba(0,0,0,.55);
  color-scheme: dark;
}
* { box-sizing:border-box; }
html,body { margin:0; padding:0; }
body {
  background:var(--bg); color:var(--text); font-family:var(--sans);
  font-size:14px; line-height:1.5; -webkit-font-smoothing:antialiased;
}
a { color:var(--accent); text-decoration:none; }
.mono { font-family:var(--mono); font-variant-numeric:tabular-nums; }

/* ---------- shell / layout ---------- */
.shell { display:grid; grid-template-columns:248px 1fr; min-height:100vh; }
.shell.collapsed { grid-template-columns:72px 1fr; }
@media (max-width:880px){ .shell{ grid-template-columns:1fr; } }

.sidebar {
  background:var(--bg); border-right:1px solid var(--border);
  padding:22px 10px; display:flex; flex-direction:column; gap:1px;
  position:sticky; top:0; height:100vh; overflow-y:auto;
  transition:width .24s var(--ease);
}
@media (max-width:880px){
  .sidebar{
    position:fixed; z-index:40; width:248px; left:0; top:0;
    transform:translateX(-100%); transition:transform .22s ease; box-shadow:var(--shadow-lg);
  }
  .shell.mobile-nav-open .sidebar{ transform:translateX(0); }
}
.sidebar-top{ display:flex; align-items:center; justify-content:space-between; padding:2px 8px 28px; }
.brand{ display:flex; align-items:center; gap:9px; min-width:0; }
.brand .mark{
  width:22px; height:22px; border-radius:6px; flex-shrink:0;
  background:var(--text);
  display:flex; align-items:center; justify-content:center; color:var(--bg); font-weight:700; font-size:11px;
}
.brand .text{ min-width:0; overflow:hidden; }
.brand .name{ font-weight:600; font-size:13px; letter-spacing:-.01em; white-space:nowrap; color:var(--text); }
.shell.collapsed .brand .text{ display:none; }

.icon-btn{
  width:28px; height:28px; border-radius:7px; border:1px solid transparent; background:none;
  color:var(--text-muted); display:flex; align-items:center; justify-content:center; cursor:pointer;
  transition:background .15s ease,color .15s ease,border-color .15s ease; flex-shrink:0;
}
.icon-btn:hover{ background:var(--bg-subtle); color:var(--text); border-color:var(--border); }
.icon-btn svg{ width:16px; height:16px; }
.shell.collapsed #sidebarToggle svg{ transform:rotate(180deg); }

.nav-item{
  display:flex; align-items:center; gap:11px; padding:7px 10px 7px 12px; margin:0 -2px; border-radius:8px;
  color:var(--text-muted); font-size:13px; font-weight:500; cursor:pointer;
  transition:background .16s var(--ease),color .16s var(--ease); white-space:nowrap; user-select:none;
  position:relative;
}
.nav-item::before{
  content:""; position:absolute; left:-2px; top:20%; bottom:20%; width:2px; border-radius:2px;
  background:var(--text); opacity:0; transition:opacity .16s var(--ease);
}
.nav-item:hover{ color:var(--text); }
.nav-item.active{ color:var(--text); font-weight:600; }
.nav-item.active::before{ opacity:1; }
.nav-item svg{ width:16px; height:16px; flex-shrink:0; opacity:.85; }
.nav-item .label{ overflow:hidden; text-overflow:ellipsis; }
.nav-item .badge{
  margin-left:auto; color:var(--text-muted); font-size:11px; font-weight:600; font-family:var(--mono);
  flex-shrink:0;
}
.nav-item.active .badge{ color:var(--accent); }
.shell.collapsed .nav-item .label,.shell.collapsed .nav-item .badge{ display:none; }
.shell.collapsed .nav-item{ justify-content:center; }

/* ---------- topbar ---------- */
.topbar{
  position:sticky; top:0; z-index:20; height:60px; display:flex; align-items:center; gap:12px;
  padding:0 24px; background:color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter:blur(10px); border-bottom:1px solid var(--border);
}
.hamburger{ display:none; }
@media (max-width:880px){ .hamburger{ display:flex; } }
.search-wrap{
  flex:1; max-width:440px; position:relative; display:flex; align-items:center;
}
.search-wrap svg{ position:absolute; left:11px; width:15px; height:15px; color:var(--text-muted); pointer-events:none; }
.search-wrap input{
  width:100%; padding:8px 44px 8px 34px; border-radius:var(--radius-sm); border:1px solid var(--border);
  background:var(--bg-subtle); color:var(--text); font-size:13px; font-family:var(--sans);
  transition:border-color .15s ease,background .15s ease,box-shadow .15s ease;
}
.search-wrap input:focus{ outline:none; border-color:var(--accent); background:var(--surface); box-shadow:0 0 0 3px var(--accent-soft); }
.search-wrap kbd{
  position:absolute; right:9px; font-family:var(--mono); font-size:10.5px; color:var(--text-muted);
  background:var(--surface); border:1px solid var(--border); border-radius:5px; padding:1.5px 5px;
}
.topbar-right{ margin-left:auto; display:flex; align-items:center; gap:8px; }
.workspace-chip{
  display:flex; align-items:center; gap:7px; padding:5px 10px 5px 6px; border-radius:20px;
  border:1px solid var(--border); font-size:12.5px; color:var(--text-secondary); font-weight:500;
}
.workspace-chip .dot{ width:7px; height:7px; border-radius:50%; background:var(--success); box-shadow:0 0 0 3px var(--success-soft); }
.bell-wrap{ position:relative; }
.bell-wrap .count{
  position:absolute; top:-3px; right:-3px; background:var(--danger); color:#fff; font-size:9.5px;
  font-weight:700; min-width:14px; height:14px; border-radius:20px; display:flex; align-items:center;
  justify-content:center; padding:0 3px; border:2px solid var(--bg);
}
.avatar{
  width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#3355E0,#84A0FF);
  color:#fff; font-size:12px; font-weight:700; display:flex; align-items:center; justify-content:center;
}

/* ---------- main / pages ---------- */
main{ padding:28px 28px 64px; max-width:1360px; margin:0 auto; }
.page{ display:none; }
.page.active{ display:block; animation:fadeIn .28s ease; }
@keyframes fadeIn{ from{ opacity:0; transform:translateY(4px);} to{ opacity:1; transform:none; } }
@keyframes fadeInUp{ from{ opacity:0; transform:translateY(10px);} to{ opacity:1; transform:none; } }

.hero{ margin-bottom:8px; }
.hero .greeting{ font-size:clamp(26px,3vw,34px); font-weight:600; letter-spacing:-.025em; margin:0 0 10px; }
.hero .status-line{ display:flex; align-items:center; gap:9px; color:var(--text-muted); font-size:13.5px; }
.status-dot{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.status-dot.ok{ background:var(--success); }
.status-dot.warn{ background:var(--warning); }
.status-dot.bad{ background:var(--danger); }

h2.section-title{
  font-size:11.5px; text-transform:uppercase; letter-spacing:.08em; font-weight:600;
  color:var(--text-muted); margin:0 0 14px;
}
.page-header{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:24px; }
.page-header h1{ font-size:26px; font-weight:600; letter-spacing:-.02em; margin:0; }
.page-header p{ margin:5px 0 0; font-size:13.5px; color:var(--text-muted); }

/* ---------- bento hero (overview focal point) ---------- */
.bento{
  display:grid; grid-template-columns:1.7fr 1fr; gap:1px; background:var(--border);
  border-radius:var(--radius-lg); overflow:hidden; margin:28px 0 44px; box-shadow:var(--shadow-sm);
}
@media (max-width:760px){ .bento{ grid-template-columns:1fr; } }
.bento-primary{ background:var(--surface); padding:36px 38px 30px; display:flex; flex-direction:column; }
.eyebrow{ font-size:11px; font-weight:650; letter-spacing:.09em; text-transform:uppercase; color:var(--text-muted); }
.bento-number{ font-family:var(--mono); font-size:clamp(46px,6vw,68px); font-weight:600; letter-spacing:-.035em; margin:12px 0 2px; line-height:1; }
.bento-spark-wrap{ margin:22px 0 6px; }
.bento-spark-wrap svg{ width:100%; height:64px; display:block; }
.bento-caption{ font-size:12.5px; color:var(--text-muted); margin-top:auto; padding-top:20px; }
.bento-side{ background:var(--surface); display:flex; flex-direction:column; }
.side-row{
  padding:20px 24px; display:flex; align-items:center; justify-content:space-between; gap:12px;
  border-bottom:1px solid var(--border); transition:background .15s var(--ease);
}
.side-row:last-child{ border-bottom:none; }
.side-row:hover{ background:var(--surface-hover); }
.side-text{ display:flex; flex-direction:column; gap:5px; }
.side-label{ font-size:11.5px; color:var(--text-muted); }
.side-value{ font-family:var(--mono); font-size:23px; font-weight:600; letter-spacing:-.015em; }
.side-value.accent{ color:var(--accent); }
.spark{ display:block; color:var(--accent); }

/* ---------- generic card / badge / button ---------- */
.card{
  background:var(--surface); border:1px solid transparent; border-radius:var(--radius-md);
  padding:20px 22px; margin-bottom:10px; transition:box-shadow .2s var(--ease),transform .2s var(--ease);
  box-shadow:var(--shadow-sm);
}
.card:hover{ box-shadow:var(--shadow-md); }
.card.urgent{ border-left:2px solid var(--danger); border-radius:6px var(--radius-md) var(--radius-md) 6px; }
.card.action{ border-left:2px solid var(--accent); border-radius:6px var(--radius-md) var(--radius-md) 6px; }
.card-meta{ display:flex; align-items:center; gap:10px; font-size:11.5px; color:var(--text-muted); margin-bottom:9px; flex-wrap:wrap; }
.card-body{ white-space:pre-wrap; word-break:break-word; font-size:14px; color:var(--text); line-height:1.65; }
.card-sub{ color:var(--text-secondary); font-size:12.5px; margin-top:9px; line-height:1.6; }

.badge{
  display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:600; padding:2px 0;
  letter-spacing:.01em; white-space:nowrap; color:var(--text-muted);
}
.badge.red{ color:var(--danger); }
.badge.blue{ color:var(--accent-text); }
.badge.green{ color:var(--success); }
.badge.amber{ color:var(--warning); }
.badge.neutral{ color:var(--text-muted); }
.badge.red::before,.badge.blue::before,.badge.green::before,.badge.amber::before{
  content:""; width:5px; height:5px; border-radius:50%; background:currentColor; flex-shrink:0;
}

.btn{
  display:inline-flex; align-items:center; gap:6px; border:1px solid var(--border); background:var(--surface);
  color:var(--text); border-radius:var(--radius-sm); padding:8px 14px; font-size:13px; font-weight:600;
  font-family:var(--sans); cursor:pointer; transition:background .15s ease,border-color .15s ease,transform .12s ease;
}
.btn:hover{ background:var(--bg-subtle); }
.btn:active{ transform:scale(.97); }
.btn.primary{ background:var(--accent); border-color:var(--accent); color:#fff; }
.btn.primary:hover{ background:var(--accent-hover); }
.btn.ok{ background:var(--success); border-color:var(--success); color:#fff; }
.btn.no{ background:transparent; border-color:var(--border); color:var(--danger); }
.btn.no:hover{ background:var(--danger-soft); }

.field{
  flex:1; min-width:240px; padding:9px 12px; border-radius:var(--radius-sm); border:1px solid var(--border);
  background:var(--bg-subtle); color:var(--text); font-size:13.5px; font-family:var(--sans);
  transition:border-color .15s ease,background .15s ease,box-shadow .15s ease;
}
.field:focus{ outline:none; border-color:var(--accent); background:var(--surface); box-shadow:0 0 0 3px var(--accent-soft); }
form.inline-form{ margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }

.empty-state{
  display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center;
  padding:40px 20px; color:var(--text-muted); gap:8px;
}
.empty-state svg{ width:28px; height:28px; opacity:.6; }
.empty-state .t{ font-size:13px; color:var(--text-secondary); max-width:360px; }

/* ---------- agent roster ---------- */
.division-label{ font-size:11px; font-weight:600; color:var(--text-muted); margin:32px 0 12px; text-transform:uppercase; letter-spacing:.08em; }
.division-label:first-child{ margin-top:0; }
.agent-grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(266px,1fr)); gap:1px; background:var(--border); border-radius:var(--radius-md); overflow:hidden; }
.agent-card{
  background:var(--surface); padding:18px 20px;
  transition:background .18s var(--ease);
  opacity:0; animation:fadeInUp .4s var(--ease) forwards;
}
.agent-card:hover{ background:var(--surface-hover); }
.agent-card.unbuilt{ opacity:.4; }
.agent-card.unbuilt:hover{ opacity:.65; }
.agent-head{ display:flex; align-items:flex-start; justify-content:space-between; gap:8px; margin-bottom:6px; }
.agent-name{ font-size:14.5px; font-weight:600; letter-spacing:-.01em; }
.dot{ width:6px; height:6px; border-radius:50%; flex-shrink:0; margin-top:6px; }
.dot.green{ background:var(--success); }
.dot.amber{ background:var(--warning); }
.dot.red{ background:var(--danger); }
.dot.grey{ background:var(--border-strong); }
.agent-out{
  font-size:12.5px; color:var(--text-secondary); line-height:1.6; margin-top:2px; cursor:pointer;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.agent-out.expanded{ -webkit-line-clamp:unset; }
.agent-foot{ display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:14px; font-size:11px; color:var(--text-muted); }

/* ---------- table ---------- */
table{ width:100%; border-collapse:collapse; font-size:13px; }
th,td{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:top; }
th{ color:var(--text-muted); font-weight:650; font-size:10.5px; text-transform:uppercase; letter-spacing:.06em; }
tbody tr{ transition:background .12s ease; }
tbody tr:hover{ background:var(--bg-subtle); }
.table-card{ background:var(--surface); border-radius:var(--radius-md); padding:6px 18px; overflow-x:auto; box-shadow:var(--shadow-sm); }

/* ---------- logs / timeline ---------- */
.filter-chips{ display:flex; gap:7px; flex-wrap:wrap; margin-bottom:16px; }
.chip{
  padding:5.5px 12px; border-radius:20px; border:1px solid var(--border); background:var(--surface);
  font-size:12px; font-weight:600; color:var(--text-secondary); cursor:pointer; transition:all .15s ease;
}
.chip:hover{ border-color:var(--border-strong); }
.chip.active{ background:var(--accent); border-color:var(--accent); color:#fff; }
.timeline{ position:relative; padding-left:22px; }
.timeline::before{ content:""; position:absolute; left:5px; top:6px; bottom:6px; width:1.5px; background:var(--border); }
.t-row{ position:relative; padding:0 0 18px; }
.t-row::before{
  content:""; position:absolute; left:-22px; top:4px; width:9px; height:9px; border-radius:50%;
  background:var(--surface); border:2px solid var(--text-muted);
}
.t-row.red::before{ border-color:var(--danger); }
.t-row.blue::before{ border-color:var(--accent); }
.t-row.grey::before{ border-color:var(--border-strong); }
.t-head{ display:flex; align-items:center; gap:9px; font-size:12px; color:var(--text-muted); margin-bottom:3px; }
.t-body{ font-size:13px; color:var(--text); line-height:1.55; }

/* ---------- knowledge base ---------- */
.kb-list{ display:flex; flex-direction:column; gap:1px; background:var(--border); border-radius:var(--radius-md); overflow:hidden; }
.kb-item{ background:var(--surface); padding:15px 18px; transition:background .15s var(--ease); }
.kb-item:hover{ background:var(--surface-hover); }
.kb-id{ font-family:var(--mono); font-size:11px; color:var(--text-muted); margin-bottom:5px; }
.kb-text{ font-size:13px; color:var(--text); line-height:1.55; }
.skeleton{ background:linear-gradient(90deg,var(--bg-subtle) 25%,var(--border) 37%,var(--bg-subtle) 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; border-radius:8px; height:56px; margin-bottom:8px; }
@keyframes shimmer{ 0%{ background-position:100% 0;} 100%{ background-position:-100% 0;} }

/* ---------- command palette ---------- */
.palette-backdrop{
  position:fixed; inset:0; background:rgba(10,10,8,.45); backdrop-filter:blur(3px); z-index:100;
  display:none; align-items:flex-start; justify-content:center; padding-top:14vh;
}
.palette-backdrop.open{ display:flex; animation:fadeIn .15s ease; }
.palette{
  width:min(560px,92vw); background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  box-shadow:var(--shadow-lg); overflow:hidden;
}
.palette input{
  width:100%; border:none; border-bottom:1px solid var(--border); padding:16px 18px; font-size:15px;
  background:transparent; color:var(--text); font-family:var(--sans);
}
.palette input:focus{ outline:none; }
.palette-results{ max-height:340px; overflow-y:auto; padding:6px; }
.palette-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:var(--radius-sm); cursor:pointer; font-size:13.5px; }
.palette-item.sel{ background:var(--accent-soft); color:var(--accent-text); }
.palette-item .hint{ margin-left:auto; font-size:11px; color:var(--text-muted); }

.nav-item,.chip,.palette-item{ font-family:var(--sans); text-align:left; appearance:none; -webkit-appearance:none; margin:0; }
.nav-item,.palette-item{ width:100%; background:none; border:none; font-size:inherit; color:inherit; }
.nav-item:focus-visible,.chip:focus-visible,.palette-item:focus-visible,.icon-btn:focus-visible,.btn:focus-visible{
  outline:2px solid var(--accent); outline-offset:2px;
}
::-webkit-scrollbar{ width:9px; height:9px; }
::-webkit-scrollbar-thumb{ background:var(--border-strong); border-radius:20px; }
::-webkit-scrollbar-track{ background:transparent; }
"""

SCRIPT = """
(function(){
  var root = document.documentElement;
  var saved = localStorage.getItem('theme');
  var theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  root.setAttribute('data-theme', theme);
})();
document.addEventListener('DOMContentLoaded', function(){
  var shell = document.getElementById('shell');

  // theme toggle
  function setTheme(t){
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
    document.getElementById('themeIconSun').style.display = t === 'dark' ? 'flex' : 'none';
    document.getElementById('themeIconMoon').style.display = t === 'dark' ? 'none' : 'flex';
  }
  setTheme(document.documentElement.getAttribute('data-theme') || 'light');
  document.getElementById('themeToggle').addEventListener('click', function(){
    var cur = document.documentElement.getAttribute('data-theme');
    setTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // sidebar collapse (desktop) / off-canvas (mobile)
  var collapsed = localStorage.getItem('sidebarCollapsed') === '1';
  if (collapsed) shell.classList.add('collapsed');
  document.getElementById('sidebarToggle').addEventListener('click', function(){
    shell.classList.toggle('collapsed');
    localStorage.setItem('sidebarCollapsed', shell.classList.contains('collapsed') ? '1' : '0');
  });
  var hamburger = document.getElementById('hamburger');
  if (hamburger) hamburger.addEventListener('click', function(){ shell.classList.toggle('mobile-nav-open'); });

  // section navigation
  function go(section){
    document.querySelectorAll('.page').forEach(function(p){ p.classList.toggle('active', p.id === 'page-' + section); });
    document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.toggle('active', n.dataset.section === section); });
    shell.classList.remove('mobile-nav-open');
    if (section === 'kb') loadKb('');
    history.replaceState(null, '', '#' + section);
  }
  document.querySelectorAll('.nav-item').forEach(function(n){
    n.addEventListener('click', function(){ go(n.dataset.section); });
  });
  go((location.hash || '#overview').slice(1));

  // animated metric counters
  document.querySelectorAll('[data-count]').forEach(function(el){
    var target = parseFloat(el.dataset.count);
    var prefix = el.dataset.prefix || '';
    var suffix = el.dataset.suffix || '';
    var decimals = parseInt(el.dataset.decimals || '0', 10);
    if (isNaN(target)) return;
    var start = performance.now(), dur = 700;
    function frame(now){
      var p = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });

  // agent card expand
  document.querySelectorAll('.agent-out').forEach(function(el){
    el.addEventListener('click', function(){ el.classList.toggle('expanded'); });
  });

  // topbar search: filters cards/rows with data-search-text within the active page
  var searchInput = document.getElementById('topSearch');
  searchInput.addEventListener('input', function(){
    var q = searchInput.value.trim().toLowerCase();
    document.querySelectorAll('.page.active [data-search-text]').forEach(function(el){
      el.style.display = (!q || el.dataset.searchText.toLowerCase().indexOf(q) !== -1) ? '' : 'none';
    });
  });

  // log filter chips
  document.querySelectorAll('.chip[data-filter]').forEach(function(c){
    c.addEventListener('click', function(){
      document.querySelectorAll('.chip[data-filter]').forEach(function(x){ x.classList.remove('active'); });
      c.classList.add('active');
      var f = c.dataset.filter;
      document.querySelectorAll('#logTimeline .t-row').forEach(function(row){
        row.style.display = (f === 'all' || row.dataset.type === f) ? '' : 'none';
      });
    });
  });

  // knowledge base search (real, hits /kb)
  var kbBox = document.getElementById('kbResults');
  var kbInput = document.getElementById('kbSearch');
  var kbTimer = null;
  function loadKb(q){
    if (!kbBox) return;
    kbBox.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
    fetch('/kb?q=' + encodeURIComponent(q))
      .then(function(r){ return r.text(); })
      .then(function(html){ kbBox.innerHTML = html; })
      .catch(function(){ kbBox.innerHTML = '<div class="empty-state"><div class="t">Could not reach the knowledge base right now.</div></div>'; });
  }
  if (kbInput) kbInput.addEventListener('input', function(){
    clearTimeout(kbTimer);
    kbTimer = setTimeout(function(){ loadKb(kbInput.value.trim()); }, 320);
  });

  // command palette
  var paletteItems = window.__paletteItems || [];
  var backdrop = document.getElementById('paletteBackdrop');
  var pInput = document.getElementById('paletteInput');
  var pResults = document.getElementById('paletteResults');
  var selIdx = 0, filtered = paletteItems;

  function renderPalette(){
    pResults.innerHTML = '';
    filtered.forEach(function(item, i){
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'palette-item' + (i === selIdx ? ' sel' : '');
      btn.innerHTML = '<span>' + item.label + '</span><span class="hint">' + item.hint + '</span>';
      btn.addEventListener('click', function(){ go(item.section); closePalette(); });
      pResults.appendChild(btn);
    });
  }
  function openPalette(){
    backdrop.classList.add('open'); pInput.value = ''; filtered = paletteItems; selIdx = 0;
    renderPalette(); setTimeout(function(){ pInput.focus(); }, 10);
  }
  function closePalette(){ backdrop.classList.remove('open'); }
  document.getElementById('cmdBtn').addEventListener('click', openPalette);
  backdrop.addEventListener('click', function(e){ if (e.target === backdrop) closePalette(); });
  pInput.addEventListener('input', function(){
    var q = pInput.value.toLowerCase();
    filtered = paletteItems.filter(function(it){ return it.label.toLowerCase().indexOf(q) !== -1; });
    selIdx = 0; renderPalette();
  });
  document.addEventListener('keydown', function(e){
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'){ e.preventDefault(); openPalette(); return; }
    if (!backdrop.classList.contains('open')) return;
    if (e.key === 'Escape'){ closePalette(); }
    else if (e.key === 'ArrowDown'){ e.preventDefault(); selIdx = Math.min(filtered.length - 1, selIdx + 1); renderPalette(); }
    else if (e.key === 'ArrowUp'){ e.preventDefault(); selIdx = Math.max(0, selIdx - 1); renderPalette(); }
    else if (e.key === 'Enter' && filtered[selIdx]){ go(filtered[selIdx].section); closePalette(); }
  });
});
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _parse_flags(description: str) -> dict:
    """agent_end descriptions look like 'run_id=... turns=21 cost=$0.58
    is_error=False hit_turn_limit=False' — pull the key=value tokens back out."""
    out = {}
    for token in description.split():
        if "=" in token:
            key, _, val = token.partition("=")
            out[key] = val
    return out


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


def _sparkline(values, width=104, height=30, color="var(--accent)") -> str:
    """Minimal inline SVG sparkline from a REAL numeric series — no chart
    library, no fabricated data. Returns '' if there's nothing to show."""
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - lo) / span) * (height - 5) - 2.5
        pts.append(f"{x:.1f},{y:.1f}")
    line = " ".join(pts)
    area = f"0,{height} {line} {width},{height}"
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<polyline points="{area}" fill="{color}" opacity="0.12" stroke="none"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.75" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def _ring(pct: float, size: int = 36, stroke: float = 3) -> str:
    """Real-percentage radial progress ring — used for agents-built, not decoration."""
    r = (size - stroke) / 2
    c = 2 * 3.14159265 * r
    offset = c * (1 - max(0, min(100, pct)) / 100)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="var(--border-strong)" stroke-width="{stroke}"/>'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="var(--accent)" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-dasharray="{c:.2f}" stroke-dashoffset="{offset:.2f}" '
        f'transform="rotate(-90 {size / 2} {size / 2})"/></svg>'
    )


def _fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s}s" if s else f"{m}m"


def _run_durations(events) -> list:
    """Real per-run wall-clock time, paired from agent_start/agent_end
    timestamps sharing the same run_id. Nothing here is estimated."""
    start_ts, end_ts = {}, {}
    for e in events:
        rid = _parse_flags(e["description"]).get("run_id")
        if not rid:
            continue
        if e["event_type"] == "agent_start":
            start_ts[rid] = e["timestamp"]
        elif e["event_type"] == "agent_end":
            end_ts[rid] = e["timestamp"]
    durations = []
    for rid, s in start_ts.items():
        t = end_ts.get(rid)
        if not t:
            continue
        try:
            durations.append((datetime.fromisoformat(t) - datetime.fromisoformat(s)).total_seconds())
        except ValueError:
            continue
    return durations


def page(active_title: str, sections: dict, palette_items: list, open_decisions: int, escalations: int) -> str:
    nav_html = []
    for key, label, _ in NAV:
        badge = ""
        if key == "decisions" and open_decisions:
            badge = f'<span class="badge">{open_decisions}</span>'
        nav_html.append(
            f'<button type="button" class="nav-item" data-section="{key}">{ICONS[key]}<span class="label">{esc(label)}</span>{badge}</button>'
        )

    pages_html = "".join(
        f'<div class="page" id="page-{key}">{html_body}</div>' for key, html_body in sections.items()
    )

    palette_json = json.dumps(palette_items)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Electric Aircraft — Agent Oversight</title>
<style>{STYLE}</style>
</head>
<body>
<div class="shell" id="shell">
  <aside class="sidebar">
    <div class="sidebar-top">
      <div class="brand">
        <div class="mark">EA</div>
        <div class="text"><div class="name">Electric Aircraft</div></div>
      </div>
      <button class="icon-btn" id="sidebarToggle" title="Collapse sidebar">{ICONS['collapse']}</button>
    </div>
    {''.join(nav_html)}
  </aside>

  <div>
    <header class="topbar">
      <button class="icon-btn" id="hamburger">{ICONS['collapse']}</button>
      <div class="search-wrap">
        {ICONS['search']}
        <input id="topSearch" type="text" placeholder="Filter this page…">
      </div>
      <div class="topbar-right">
        <button class="icon-btn" id="cmdBtn" title="Command palette (⌘K)">{ICONS['command']}</button>
        <div class="bell-wrap">
          <button class="icon-btn" title="Escalations">{ICONS['bell']}</button>
          {f'<span class="count">{escalations}</span>' if escalations else ''}
        </div>
        <button class="icon-btn" id="themeToggle" title="Toggle theme">
          <span id="themeIconSun" style="display:flex">{ICONS['sun']}</span>
          <span id="themeIconMoon" style="display:none">{ICONS['moon']}</span>
        </button>
        <div class="workspace-chip"><span class="dot"></span>Electric Aircraft</div>
        <div class="avatar">S</div>
      </div>
    </header>
    <main>{pages_html}</main>
  </div>
</div>

<div class="palette-backdrop" id="paletteBackdrop">
  <div class="palette">
    <input id="paletteInput" placeholder="Jump to a section…" autocomplete="off">
    <div class="palette-results" id="paletteResults"></div>
  </div>
</div>

<script>window.__paletteItems = {palette_json};</script>
<script>{SCRIPT}</script>
</body>
</html>"""


@app.route("/")
def index():
    events = storage.get_audit_log(limit=500)
    baselines = storage.list_baselines(limit=40)
    requirements = storage.list_requirements(limit=200)

    try:
        kb_count = len(storage.list_kb_ids())
    except Exception:
        kb_count = None  # Vectorize has intermittent outages; never break the page over it

    runs = [e for e in events if e["event_type"] == "agent_end"]
    proposed = [r for r in requirements if r["status"] == "proposed"]
    req_status = Counter(r["status"] for r in requirements)
    answered = _answered_decision_ids(events)

    escalations = [e for e in events if e["event_type"] in URGENT_EVENTS]
    decisions = [e for e in events if e["event_type"] == "decision_request"]
    open_decisions = [d for d in decisions if _parse_kv(d["description"]).get("QUESTION", "") not in answered]

    # ---- real cost/run series, oldest -> newest, for sparklines & totals ----
    chrono_runs = list(reversed(runs))  # events is DESC; flip to chronological
    costs, cum_cost, cum_runs, running = [], [], [], 0.0
    for i, e in enumerate(chrono_runs):
        c = 0.0
        for tok in e["description"].split():
            if tok.startswith("cost=$"):
                try:
                    c = float(tok[6:])
                except ValueError:
                    pass
        costs.append(c)
        running += c
        cum_cost.append(round(running, 4))
        cum_runs.append(i + 1)
    total_cost = round(sum(costs), 4)

    now = datetime.now()
    recent_runs = 0
    recent_cost = 0.0
    for e, c in zip(chrono_runs, costs):
        try:
            ts = datetime.fromisoformat(e["timestamp"])
            if (now - ts.replace(tzinfo=None)).days <= 7:
                recent_runs += 1
                recent_cost += c
        except ValueError:
            pass

    error_flags = [_parse_flags(e["description"]) for e in runs]
    known = [f for f in error_flags if "is_error" in f]
    errored = [f for f in known if f.get("is_error") == "True"]
    success_rate = 100.0 * (1 - len(errored) / len(known)) if known else None

    durations = _run_durations(events)
    avg_runtime = sum(durations) / len(durations) if durations else None

    built_agents = [r for r in ROSTER if r[2]]

    hour = now.hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")

    if errored:
        status_class, status_text = "bad", f"{len(errored)} agent run(s) errored — see Agents"
    elif open_decisions or proposed:
        status_class, status_text = "warn", f"{len(open_decisions)} decision(s) and {len(proposed)} requirement(s) waiting on you"
    else:
        status_text = "All tracked runs clean, nothing waiting on you"
        status_class = "ok"

    out = {}

    # ============================================================ overview
    ov = []
    ov.append(f"""<div class="hero">
      <div class="greeting">{greeting}, Saiyam</div>
      <div class="status-line"><span class="status-dot {status_class}"></span>{esc(status_text)}</div>
    </div>""")

    # One obvious focal point — spend, since it's the number Saiyam asked about
    # unprompted last session — plus a compact real-data side column. Not six
    # equal cards: everything here supports the one large number.
    built_pct = round(100 * len(built_agents) / len(ROSTER))
    success_display = f"{success_rate:.0f}%" if success_rate is not None else "—"
    runtime_display = _fmt_duration(avg_runtime) if avg_runtime is not None else "—"

    ov.append(f"""<div class="bento">
      <div class="bento-primary">
        <div class="eyebrow">Total spend</div>
        <div class="bento-number" data-count="{total_cost}" data-prefix="$" data-decimals="2">$0.00</div>
        <div class="bento-spark-wrap">{_sparkline(cum_cost, width=520, height=64)}</div>
        <div class="bento-caption">${recent_cost:.2f} in the last 7 days · {recent_runs} of {len(runs)} runs · real Claude Agent SDK usage, not simulated</div>
      </div>
      <div class="bento-side">
        <div class="side-row"><div class="side-text"><span class="side-label">Run success</span></div><span class="side-value">{esc(success_display)}</span></div>
        <div class="side-row"><div class="side-text"><span class="side-label">Avg. run time</span></div><span class="side-value">{esc(runtime_display)}</span></div>
        <div class="side-row"><div class="side-text"><span class="side-label">Agents built</span><span style="font-family:var(--mono);font-size:12px;color:var(--text-muted)">{len(built_agents)} of {len(ROSTER)}</span></div>{_ring(built_pct)}</div>
        <div class="side-row"><div class="side-text"><span class="side-label">Awaiting you</span></div><span class="side-value{' accent' if open_decisions else ''}">{len(open_decisions)}</span></div>
      </div>
    </div>""")

    ov.append('<h2 class="section-title">Escalations — surfaced immediately</h2>')
    if escalations:
        for e in escalations[:6]:
            ov.append(f"""<div class="card urgent">
              <div class="card-meta"><span class="badge red">Escalation</span><span>{esc(e['agent'])}</span><span>{esc(e['timestamp'][:19])}</span></div>
              <div class="card-body">{esc(e['description'])}</div>
            </div>""")
    else:
        ov.append('<div class="card empty-state"><div class="t">None. Safety, regulatory and irreversible-cost issues appear here the moment they are raised.</div></div>')

    ov.append('<h2 class="section-title" style="margin-top:26px">Decisions waiting on you</h2>')
    if open_decisions:
        ov.append(f'<div class="card-sub" style="margin:-6px 0 12px">{len(open_decisions)} queued — full list on the Decisions page.</div>')
        for d in open_decisions[:2]:
            fields = _parse_kv(d["description"])
            ov.append(f"""<div class="card action"><div class="card-meta"><span class="badge blue">Decision</span><span>{esc(d['timestamp'][:19])}</span></div>
              <div class="card-body"><strong>{esc(fields.get('QUESTION', d['description']))}</strong></div></div>""")
    else:
        ov.append('<div class="card empty-state"><div class="t">Nothing queued.</div></div>')
    out["overview"] = "".join(ov)

    # ============================================================ agents
    known_clean_text = f'{len(known) - len(errored)}/{len(known)} tracked runs clean' if known else 'no runs have tracked error status yet'
    ag = ['<div class="page-header"><div><h1>Agent roster</h1><p>'
          f'{len(built_agents)}/19 built · {known_clean_text}'
          f'{" · " + str(len(errored)) + " with a real error" if errored else ""}. '
          "No agent script has a dedicated test file of its own — verification is each agent's real run history below."
          "</p></div></div>"]

    agent_ends_by_name, latest_output_by_name = {}, {}
    for e in events:
        if e["event_type"] == "agent_end":
            agent_ends_by_name.setdefault(e["agent"], []).append(e)
        elif e["event_type"] not in ("agent_start", "agent_end") and e["agent"] not in latest_output_by_name:
            latest_output_by_name[e["agent"]] = e

    last_division = None
    delay = 0
    for division, display_name, script, log_name in ROSTER:
        if division != last_division:
            if last_division is not None:
                ag.append("</div>")
            ag.append(f'<div class="division-label">{esc(division)}</div><div class="agent-grid">')
            last_division = division
        delay += 30
        if not script:
            ag.append(f"""<div class="agent-card unbuilt" data-search-text="{esc(display_name)} {esc(division)} not built" style="animation-delay:{delay}ms">
              <div class="agent-head"><span class="dot grey"></span><span class="agent-name">{esc(display_name)}</span></div>
              <div class="agent-out">Not built yet.</div>
              <div class="agent-foot"><span class="badge neutral">not built</span></div>
            </div>""")
            continue
        ends = agent_ends_by_name.get(log_name, [])
        if not ends:
            status_badge, dot = '<span class="badge amber">built, not run</span>', "amber"
            out_text, runs_n = "No run yet.", 0
        else:
            flagged = [(_parse_flags(e["description"]), e) for e in ends]
            errs = [e for f, e in flagged if f.get("is_error") == "True"]
            limits = [e for f, e in flagged if f.get("hit_turn_limit") == "True"]
            unknown_n = len([f for f, e in flagged if "is_error" not in f])
            if errs:
                status_badge, dot = f'<span class="badge red">{len(errs)} error run(s)</span>', "red"
            elif limits:
                status_badge, dot = '<span class="badge amber">hit turn limit</span>', "amber"
            else:
                status_badge, dot = '<span class="badge green">verified, no errors</span>', "green"
            if unknown_n:
                status_badge += f' <span class="badge neutral">+{unknown_n} pre-fix</span>'
            runs_n = len(ends)
            latest = latest_output_by_name.get(log_name)
            out_text = latest["description"] if latest else "Ran, but no output event found."
        ag.append(f"""<div class="agent-card" data-search-text="{esc(display_name)} {esc(division)} {esc(out_text)}" style="animation-delay:{delay}ms">
          <div class="agent-head"><span class="dot {dot}"></span><span class="agent-name">{esc(display_name)}</span></div>
          <div class="agent-out">{esc(out_text)}</div>
          <div class="agent-foot">{status_badge}<span style="margin-left:auto">{runs_n} run{'s' if runs_n != 1 else ''}</span></div>
        </div>""")
    ag.append("</div>")
    out["agents"] = "".join(ag)

    # ============================================================ decisions
    dec = ['<div class="page-header"><div><h1>Decisions</h1><p>Only Saiyam answers these — agents batch real forks here rather than deciding for themselves.</p></div></div>']
    if open_decisions:
        for d in open_decisions:
            fields = _parse_kv(d["description"])
            question = fields.get("QUESTION", d["description"])
            dec.append(f'<div class="card action" data-search-text="{esc(question)}">')
            dec.append(f'<div class="card-meta"><span class="badge blue">Decision</span><span>{esc(d["agent"])}</span><span>{esc(d["timestamp"][:19])}</span></div>')
            dec.append(f'<div class="card-body"><strong>{esc(question)}</strong></div>')
            if fields.get("CONTEXT"):
                dec.append(f'<div class="card-sub">{esc(fields["CONTEXT"])}</div>')
            try:
                for opt in json.loads(fields.get("OPTIONS", "[]")):
                    label = opt.get("label") or opt.get("option") or json.dumps(opt)
                    tag = opt.get("option") or opt.get("id") or "•"
                    dec.append(f'<div class="card-sub" style="margin-top:6px"><span class="badge neutral">{esc(tag)}</span> {esc(label)}</div>')
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
            dec.append(
                '<form method="post" action="/answer" class="inline-form">'
                f'<input type="hidden" name="question" value="{esc(question)}">'
                '<input class="field" type="text" name="answer" placeholder="Your decision — e.g. &quot;Option F: set 1.40 m absolute&quot;" required>'
                '<button class="btn primary" type="submit">Submit decision</button></form>'
            )
            dec.append("</div>")
    else:
        dec.append('<div class="card empty-state">' + ICONS["decisions"] + '<div class="t">Nothing queued right now.</div></div>')
    out["decisions"] = "".join(dec)

    # ============================================================ requirements
    req = [f'<div class="page-header"><div><h1>Requirements</h1><p>Agents propose; only Saiyam approves. {len(proposed)} awaiting review.</p></div></div>']
    req.append('<div style="display:flex;gap:40px;flex-wrap:wrap;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--border)">')
    for status, n in sorted(req_status.items()):
        req.append(
            f'<div><div style="font-family:var(--mono);font-size:28px;font-weight:600;letter-spacing:-.02em">{n}</div>'
            f'<div style="font-size:11.5px;color:var(--text-muted);margin-top:4px;text-transform:capitalize">{esc(status)}</div></div>'
        )
    req.append("</div>")
    if proposed:
        for r in proposed:
            req.append(f'<div class="card action" data-search-text="{esc(r["text"])}">')
            req.append(f'<div class="card-meta"><span class="badge neutral">#{esc(r["id"])}</span><span>{esc(r["created_at"][:19])}</span></div>')
            req.append(f'<div class="card-body">{esc(r["text"])}</div>')
            if r.get("impact_assessment"):
                req.append(f'<div class="card-sub"><strong>Impact:</strong> {esc(r["impact_assessment"])}</div>')
            req.append(
                '<form method="post" action="/requirement" class="inline-form">'
                f'<input type="hidden" name="req_id" value="{esc(r["id"])}">'
                '<button class="btn ok" name="decision" value="approved">Approve</button>'
                '<button class="btn no" name="decision" value="rejected">Reject</button></form>'
            )
            req.append("</div>")
    else:
        req.append('<div class="card empty-state">' + ICONS["requirements"] + '<div class="t">None pending.</div></div>')
    out["requirements"] = "".join(req)

    # ============================================================ baselines
    bl = ['<div class="page-header"><div><h1>Baselines</h1><p>No baseline can be stamped until all three Assurance Gate agents exist and sign off — none are built yet.</p></div></div>']
    bl.append('<div class="table-card"><table><tr><th>id</th><th>version</th><th>status</th><th>assurance sign-off</th><th>created</th></tr>')
    for b in baselines[:20]:
        try:
            stamped = storage.is_baseline_stamped(b["id"])
        except Exception:
            stamped = False
        badge = '<span class="badge green">stamped</span>' if stamped else '<span class="badge neutral">0/3 offices</span>'
        bl.append(f'<tr><td class="mono">{esc(b["id"])}</td><td class="mono">{esc(b["version"])}</td><td>{esc(b["status"])}</td><td>{badge}</td><td>{esc(b["created_at"][:19])}</td></tr>')
    bl.append("</table></div>")
    out["baselines"] = "".join(bl)

    # ============================================================ knowledge base
    kb = [f'<div class="page-header"><div><h1>Knowledge base</h1><p>{kb_count if kb_count is not None else "?"} entries in Vectorize. Search is real semantic search, not a client-side filter.</p></div></div>']
    kb.append('<div class="search-wrap" style="max-width:480px;margin-bottom:18px">' + ICONS["search"] + '<input id="kbSearch" class="field" style="padding-left:34px" placeholder="Search the knowledge base…"></div>')
    kb.append('<div class="kb-list" id="kbResults"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>')
    out["kb"] = "".join(kb)

    # ============================================================ logs
    lg = ['<div class="page-header"><div><h1>Activity log</h1><p>Every real event written to D1, newest first.</p></div></div>']
    lg.append('<div class="filter-chips">')
    for key, lbl in [("all", "All"), ("escalation", "Escalations"), ("decision_request", "Decisions"), ("decision_answer", "Answers"),
                      ("agent_start", "Agent start"), ("agent_end", "Agent end"), ("requirement_decision", "Requirements")]:
        lg.append(f'<button type="button" class="chip{" active" if key == "all" else ""}" data-filter="{key}">{lbl}</button>')
    lg.append("</div>")
    lg.append('<div class="timeline" id="logTimeline">')
    type_color = {"escalation": "red", "decision_request": "blue", "decision_answer": "blue"}
    for e in events[:120]:
        detail = e["description"]
        color = type_color.get(e["event_type"], "grey")
        lg.append(f"""<div class="t-row {color}" data-type="{esc(e['event_type'])}" data-search-text="{esc(e['agent'])} {esc(detail)}">
          <div class="t-head"><span class="badge neutral">{esc(e['event_type'])}</span><span>{esc(e['agent'])}</span><span>{esc(e['timestamp'][:19])}</span></div>
          <div class="t-body">{esc(detail[:280])}{'…' if len(detail) > 280 else ''}</div>
        </div>""")
    lg.append("</div>")
    out["logs"] = "".join(lg)

    palette_items = [{"label": label, "section": key, "hint": "section"} for key, label, _ in NAV]
    for division, display_name, script, log_name in ROSTER:
        if script:
            palette_items.append({"label": display_name, "section": "agents", "hint": division})

    return page("Overview", out, palette_items, len(open_decisions), len(escalations))


@app.route("/kb")
def kb_fragment():
    """Real KB browsing/search, loaded on demand so the main page load never
    pays Vectorize's per-ID fetch cost unless someone actually opens this tab."""
    q = request.args.get("q", "").strip()
    try:
        if q:
            matches = storage.search_kb(q, top_k=20)
            rows = [(m.get("id") or m.get("entry_id"), m.get("metadata", {}).get("text") or m.get("text") or "", m.get("score")) for m in matches]
        else:
            ids = storage.list_kb_ids(limit=15)
            entries = storage.get_kb_entries(ids) if ids else []
            rows = [(e.get("id"), (e.get("metadata") or {}).get("text", ""), None) for e in entries]
    except Exception as exc:
        return f'<div class="empty-state"><div class="t">Could not reach the knowledge base: {esc(exc)}</div></div>'

    if not rows:
        return '<div class="empty-state"><div class="t">No matching entries.</div></div>'

    out = []
    if not q:
        out.append(f'<div class="card-sub" style="margin-bottom:4px">Showing a sample of {len(rows)} entries — search to find more.</div>')
    for entry_id, text, score in rows:
        score_html = f'<span class="badge blue">match {score:.2f}</span>' if score is not None else ""
        out.append(f"""<div class="kb-item"><div class="kb-id">{esc(entry_id)}{' · ' if score_html else ''}{score_html}</div>
          <div class="kb-text">{esc((text or '')[:600])}{'…' if text and len(text) > 600 else ''}</div></div>""")
    return "".join(out)


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
    port = int(os.environ.get("PORT", 5000))
    print(f"Dashboard → http://127.0.0.1:{port}   (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=port, debug=False)
