import streamlit as st
import pandas as pd
import random
import math
from collections import defaultdict

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="The Runway Game",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

hide_ui = """
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
.stDeployButton {display:none;}
</style>
"""
st.markdown(hide_ui, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# App branding CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
:root {
    --purple: #6f42c1;
    --purple-light: #f8f4ff;
    --text: #2d3748;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
}
body { background:#fff; color:var(--text); font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; }

.lx-header {
    background: linear-gradient(135deg,#6f42c1 0%,#7952b3 100%);
    color:#fff; padding:1.8rem 2rem; border-radius:8px; margin-bottom:1.5rem;
    box-shadow:0 4px 12px rgba(111,66,193,.15);
}
.lx-header h1 { margin:0; font-size:2.2em; font-weight:700; }
.lx-header p  { margin:.4rem 0 0; font-size:1.05em; opacity:.92; }

.card {
    background:var(--purple-light); border-left:4px solid var(--purple);
    padding:1.2rem 1.5rem; border-radius:6px; margin:.8rem 0;
}
.event-card {
    background:#fff; border:2px solid var(--purple); border-radius:8px;
    padding:1.4rem; margin:.8rem 0; box-shadow:0 2px 8px rgba(0,0,0,.06);
}
.event-card h3 { margin:0 0 .4rem; color:var(--purple); }
.badge {
    display:inline-block; background:var(--purple); color:#fff;
    padding:.25rem .7rem; border-radius:12px; font-size:.85em; margin:.2rem;
}
.fuel-track { background:#e5e7eb; border-radius:6px; height:22px; overflow:hidden; margin:.5rem 0; }
.fuel-bar  { height:100%; border-radius:6px; transition:width .4s; }

.metric-row { display:flex; gap:.8rem; flex-wrap:wrap; margin-bottom:1rem; }
.m-box {
    flex:1; min-width:120px; background:#fff; border:1px solid #e5e7eb;
    padding:.8rem; border-radius:6px; text-align:center;
}
.m-val { font-size:1.5em; font-weight:700; color:var(--purple); }
.m-lbl { font-size:.82em; color:#6b7280; margin-top:.25rem; }
.m-val.green { color:var(--green); }
.m-val.amber { color:var(--amber); }
.m-val.red   { color:var(--red); }
</style>
""", unsafe_allow_html=True)


# ===================================================================
# CONSTANTS
# ===================================================================
STARTING_CASH = 48_000
STARTING_BURN = 5_000
MONTHS_TOTAL = 12
WIN_MRR = 5_000
STRONG_MRR = 2_500
STARTING_ACV = 29          # avg revenue per customer per month
STARTING_CHURN = 0.10
STARTING_MORALE = 80
STARTING_PRODUCT = 30       # product quality 0-100
STARTING_AWARENESS = 10     # market awareness 0-100
STARTING_CONVERSION = 0.04  # signup to paid %


# ===================================================================
# EVENT CATALOG
# ===================================================================
AUTO_EVENTS = [
    dict(title="📰 Press Mention",
         desc="A tech blog featured your product! New signups pour in.",
         delta=dict(new_customers=25)),
    dict(title="🤝 Partnership Win",
         desc="A co-marketing partner shared your product with their audience.",
         delta=dict(new_customers=40)),
    dict(title="💸 AWS Bill Spike",
         desc="Server costs exceeded your forecast this month.",
         delta=dict(cash=-1200)),
    dict(title="🏃 Competitor Launch",
         desc="A well-funded competitor launched a similar product at a lower price.",
         delta=dict(churn_bump=0.02)),
    dict(title="🎉 Product Hunt Feature",
         desc="Your product trended on Product Hunt for a day!",
         delta=dict(new_customers=60, awareness_bump=8)),
    dict(title="🐛 Critical Bug",
         desc="A major bug caused data loss for some users. Trust took a hit.",
         delta=dict(churn_bump=0.03, morale=-5)),
    dict(title="📈 Organic Growth Spike",
         desc="Word of mouth drove a surprise wave of signups.",
         delta=dict(new_customers=35)),
    dict(title="🔧 Tech Debt Crunch",
         desc="Accumulated shortcuts slowed your team to a crawl this month.",
         delta=dict(morale=-8, product_bump=-5)),
]

CHOICE_EVENTS = [
    dict(title="🧑‍💻 Key Engineer Got a FAANG Offer",
         desc="Your best engineer is considering leaving.",
         options=[
             dict(label="Offer a $1K/mo raise to keep them",
                  delta=dict(burn_bump=1000, morale=5),
                  journal="Retained key engineer with a raise"),
             dict(label="Wish them well and let them go",
                  delta=dict(morale=-12, product_bump=-8),
                  journal="Lost key engineer; team morale dropped"),
         ]),
    dict(title="🏢 Enterprise Client Interest",
         desc="A large company wants a custom feature. It would take a month of dev time but pay $1K/mo ongoing.",
         options=[
             dict(label="Build the custom feature",
                  delta=dict(mrr_bump=1000, product_bump=-5, morale=-5),
                  journal="Built enterprise feature, landed $1K/mo deal"),
             dict(label="Politely decline and stay focused",
                  delta=dict(),
                  journal="Declined enterprise deal to stay focused on core product"),
         ]),
    dict(title="🎓 Accelerator Invitation",
         desc="A top accelerator invited you to their next cohort. It costs a month of founder time but could yield $15K and mentorship.",
         options=[
             dict(label="Accept the accelerator spot",
                  delta=dict(cash=15000, product_bump=-3),
                  journal="Joined accelerator, secured $15K"),
             dict(label="Stay heads down on execution",
                  delta=dict(),
                  journal="Declined accelerator to maintain execution speed"),
         ]),
    dict(title="💰 Angel Investor Offer",
         desc="An angel wants to invest $10K at a 20% discount to your last round. Quick cash, but dilutive.",
         options=[
             dict(label="Take the money",
                  delta=dict(cash=10000),
                  journal="Accepted angel investment of $10K"),
             dict(label="Protect your cap table",
                  delta=dict(),
                  journal="Declined angel investment to protect equity"),
         ]),
    dict(title="📢 Influencer Partnership",
         desc="A social media influencer will promote your product for $800 flat.",
         options=[
             dict(label="Pay for the promotion",
                  delta=dict(cash=-800, new_customers=45, awareness_bump=6),
                  journal="Paid influencer $800, gained 45 customers"),
             dict(label="Save the cash",
                  delta=dict(),
                  journal="Skipped influencer promotion to conserve runway"),
         ]),
    dict(title="⏸️ Unexpected Stability Window",
         desc="This month is unusually calm. No major fires, no new opportunities. The fundamentals of your business are working well.",
         options=[
             dict(label="Maintain course—ride the wave",
                  delta=dict(morale=5),
                  journal="Maintained steady execution; team recharged"),
             dict(label="Aggressively push for growth despite the calm",
                  delta=dict(product_bump=-3, morale=-5),
                  journal="Forced aggressive growth push; created unnecessary stress"),
             dict(label="Use the calm to reflect and optimize operations",
                  delta=dict(burn=-500, morale=3),
                  journal="Took time to optimize; slightly reduced burn and improved morale"),
         ]),
]

BOARD_DECISIONS = {
    3: dict(title="Quarter 1 Board Check-in: First Hire",
            desc="You've been doing everything solo. It's time to consider your first hire. Each costs $3K/mo but boosts their area significantly.",
            options=[
                dict(label="Hire an Engineer (+50% product impact)",
                     delta=dict(burn_bump=3000, team=1, product_buff=0.5),
                     journal="Hired first engineer"),
                dict(label="Hire a Growth Marketer (+50% marketing impact)",
                     delta=dict(burn_bump=3000, team=1, marketing_buff=0.5),
                     journal="Hired first growth marketer"),
                dict(label="Hire a Salesperson (+50% sales impact)",
                     delta=dict(burn_bump=3000, team=1, sales_buff=0.5),
                     journal="Hired first salesperson"),
                dict(label="Stay solo and keep burn low",
                     delta=dict(),
                     journal="Chose to stay solo, preserving runway"),
            ]),
    6: dict(title="Mid-Game Board Check-in: Strategic Direction",
            desc="Six months in. You have real data now. Time for a strategic call.",
            options=[
                dict(label="Double down on current path (boost all metrics slightly)",
                     delta=dict(product_bump=5, awareness_bump=5, morale=5),
                     journal="Doubled down on current strategy"),
                dict(label="Pivot to a higher-value segment (+$15 ACV, reset some awareness)",
                     delta=dict(acv_bump=15, awareness_bump=-15, product_bump=-5),
                     journal="Pivoted to higher-value customer segment"),
                dict(label="Launch a freemium tier (2x signups, lower ACV by $10)",
                     delta=dict(acv_bump=-10, signup_multiplier=2.0),
                     journal="Launched freemium tier"),
            ]),
    9: dict(title="Month 9 Board Check-in: Final Push",
            desc="Three months left. This is your last strategic decision point. Cash is tight.",
            options=[
                dict(label="Start fundraising now (takes founder focus but could add $20K)",
                     delta=dict(cash=20000, product_bump=-8, morale=-5),
                     journal="Started fundraising, secured $20K bridge"),
                dict(label="Cut burn 25% to extend runway (morale hit)",
                     delta=dict(burn_cut=0.25, morale=-15),
                     journal="Cut burn 25% to extend runway"),
                dict(label="All-in on sales (redirect 40% of budget to close deals)",
                     delta=dict(sales_buff_temp=0.4, product_bump=-5),
                     journal="Went all-in on sales for final push"),
                dict(label="Hold steady and trust the current trajectory",
                     delta=dict(),
                     journal="Maintained current approach for final stretch"),
            ]),
}

ACHIEVEMENTS = {
    "first_customer": ("🎯 First Customer!", "You acquired your first paying customer."),
    "ramen_profitable": ("🍜 Ramen Profitable", "Your MRR exceeds your monthly burn."),
    "hundred_club": ("💯 The Hundred Club", "You reached 100 customers."),
    "growth_10x": ("📈 10x Month", "You grew MRR by 10x in a single month."),
    "survivor": ("🛡 Crisis Survivor", "You made it through a crisis event."),
    "first_hire": ("👥 Team of Two", "You made your first hire."),
    "two_k_mrr": ("🌟 $2K MRR", "You crossed $2,000 in monthly recurring revenue."),
    "five_k_mrr": ("🏆 $5K MRR", "You hit the ultimate goal!"),
}


# ===================================================================
# SESSION STATE INIT
# ===================================================================
def init():
    defaults = dict(
        stage="intro",       # intro | play | event | board | gameover
        month=1,
        cash=STARTING_CASH,
        burn=STARTING_BURN,
        mrr=0,
        customers=0,
        churn=STARTING_CHURN,
        team=1,
        morale=STARTING_MORALE,
        product=STARTING_PRODUCT,
        awareness=STARTING_AWARENESS,
        conversion=STARTING_CONVERSION,
        acv=STARTING_ACV,
        journal=[],
        alloc_hist=defaultdict(float),
        badges=[],
        pending_events=[],
        pending_board=None,
        prev_mrr=0,
        signup_multiplier=1.0,
        product_buff=0.0,
        marketing_buff=0.0,
        sales_buff=0.0,
        sales_buff_temp=0.0,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

S = st.session_state   # shorthand


# ===================================================================
# HELPERS
# ===================================================================
def runway_months():
    net = S.burn - S.mrr
    if net <= 0:
        return 99
    return max(0, int(S.cash / net))

def color_class(val, low, med):
    if val <= low:
        return "red"
    if val <= med:
        return "amber"
    return "green"

def add_badge(key):
    if key not in S.badges:
        S.badges.append(key)

def journal(text):
    S.journal.append(f"Month {S.month}: {text}")


# ===================================================================
# MONTHLY SIMULATION ENGINE
# ===================================================================
def simulate_month(product_pct, marketing_pct, sales_pct, ops_pct):
    """Run one month of the simulation given allocation percentages (sum to 100)."""
    # Track allocation for personality
    S.alloc_hist["product"] += product_pct
    S.alloc_hist["marketing"] += marketing_pct
    S.alloc_hist["sales"] += sales_pct
    S.alloc_hist["ops"] += ops_pct

    # ---- Product quality ----
    prod_gain = product_pct * 0.20 * (1 + S.product_buff)
    S.product = min(95, S.product + prod_gain)

    # ---- Awareness ----
    mkt_gain = marketing_pct * 0.15 * (1 + S.marketing_buff)
    S.awareness = min(95, S.awareness + mkt_gain)

    # ---- Product-driven awareness (good products get organic press & reviews) ----
    if S.product >= 65:
        organic_awareness = (S.product - 55) * 0.08
        S.awareness = min(95, S.awareness + organic_awareness)

    # ---- Conversion ----
    sales_gain = sales_pct * 0.0004 * (1 + S.sales_buff + S.sales_buff_temp)
    S.conversion = min(0.30, S.conversion + sales_gain)

    # ---- Morale ----
    if ops_pct >= 15:
        S.morale = min(100, S.morale + 3)
    elif ops_pct >= 5:
        S.morale = min(100, S.morale + 1)
    else:
        S.morale = max(10, S.morale - 4)

    # ---- Synergy bonus for balanced allocation ----
    min_alloc = min(product_pct, marketing_pct, sales_pct, ops_pct)
    synergy = 1.0 + (min_alloc / 100) * 0.5  # up to 1.125 at perfectly balanced (25/25/25/25)

    # ---- New customers this month ----
    # Product quality affects word of mouth: poor product = fewer referrals, bad reviews
    product_reputation = max(0.3, S.product / 60)  # 0.3 at low quality, 1.0 at 60, 1.5+ at 90
    base_signups = marketing_pct * 0.7 * (S.awareness / 100) * product_reputation
    converted = base_signups * S.conversion * 7 * S.signup_multiplier * synergy
    new_custs = max(0, int(converted))

    # ---- Outbound / direct sales channel ----
    outbound_effectiveness = (1 + S.sales_buff + S.sales_buff_temp) * product_reputation * max(0.3, S.awareness / 80)
    outbound = int(sales_pct * 0.18 * outbound_effectiveness)
    new_custs += outbound

    # ---- Word of mouth from high product quality ----
    if S.product >= 70:
        wom_signups = int((S.product - 60) * 0.15 * (S.customers / max(1, 50)))
        new_custs += wom_signups

    S.customers += new_custs

    # ---- Churn (remove customers) ----
    # Low product quality causes significant churn; high product reduces it
    effective_churn = S.churn
    if S.product >= 80:
        effective_churn -= 0.025
    elif S.product >= 65:
        effective_churn -= 0.01
    elif S.product < 35:
        effective_churn += 0.05   # serious leaky bucket
    elif S.product < 50:
        effective_churn += 0.03
    elif S.product < 65:
        effective_churn += 0.01
    if S.morale < 30:
        effective_churn += 0.05
    elif S.morale < 50:
        effective_churn += 0.03
    elif S.morale < 65:
        effective_churn += 0.01
    effective_churn = max(0.005, min(0.30, effective_churn))
    lost = int(S.customers * effective_churn)
    S.customers = max(0, S.customers - lost)

    # ---- MRR ----
    S.prev_mrr = S.mrr
    S.mrr = S.customers * S.acv

    # ---- Cash flow ----
    S.cash = S.cash - S.burn + S.mrr

    # ---- Reset temp buffs ----
    S.sales_buff_temp = 0.0

    # ---- Check achievements ----
    if S.customers > 0:
        add_badge("first_customer")
    if S.customers >= 100:
        add_badge("hundred_club")
    if S.mrr >= S.burn and S.mrr > 0:
        add_badge("ramen_profitable")
    if S.prev_mrr > 0 and S.mrr >= S.prev_mrr * 10:
        add_badge("growth_10x")
    if S.team > 1:
        add_badge("first_hire")
    if S.mrr >= 2000:
        add_badge("two_k_mrr")
    if S.mrr >= 5000:
        add_badge("five_k_mrr")

    journal(f"Spend $ {S.burn:,} | Prod {product_pct}% / Mkt {marketing_pct}% / Sales {sales_pct}% / Ops {ops_pct}% | +{new_custs} customers, {lost} churned | MRR ${S.mrr:,}")

    return new_custs, lost


def project_month(product_usd: int, marketing_usd: int, sales_usd: int, ops_usd: int) -> dict:
    """Deterministic forward projection of one month given a proposed spend mix.
    Uses the SAME core math as simulate_month() but without randomness. Returns
    a full projected P&L + unit economics so the learner can see the
    consequences of their allocation live, BEFORE committing.
    """
    total_spend = product_usd + marketing_usd + sales_usd + ops_usd
    if total_spend <= 0:
        return {
            "total_spend": 0, "projected_new_custs": 0, "projected_lost": 0,
            "projected_mrr": S.mrr, "projected_cash": S.cash - 0,
            "net_burn": S.burn - S.mrr, "runway_months": runway_months(),
            "cac": 0, "ltv": 0, "ltv_cac": 0, "payback_months": 0,
            "product_pct": 0, "marketing_pct": 0, "sales_pct": 0, "ops_pct": 0,
        }
    product_pct = product_usd / total_spend * 100
    marketing_pct = marketing_usd / total_spend * 100
    sales_pct = sales_usd / total_spend * 100
    ops_pct = ops_usd / total_spend * 100

    # Replicate customer-acquisition math from simulate_month (no RNG)
    product_reputation = max(0.3, S.product / 60)
    min_alloc = min(product_pct, marketing_pct, sales_pct, ops_pct)
    synergy = 1.0 + (min_alloc / 100) * 0.5

    base_signups = marketing_pct * 0.7 * (S.awareness / 100) * product_reputation
    inbound = base_signups * S.conversion * 7 * S.signup_multiplier * synergy
    outbound_eff = (1 + S.sales_buff + S.sales_buff_temp) * product_reputation * max(0.3, S.awareness / 80)
    outbound = sales_pct * 0.18 * outbound_eff
    wom = 0.0
    if S.product >= 70:
        wom = (S.product - 60) * 0.15 * (S.customers / max(1, 50))
    new_custs = max(0, int(inbound + outbound + wom))

    # Churn projection
    effective_churn = S.churn
    if S.product >= 80: effective_churn -= 0.025
    elif S.product >= 65: effective_churn -= 0.01
    elif S.product < 35: effective_churn += 0.05
    elif S.product < 50: effective_churn += 0.03
    elif S.product < 65: effective_churn += 0.01
    if S.morale < 30: effective_churn += 0.05
    elif S.morale < 50: effective_churn += 0.03
    elif S.morale < 65: effective_churn += 0.01
    effective_churn = max(0.005, min(0.30, effective_churn))
    lost = int(S.customers * effective_churn)

    # Projected end-of-month state
    projected_customers = max(0, S.customers + new_custs - lost)
    projected_mrr = projected_customers * S.acv
    projected_cash = S.cash - total_spend + projected_mrr
    net_burn = total_spend - projected_mrr

    # Runway = cash / net monthly burn (99 if profitable)
    if net_burn <= 0:
        runway = 99
    else:
        runway = max(0, int(projected_cash / net_burn)) if projected_cash > 0 else 0

    # Unit economics: CAC = (sales+marketing) / new_custs
    ca_spend = marketing_usd + sales_usd
    cac = (ca_spend / new_custs) if new_custs > 0 else 0
    # LTV = ACV / churn (perpetuity at effective churn rate)
    ltv = (S.acv / effective_churn) if effective_churn > 0 else S.acv * 12
    ltv_cac = (ltv / cac) if cac > 0 else 0
    # Payback: CAC / monthly contribution (assume 80% gross margin on SaaS)
    gross_margin = 0.80
    monthly_cm_per_cust = S.acv * gross_margin
    payback = (cac / monthly_cm_per_cust) if monthly_cm_per_cust > 0 and cac > 0 else 0

    return {
        "total_spend": total_spend,
        "projected_new_custs": new_custs,
        "projected_lost": lost,
        "projected_customers": projected_customers,
        "projected_mrr": projected_mrr,
        "projected_cash": projected_cash,
        "net_burn": net_burn,
        "runway_months": runway,
        "effective_churn": effective_churn,
        "cac": cac,
        "ltv": ltv,
        "ltv_cac": ltv_cac,
        "payback_months": payback,
        "product_pct": product_pct,
        "marketing_pct": marketing_pct,
        "sales_pct": sales_pct,
        "ops_pct": ops_pct,
    }


def apply_delta(delta):
    """Apply an event/board delta dict to the game state."""
    S.cash += delta.get("cash", 0)
    S.customers += delta.get("new_customers", 0)
    S.churn += delta.get("churn_bump", 0)
    S.churn -= delta.get("churn_reduction", 0)
    S.churn = max(0.005, min(0.20, S.churn))
    S.morale = max(0, min(100, S.morale + delta.get("morale", 0)))
    S.product = max(0, min(95, S.product + delta.get("product_bump", 0)))
    S.awareness = max(0, min(95, S.awareness + delta.get("awareness_bump", 0)))
    S.burn += delta.get("burn_bump", 0)
    S.team += delta.get("team", 0)
    S.acv += delta.get("acv_bump", 0)
    S.acv = max(5, S.acv)
    S.mrr += delta.get("mrr_bump", 0)
    S.product_buff += delta.get("product_buff", 0)
    S.marketing_buff += delta.get("marketing_buff", 0)
    S.sales_buff += delta.get("sales_buff", 0)
    S.sales_buff_temp += delta.get("sales_buff_temp", 0)
    if delta.get("signup_multiplier"):
        S.signup_multiplier *= delta["signup_multiplier"]
    if delta.get("burn_cut"):
        S.burn = int(S.burn * (1 - delta["burn_cut"]))
    if delta.get("burn_bump_pct"):
        S.burn = int(S.burn * (1 + delta["burn_bump_pct"]))


# ===================================================================
# ARCHETYPE SYSTEM
# ===================================================================
ARCHETYPES = {
    "The Perfectionist": {
        "condition": lambda p, m, s, o: p > 35,
        "icon": "🔬",
        "summary": "You invested heavily in building the best possible product.",
        "strength": "Product excellence and low churn. Customers who find you tend to stay.",
        "watch_out": "Spending too long perfecting before enough people know you exist. Great products still need distribution.",
        "real_world": "Think about whether your instinct to 'make it better first' is protecting you from the scarier work of selling and marketing.",
    },
    "The Hype Machine": {
        "condition": lambda p, m, s, o: m > 35,
        "icon": "📣",
        "summary": "You prioritized awareness and getting the word out above all else.",
        "strength": "Strong top of funnel. Lots of people know about your product.",
        "watch_out": "High awareness with a weak product leads to high churn. People try it once and leave.",
        "real_world": "Marketing without product market fit burns cash fast. Make sure your retention metrics justify your acquisition spend.",
    },
    "The Closer": {
        "condition": lambda p, m, s, o: s > 35,
        "icon": "🤝",
        "summary": "You focused on converting leads and driving revenue through direct sales effort.",
        "strength": "Strong conversion rates and potentially higher deal sizes.",
        "watch_out": "Sales-heavy models can be hard to scale. If you need a human in every deal, growth has a ceiling.",
        "real_world": "Consider whether your sales focus reflects a genuine strategy or an avoidance of investing in product and brand.",
    },
    "The Organizer": {
        "condition": lambda p, m, s, o: o > 35,
        "icon": "⚙️",
        "summary": "You invested heavily in team health, operations, and infrastructure.",
        "strength": "High morale and a stable team. Less firefighting, more consistency.",
        "watch_out": "Over-investing in ops before you have product market fit can mean a well-run ship sailing in the wrong direction.",
        "real_world": "Operational excellence matters, but in early stages, speed of learning matters more. Are you optimizing too early?",
    },
    "The Orchestrator": {
        "condition": lambda p, m, s, o: True,  # fallback
        "icon": "🎯",
        "summary": "You spread your resources across all areas, keeping things balanced.",
        "strength": "No single blind spot. You kept every area moving forward.",
        "watch_out": "Balance can also mean lack of conviction. Sometimes startups need to go all in on one lever to break through.",
        "real_world": "Think about whether your balanced approach reflects strategic thinking or difficulty making tough trade-offs.",
    },
}

def get_archetype():
    total = sum(S.alloc_hist.values()) or 1
    p = S.alloc_hist["product"] / total * 100
    m = S.alloc_hist["marketing"] / total * 100
    s = S.alloc_hist["sales"] / total * 100
    o = S.alloc_hist["ops"] / total * 100
    for name, info in ARCHETYPES.items():
        if name == "The Orchestrator":
            continue
        if info["condition"](p, m, s, o):
            return name, info
    return "The Orchestrator", ARCHETYPES["The Orchestrator"]


# ===================================================================
# RENDER: DASHBOARD (reused across stages)
# ===================================================================
def render_dashboard():
    rw = runway_months()
    rw_color = color_class(rw, 3, 6)
    morale_color = color_class(S.morale, 40, 65)
    fuel_pct = max(0, min(100, int(S.cash / STARTING_CASH * 100)))
    fuel_color = "#ef4444" if fuel_pct < 20 else "#f59e0b" if fuel_pct < 45 else "#10b981"

    # Oxygen/runway color: green (6+ months), yellow (3-5 months), red (1-2 months)
    if rw >= 6:
        oxygen_color = "#10b981"  # green
        oxygen_status = "✅ Healthy"
    elif rw >= 3:
        oxygen_color = "#f59e0b"  # yellow
        oxygen_status = "⚠️ Caution"
    else:
        oxygen_color = "#ef4444"  # red
        oxygen_status = "🔴 Critical"

    st.markdown(f"""
    <div style="background: linear-gradient(90deg, {oxygen_color}33 0%, transparent 100%); border-left: 4px solid {oxygen_color}; padding: 1.2rem; border-radius: 8px; margin-bottom: 1.2rem;">
        <div style="font-size: 1.8em; font-weight: 700; color: {oxygen_color};">{rw} months of oxygen remaining</div>
        <div style="font-size: 0.9em; color: #6b7280; margin-top: 0.3rem;">{oxygen_status}</div>
    </div>

    <div class="metric-row">
      <div class="m-box"><div class="m-val">${S.cash:,.0f}</div><div class="m-lbl">Cash</div></div>
      <div class="m-box"><div class="m-val">${S.burn:,.0f}</div><div class="m-lbl">Monthly Burn</div></div>
      <div class="m-box"><div class="m-val {rw_color}">${S.mrr:,.0f}</div><div class="m-lbl">Monthly Revenue</div></div>
      <div class="m-box"><div class="m-val">{S.customers}</div><div class="m-lbl">Customers</div></div>
      <div class="m-box"><div class="m-val {morale_color}">{S.morale}</div><div class="m-lbl">Morale</div></div>
      <div class="m-box"><div class="m-val">{S.team}</div><div class="m-lbl">Team Size</div></div>
    </div>
    <div class="fuel-track">
      <div class="fuel-bar" style="width:{fuel_pct}%; background:{fuel_color};"></div>
    </div>
    """, unsafe_allow_html=True)

    # Badges
    if S.badges:
        badge_html = " ".join(f'<span class="badge">{ACHIEVEMENTS[b][0]}</span>' for b in S.badges)
        st.markdown(badge_html, unsafe_allow_html=True)


# ===================================================================
# RENDER: INTRO
# ===================================================================
def render_intro():
    st.markdown("""
    <div class="lx-header">
        <h1>🚀 The Runway Game</h1>
        <p>Survive, Grow, or Flame Out</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### Your Mission

        You just scraped together **$48K** from savings and a small angel check for your startup.
        You have **12 months** to reach **$5K MRR** before your cash runs out.

        ### ⏱️ Time Estimate
        **~30-45 minutes** to play through all 12 months.

        Each month you will allocate your budget across four areas:

        **Product Development**: Build features, reduce churn, improve quality

        **Marketing & Growth**: Drive awareness and signups

        **Sales & Business Dev**: Convert leads, grow deal size

        **Team & Operations**: Maintain morale and keep the lights on

        Along the way, random shocks and quarterly board check-ins will test your judgment.
        Your choices reveal your **founder operating style** and teach you about your decision-making tendencies.

        **Can you survive the runway?**
        """)

        if st.button("🚀 Launch the Game", use_container_width=True):
            S.stage = "play"
            st.rerun()

    with col2:
        st.markdown("""
        ### Starting Position
        """)
        st.markdown(f"""
        <div class="card">
            <p>💰 <strong>Cash:</strong> $48,000</p>
            <p>🔥 <strong>Monthly Burn:</strong> $5,000</p>
            <p>⏱ <strong>Runway:</strong> 12 months</p>
            <p>💵 <strong>MRR:</strong> $0</p>
            <p>👥 <strong>Customers:</strong> 0</p>
            <p>👔 <strong>Team:</strong> 1 (you)</p>
            <p>😊 <strong>Morale:</strong> 80/100</p>
            <p>🎯 <strong>Goal:</strong> $5K MRR</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        ### How Scoring Works
        """)
        st.markdown("""
        <div class="card">
            <p>Your allocation patterns across all 12 months determine your <strong>Founder Operating Style</strong>.
            There's no single right answer: the game reveals your natural tendencies so you can learn from them.</p>
        </div>
        """, unsafe_allow_html=True)


# ===================================================================
# RENDER: MONTHLY PLAY
# ===================================================================
def render_play():
    st.markdown(f"""
    <div class="lx-header">
        <h1>Month {S.month} of {MONTHS_TOTAL}</h1>
        <p>Monthly burn: ${S.burn:,} | Net monthly: ${S.mrr - S.burn:,}</p>
    </div>
    """, unsafe_allow_html=True)

    render_dashboard()
    st.divider()

    st.subheader("Allocate Your Monthly Spend")
    max_spend_this_month = max(1500, int(S.cash))
    st.caption(
        f"You have **${S.cash:,.0f}** in the bank and earned **${S.mrr:,.0f}** in MRR last month. "
        f"Decide how to deploy cash across four categories. The sum becomes this month's burn "
        f"(minimum $1,500 to keep the lights on, max $ {max_spend_this_month:,} = your cash)."
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        product_usd  = st.number_input("🔨 Product Development ($)",   min_value=0, max_value=max_spend_this_month, value=min(1500, max_spend_this_month), step=250, key="usd_p",
                                       help="Engineers, design, QA. Each $500 adds ~2 product quality points.")
        marketing_usd = st.number_input("📣 Marketing & Growth ($)",    min_value=0, max_value=max_spend_this_month, value=min(1500, max_spend_this_month), step=250, key="usd_m",
                                        help="Ads, content, PR. Drives awareness and top-of-funnel signups.")
        sales_usd    = st.number_input("🤝 Sales & Biz Dev ($)",       min_value=0, max_value=max_spend_this_month, value=min(1000, max_spend_this_month), step=250, key="usd_s",
                                       help="Outbound, deal closing, partnerships. Improves conversion rate.")
        ops_usd      = st.number_input("⚙️ Team & Operations ($)",     min_value=0, max_value=max_spend_this_month, value=min(1000, max_spend_this_month), step=250, key="usd_o",
                                       help="HR, tools, admin, morale. Keeps team productive and retained.")

    total_spend = product_usd + marketing_usd + sales_usd + ops_usd
    # Convert dollars to percentages for the existing simulation engine
    if total_spend > 0:
        product_pct  = int(round(product_usd  / total_spend * 100))
        marketing_pct = int(round(marketing_usd / total_spend * 100))
        sales_pct    = int(round(sales_usd    / total_spend * 100))
        ops_pct      = 100 - product_pct - marketing_pct - sales_pct  # absorb rounding
    else:
        product_pct = marketing_pct = sales_pct = ops_pct = 0

    with c2:
        st.metric("Monthly Burn", f"${total_spend:,}")
        st.caption(f"Cash after burn: ${S.cash - total_spend + S.mrr:,.0f}")
        if total_spend < 1500:
            st.warning("Minimum spend is $1,500/month.")
        elif total_spend > S.cash:
            st.error(f"Cannot spend more than ${S.cash:,.0f}.")
        else:
            st.success("Ready to commit!")

    # Live projected P&L — deterministic preview of this allocation
    proj = project_month(product_usd, marketing_usd, sales_usd, ops_usd)
    st.markdown("##### 📊 Live Projection (deterministic — actual results include variance)")

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Proj. New Customers", f"+{proj['projected_new_custs']}",
                  delta=f"-{proj['projected_lost']} churn" if proj['projected_lost'] > 0 else None,
                  delta_color="inverse")
    with p2:
        mrr_delta = proj["projected_mrr"] - S.mrr
        st.metric("Proj. End-of-Month MRR", f"${proj['projected_mrr']:,.0f}",
                  delta=f"${mrr_delta:+,.0f}")
    with p3:
        nb_color = "inverse" if proj["net_burn"] > 0 else "normal"
        st.metric("Net Burn", f"${proj['net_burn']:,.0f}/mo",
                  help="Spend minus projected MRR. Negative means profitable.")
    with p4:
        runway_label = "∞ (profitable)" if proj["runway_months"] >= 99 else f"{proj['runway_months']} mo"
        st.metric("Projected Runway", runway_label,
                  help="Months until cash runs out at this net burn (after projected MRR)")

    # Unit economics row
    u1, u2, u3, u4 = st.columns(4)
    with u1:
        cac_display = f"${proj['cac']:,.0f}" if proj["cac"] > 0 else "—"
        st.metric("Implied CAC", cac_display,
                  help="(marketing + sales spend) ÷ new customers acquired")
    with u2:
        ltv_display = f"${proj['ltv']:,.0f}" if proj["ltv"] > 0 else "—"
        st.metric("LTV", ltv_display, help="ACV ÷ effective churn rate")
    with u3:
        ratio = proj["ltv_cac"]
        ratio_label = f"{ratio:.1f} : 1" if ratio > 0 else "—"
        st.metric("LTV : CAC", ratio_label, help="≥ 3.0 is healthy")
    with u4:
        pb = proj["payback_months"]
        pb_label = f"{pb:.1f} mo" if pb > 0 else "—"
        st.metric("Payback", pb_label, help="Months of gross margin to recover CAC")

    # Mini P&L line items
    with st.expander("📋 Projected Monthly P&L", expanded=False):
        st.markdown(f"""
| Line item | Amount |
|---|---:|
| Projected MRR | ${proj['projected_mrr']:,.0f} |
| Gross margin @ 80% | ${proj['projected_mrr'] * 0.80:,.0f} |
| Product & engineering | -${product_usd:,} |
| Marketing & growth | -${marketing_usd:,} |
| Sales & biz dev | -${sales_usd:,} |
| Team & operations | -${ops_usd:,} |
| **Net (gross margin − opex)** | **${proj['projected_mrr'] * 0.80 - total_spend:,.0f}** |
| Cash at start of month | ${S.cash:,.0f} |
| Cash at end of month | ${proj['projected_cash']:,.0f} |
""")

    can_commit = 1500 <= total_spend <= S.cash
    if st.button("✅ Commit This Month", use_container_width=True, disabled=not can_commit):
        # Lock in the actual dollar burn for this month
        S.burn = total_spend
        # Run simulation with converted percentages (and actual burn)
        simulate_month(product_pct, marketing_pct, sales_pct, ops_pct)

        # Check bankruptcy
        if S.cash <= 0:
            S.stage = "gameover"
            st.rerun()
            return

        # Check win
        if S.mrr >= WIN_MRR:
            add_badge("five_k_mrr")
            S.stage = "gameover"
            st.rerun()
            return

        # Board check-in?
        if S.month in BOARD_DECISIONS:
            S.pending_board = BOARD_DECISIONS[S.month]
            S.stage = "board"
            S.month += 1
            st.rerun()
            return

        # Random events (40% chance per month)
        if random.random() < 0.40:
            # Pick one event
            if random.random() < 0.5:
                ev = random.choice(AUTO_EVENTS)
            else:
                ev = random.choice(CHOICE_EVENTS)
            S.pending_events = [ev]
            S.stage = "event"
            S.month += 1
            st.rerun()
            return

        # Normal advance
        S.month += 1
        if S.month > MONTHS_TOTAL:
            S.stage = "gameover"
        st.rerun()

    # Journal sidebar
    if S.journal:
        with st.expander("📓 Founder Journal", expanded=False):
            for entry in reversed(S.journal[-10:]):
                st.write(entry)


# ===================================================================
# RENDER: EVENT
# ===================================================================
def render_event():
    if not S.pending_events:
        S.stage = "play"
        st.rerun()
        return

    ev = S.pending_events[0]

    st.markdown(f"""
    <div class="lx-header">
        <h1>Month {S.month - 1}: Event!</h1>
        <p>Something happened this month...</p>
    </div>
    """, unsafe_allow_html=True)

    render_dashboard()

    st.markdown(f"""
    <div class="event-card">
        <h3>{ev['title']}</h3>
        <p>{ev['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    if "options" in ev:
        # Choice event
        choice = st.radio("What will you do?",
                          range(len(ev["options"])),
                          format_func=lambda i: ev["options"][i]["label"],
                          key="event_radio")

        if st.button("Make Your Decision", use_container_width=True, key="ev_btn"):
            selected = ev["options"][choice]
            apply_delta(selected.get("delta", {}))
            journal(selected.get("journal", "Made a decision"))
            add_badge("survivor")
            S.pending_events.pop(0)

            if S.cash <= 0:
                S.stage = "gameover"
            elif S.month > MONTHS_TOTAL:
                S.stage = "gameover"
            elif S.pending_events:
                pass  # stay in event stage
            else:
                S.stage = "play"
            st.rerun()
    else:
        # Auto event: show it, apply on click
        if st.button("Continue", use_container_width=True, key="ev_auto_btn"):
            apply_delta(ev.get("delta", {}))
            journal(ev.get("title", "Event occurred"))
            S.pending_events.pop(0)

            if S.cash <= 0:
                S.stage = "gameover"
            elif S.month > MONTHS_TOTAL:
                S.stage = "gameover"
            elif S.pending_events:
                pass
            else:
                S.stage = "play"
            st.rerun()


# ===================================================================
# RENDER: BOARD CHECK-IN
# ===================================================================
def render_board():
    bd = S.pending_board
    if not bd:
        S.stage = "play"
        st.rerun()
        return

    st.markdown(f"""
    <div class="lx-header">
        <h1>{bd['title']}</h1>
        <p>A strategic decision point for your startup</p>
    </div>
    """, unsafe_allow_html=True)

    render_dashboard()

    st.markdown(f"""
    <div class="event-card">
        <h3>📋 Board Decision Required</h3>
        <p>{bd['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    choice = st.radio("Your strategic decision:",
                      range(len(bd["options"])),
                      format_func=lambda i: bd["options"][i]["label"],
                      key="board_radio")

    if st.button("Confirm Decision", use_container_width=True, key="board_btn"):
        selected = bd["options"][choice]
        apply_delta(selected.get("delta", {}))
        journal(selected.get("journal", "Made board decision"))
        S.pending_board = None

        if S.cash <= 0:
            S.stage = "gameover"
        elif S.month > MONTHS_TOTAL:
            S.stage = "gameover"
        else:
            S.stage = "play"
        st.rerun()


# ===================================================================
# RENDER: GAME OVER
# ===================================================================
def render_gameover():
    # Determine outcome
    if S.cash <= 0:
        outcome = "flameout"
        title = "💥 You Ran Out of Cash"
        subtitle = "Your startup flamed out. Even great ideas need runway."
    elif S.mrr >= WIN_MRR:
        outcome = "win"
        title = "🏆 Victory: $5K MRR!"
        subtitle = "You built a real business. Investors are lining up to fund your next stage."
    elif S.mrr >= STRONG_MRR:
        outcome = "strong"
        title = "🌟 Strong Traction"
        subtitle = f"${S.mrr:,} MRR shows real momentum. You're on the path to product market fit."
    else:
        outcome = "modest"
        title = "🌱 Modest Progress"
        subtitle = "Your startup survived but hasn't broken through yet. Time to reflect on what to do differently."

    st.markdown(f"""
    <div class="lx-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

    # Final metrics
    render_dashboard()
    st.divider()

    # Archetype
    arch_name, arch_info = get_archetype()
    st.subheader(f"Your Founder Operating Style: {arch_info['icon']} {arch_name}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card">
            <p><strong>Summary:</strong> {arch_info['summary']}</p>
            <p><strong>Your Strength:</strong> {arch_info['strength']}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card">
            <p><strong>Watch Out For:</strong> {arch_info['watch_out']}</p>
            <p><strong>Real World Reflection:</strong> {arch_info['real_world']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Allocation breakdown
    st.subheader("Your Allocation Pattern")
    total_alloc = sum(S.alloc_hist.values()) or 1
    alloc_data = pd.DataFrame({
        "Category": ["Product", "Marketing", "Sales", "Operations"],
        "Percentage": [
            round(S.alloc_hist["product"] / total_alloc * 100, 1),
            round(S.alloc_hist["marketing"] / total_alloc * 100, 1),
            round(S.alloc_hist["sales"] / total_alloc * 100, 1),
            round(S.alloc_hist["ops"] / total_alloc * 100, 1),
        ]
    })
    st.bar_chart(alloc_data.set_index("Category"), color="#6f42c1")

    # Journal
    if S.journal:
        st.subheader("📓 Your Founder Journal")
        with st.expander("View Full Timeline", expanded=False):
            for entry in S.journal:
                st.write(entry)

    # Badges
    if S.badges:
        st.subheader("🏅 Achievements Unlocked")
        badge_cols = st.columns(min(4, len(S.badges)))
        for i, b in enumerate(S.badges):
            with badge_cols[i % len(badge_cols)]:
                title_b, desc_b = ACHIEVEMENTS[b]
                st.markdown(f"""
                <div class="card">
                    <p style="font-size:1.3em; margin:0;">{title_b}</p>
                    <p style="font-size:.85em; color:#6b7280;">{desc_b}</p>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # Restart
    st.divider()
    if st.button("🔄 Play Again", use_container_width=True, key="restart_btn"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ===================================================================
# MAIN GAME LOOP
# ===================================================================
if S.stage == "intro":
    render_intro()
elif S.stage == "play":
    if S.month > MONTHS_TOTAL:
        S.stage = "gameover"
        st.rerun()
    else:
        render_play()
elif S.stage == "event":
    render_event()
elif S.stage == "board":
    render_board()
elif S.stage == "gameover":
    render_gameover()
