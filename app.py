"""U.S. K-12 Education Analytics Dashboard (styled) - run with:  streamlit run app_styled.py"""
import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from analysis import (SCORE_COLUMNS, correlation_summary, data_quality_summary, load_data, missing_table,
                      national_trends, outlier_summary, paired_change_test, state_comparison)

st.set_page_config(page_title="Education Analytics Dashboard", page_icon="📘", layout="wide")
st.markdown("""<style>
.stApp{background:#f4f6fb}
section[data-testid="stSidebar"]{background:#12295a}
section[data-testid="stSidebar"] *{color:#fff}
section[data-testid="stSidebar"] [data-baseweb="select"] *{color:#111}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2rem}
h1{font-weight:800;color:#0f172a}
.kpi{background:#fff;border-radius:14px;padding:16px 20px;box-shadow:0 2px 10px rgba(15,23,42,.08)}
.kpi .t{font-weight:600;color:#0f172a}.kpi .v{font-size:2.3rem;font-weight:800;line-height:1.2}
.kpi .s{font-size:.85rem;color:#64748b}
div[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:14px;box-shadow:0 2px 10px rgba(15,23,42,.08)}
</style>""", unsafe_allow_html=True)

@st.cache_data
def get():
    d = load_data()
    d = d[~d.STATE.isin(["NATIONAL", "DODEA"])].copy()      # 50 states + DC only (NATIONAL would double count)
    d["STATE"] = d.STATE.str.replace("_", " ").str.title().str.replace(" Of ", " of ")
    return d
df = get()

st.sidebar.markdown("## 📘 Education Dashboard")
page = st.sidebar.radio("Menu", ["Overview", "Enrollment & Finance", "Achievement", "State comparison", "Data quality"],
                        label_visibility="collapsed")
st.sidebar.markdown("---")
yrs = st.sidebar.slider("Year range", 1992, 2019, (1992, 2019))
states = st.sidebar.multiselect("States (empty = all 50 + DC)", sorted(df.STATE.unique()))
d = df[df.YEAR.between(*yrs)]
if states: d = d[d.STATE.isin(states)]
BLUE, GREEN, ORANGE, RED = "#2f6fe4", "#22a45d", "#f08a24", "#dc3545"

SRC = {"Enrollment": "ENROLL_CLEAN", "Total revenue": "TOTAL_REVENUE", "Total expenditure": "TOTAL_EXPENDITURE",
       "Spending per student": "EXP_PER_STUDENT", "Grade 4 math": "AVG_MATH_4_SCORE", "Grade 8 math": "AVG_MATH_8_SCORE",
       "Grade 4 reading": "AVG_READING_4_SCORE", "Grade 8 reading": "AVG_READING_8_SCORE"}
n = national_trends(d).set_index("YEAR")
for name, src in SRC.items():                 # hide years where fewer than 90% of states reported
    c = d.groupby("YEAR")[src].count().reindex(n.index)
    n[name] = n[name].where(c >= 0.9 * c.max())
n["Spending per student"] *= 1000             # source is US$ thousands per student
def last(col):
    s = n[col].dropna(); return (s.iloc[-1], int(s.index[-1])) if len(s) else (float("nan"), "-")

def style(fig, h=320):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white",
                      plot_bgcolor="white", legend_title=None, font=dict(color="#334155"))
    fig.update_yaxes(gridcolor="#e8ecf3"); fig.update_xaxes(showgrid=False)
    return fig
def fmt_p(p): return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
def card(title, sub=None):
    box = st.container(border=True)
    box.markdown(f"**{title}**" + (f"  \n<span style='color:#64748b;font-size:.85rem'>{sub}</span>" if sub else ""), unsafe_allow_html=True)
    return box
def line(cols, colors, fmt, fill=True, h=320):
    f = go.Figure()
    for col, color in zip(cols, colors):
        s = n[col].dropna()
        f.add_trace(go.Scatter(x=s.index, y=s.values, name=col, mode="lines+markers", line=dict(color=color, width=3),
                               marker=dict(size=7, color="white", line=dict(color=color, width=2)),
                               fill="tozeroy" if fill else None, fillcolor=color + "22"))
    f.update_yaxes(tickformat=fmt); return style(f, h)

st.title("Education Analytics Dashboard")
st.caption(f"{page} · {yrs[0]}–{yrs[1]} · {', '.join(states) if states else 'All 50 states + DC'}")

if page == "Overview":
    e, ey = last("Enrollment"); sp, sy = last("Spending per student"); m4, my = last("Grade 4 math"); r8, ry = last("Grade 8 reading")
    for col, (t, v, s, c) in zip(st.columns(4), [
        ("Enrollment", f"{e/1e6:.1f}M", f"students, {ey}", BLUE),
        ("Spending / student", f"${sp:,.0f}", f"{sy}, nominal US$ (state average)", GREEN),
        ("Grade 4 Math", f"{m4:.1f}", f"avg NAEP score, {my}", GREEN),
        ("Grade 8 Reading", f"{r8:.1f}", f"avg NAEP score, {ry}", RED)]):
        col.markdown(f'<div class="kpi"><div class="t">{t}</div><div class="v" style="color:{c}">{v}</div><div class="s">{s}</div></div>', unsafe_allow_html=True)
    st.write("")
    a, b, c = st.columns(3)
    with a: card("Spending per Student", "Nominal US$, over time").plotly_chart(line(["Spending per student"], [BLUE], ",.0f"), width="stretch")
    with b:
        sc = {"Math 4": "Grade 4 math", "Math 8": "Grade 8 math", "Reading 4": "Grade 4 reading", "Reading 8": "Grade 8 reading"}
        vals = [last(v)[0] for v in sc.values()]
        f = go.Figure(go.Bar(x=list(sc), y=vals, marker_color=[BLUE, "#2c9fc9", "#3bb8a0", GREEN], text=[f"{v:.0f}" for v in vals], textposition="outside"))
        card("Average NAEP Scores", "Latest tested year").plotly_chart(style(f).update_yaxes(range=[0, 340]), width="stretch")
    with c: card("Enrollment Trend", "Total students").plotly_chart(line(["Enrollment"], [ORANGE], ",.0f"), width="stretch")
elif page == "Enrollment & Finance":
    a, b = st.columns(2)
    k = n[["Total revenue", "Total expenditure"]] / 1e6
    f = go.Figure([go.Scatter(x=k.index, y=k[c], name=c, mode="lines+markers", line=dict(width=3, color=col))
                   for c, col in zip(k.columns, [BLUE, ORANGE])]).update_yaxes(title="US$ billions (nominal)")
    with a: card("Revenue vs expenditure").plotly_chart(style(f), width="stretch")
    rev = d.groupby("YEAR")[["FEDERAL_REVENUE", "STATE_REVENUE", "LOCAL_REVENUE"]].sum()
    rev = rev.div(rev.sum(axis=1), axis=0) * 100
    f = px.area(rev, color_discrete_sequence=[ORANGE, GREEN, BLUE]).update_yaxes(title="% of revenue")
    with b: card("Where school funding comes from").plotly_chart(style(f), width="stretch")
    with card("Change between first and last available year", "Average per state, first vs last year (paired t-test across states)"):
        for col_, (lab, src, mult) in zip(st.columns(2), [("Average enrollment per state", "ENROLL_CLEAN", 1),
                                                         ("Average spending per student (US$)", "EXP_PER_STUDENT", 1000)]):
            r = paired_change_test(d, src)
            with col_:
                if r["n_states"] < 2 or r["first_year"] == r["last_year"] or pd.isna(r["p"]):
                    st.info(f"Not enough data to compare years for: {lab.lower()}."); continue
                v0, v1 = r["mean_first"] * mult, r["mean_last"] * mult
                st.markdown(f"**{lab}**  \n<span style='color:#64748b;font-size:.85rem'>{(v1 / v0 - 1) * 100:+.1f}% · {fmt_p(r['p'])} · {r['n_states']} states</span>", unsafe_allow_html=True)
                f = go.Figure(go.Bar(x=[str(r["first_year"]), str(r["last_year"])], y=[v0, v1], marker_color=["#94a3b8", BLUE],
                                     text=[f"{v:,.0f}" for v in (v0, v1)], textposition="outside", cliponaxis=False))
                st.plotly_chart(style(f, 300).update_yaxes(tickformat=",.0f", range=[0, max(v0, v1) * 1.2]).update_xaxes(type="category").update_layout(margin=dict(l=10, r=10, t=10, b=35)), width="stretch")
elif page == "Achievement":
    lab = st.selectbox("Grade / subject", list(SCORE_COLUMNS)); col = SCORE_COLUMNS[lab]
    a, b = st.columns(2)
    key = {v: k for k, v in SRC.items()}[col]
    with a: card(f"{lab} trend", "Average of state scores, tested years").plotly_chart(line([key], [BLUE], ".0f", fill=False), width="stretch")
    s = d.dropna(subset=["EXP_PER_STUDENT", col]).assign(Spending=lambda x: x.EXP_PER_STUDENT * 1000)
    f = px.scatter(s, x="Spending", y=col, color="YEAR", hover_name="STATE", color_continuous_scale="Blues").update_layout(xaxis_title="Spending per student (nominal US$)")
    with b: card("Spending vs achievement", "Each dot is one state-year").plotly_chart(style(f), width="stretch")
    with card("Correlation summary", "Correlation does not prove causation"):
        cs = correlation_summary(d).dropna(subset=["Pearson r"]).sort_values("Pearson r")
        if cs.empty: st.info("Not enough data to calculate correlations for this selection.")
        else:
            f = go.Figure(go.Bar(x=cs["Pearson r"], y=cs["Achievement measure"], orientation="h",
                                 marker_color=[BLUE if p < 0.05 else "#94a3b8" for p in cs["p-value"]],
                                 text=[f"r = {r:.2f} ({fmt_p(p)}, n = {k})" for r, p, k in zip(cs["Pearson r"], cs["p-value"], cs["N"])],
                                 textposition="outside", cliponaxis=False))
            f.update_xaxes(title="Pearson r (blue = significant, grey = not significant)", automargin=True,
                           range=[-1 if (cs["Pearson r"] < 0).any() else 0, 1.4], showgrid=True, gridcolor="#e8ecf3")
            f.update_yaxes(automargin=True)
            st.plotly_chart(style(f, 300).update_layout(margin=dict(l=10, r=10, t=10, b=50)), width="stretch")
elif page == "State comparison":
    a, b = st.columns(2)
    labels = {"Enrollment": "ENROLL_CLEAN", "Spending per student ($k)": "EXP_PER_STUDENT", "Total expenditure": "TOTAL_EXPENDITURE", **SCORE_COLUMNS}
    m = a.selectbox("Measure", list(labels)); yr = b.slider("Year", 1992, 2019, 2019)
    s = state_comparison(df, yr, labels[m]).sort_values(labels[m])
    if s.empty: st.info("No data for this measure in that year. Try another year.")
    else:
        f = px.bar(s, x=labels[m], y="STATE", orientation="h", color_discrete_sequence=[BLUE]).update_layout(yaxis_title=None, xaxis_title=m)
        card(f"{m} by state, {yr}").plotly_chart(style(f, 900), width="stretch")
else:
    q = data_quality_summary(d)
    for col, (t, v) in zip(st.columns(4), [("Rows", q["rows"]), ("States", q["states"]), ("Years", f'{q["first_year"]}–{q["last_year"]}'),
                                           ("Missing cells", f'{q["missing_percent"]:.1f}%')]):
        col.markdown(f'<div class="kpi"><div class="t">{t}</div><div class="v" style="color:{BLUE}">{v}</div></div>', unsafe_allow_html=True)
    st.write(""); a, b = st.columns(2)
    with a:
        mt = missing_table(d).query("`Missing count` > 0").head(15).sort_values("Missing (%)")
        box = card("Missing values", "Share of records missing, variables with gaps (top 15)")
        if mt.empty: box.success("No missing values in this selection.")
        else:
            f = go.Figure(go.Bar(x=mt["Missing (%)"], y=mt.index, orientation="h", marker_color=ORANGE,
                                 text=[f"{p:.1f}%  ({int(c):,})" for p, c in zip(mt["Missing (%)"], mt["Missing count"])],
                                 textposition="outside", cliponaxis=False))
            f.update_xaxes(title="% of records missing", range=[0, max(mt["Missing (%)"].max() * 1.25, 5)], showgrid=True, gridcolor="#e8ecf3")
            f.update_yaxes(automargin=True)
            box.plotly_chart(style(f, 440).update_layout(margin=dict(l=10, r=10, t=10, b=50)), width="stretch")
    with b:
        o = outlier_summary(d).assign(Share=lambda x: x["Potential outliers"] / x["Valid values"] * 100).sort_values("Share")
        f = go.Figure(go.Bar(x=o["Share"], y=o["Variable"], orientation="h", marker_color=BLUE,
                             text=[f"{s_:.1f}%  ({int(k):,} of {int(v):,})" for s_, k, v in zip(o["Share"], o["Potential outliers"], o["Valid values"])],
                             textposition="outside", cliponaxis=False))
        f.update_xaxes(title="% of values flagged by the IQR rule", range=[0, max(o["Share"].max() * 1.5, 5)], showgrid=True, gridcolor="#e8ecf3")
        f.update_yaxes(automargin=True)
        card("Potential outliers (IQR rule)", "Flags to review, not errors").plotly_chart(style(f, 440).update_layout(margin=dict(l=10, r=10, t=10, b=50)), width="stretch")
    st.download_button("Download cleaned data (CSV)", d.to_csv(index=False), "states_all_clean.csv", "text/csv")
