from __future__ import annotations


def build_css(theme: dict, profile: dict) -> str:
    variant = profile.get("css_variant", "clean")
    return _base_css(theme) + "\n" + _variant_css(theme, variant)


def _base_css(theme: dict) -> str:
    return f"""\
            :root {{
                --accent: {theme["accent"]};
                --accent-soft: {theme["accent_soft"]};
                --accent-alt: {theme["accent_alt"]};
                --ink: {theme["ink"]};
                --surface: {theme["surface_tint"]};
                --hero-start: {theme["hero_start"]};
                --hero-end: {theme["hero_end"]};
            }}
            .stApp {{
                background: {theme["app_bg"]};
                color: var(--ink);
            }}
            .main .block-container {{
                max-width: 1180px;
                padding-top: 1.8rem;
                padding-bottom: 3rem;
            }}
            [data-testid="stSidebar"] > div:first-child {{
                background: {theme["sidebar_bg"]};
                color: rgba(255, 255, 255, 0.94);
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }}
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] div {{
                color: rgba(255, 255, 255, 0.92);
            }}
            [data-testid="stSidebar"] .stMetric {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                box-shadow: none;
            }}
            [data-testid="stSidebar"] .stMetric label,
            [data-testid="stSidebar"] .stMetric div {{
                color: rgba(255, 255, 255, 0.94);
            }}
            .studio-brand {{
                margin-bottom: 1rem;
                padding: 1.1rem 1rem;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 26px;
                background: rgba(255, 255, 255, 0.08);
            }}
            .studio-brand span,
            .sidebar-label,
            .hero-eyebrow,
            .section-label {{
                display: block;
                margin: 0 0 0.45rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                font-size: 0.74rem;
                font-weight: 700;
                opacity: 0.86;
            }}
            .studio-brand h2 {{
                margin: 0 0 0.45rem;
                font-size: 1.35rem;
                line-height: 1.1;
            }}
            .studio-brand p {{
                margin: 0;
                font-size: 0.9rem;
                opacity: 0.82;
            }}
            .hero-header {{
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
                padding: 1.5rem 1.6rem;
                border-radius: 30px;
                background: linear-gradient(135deg, var(--hero-start), var(--hero-end));
                color: white;
                box-shadow: 0 28px 60px rgba(17, 24, 39, 0.14);
                margin-bottom: 1rem;
            }}
            .hero-copy h1 {{
                margin: 0;
                font-size: 2.35rem;
                line-height: 1.02;
                letter-spacing: -0.04em;
            }}
            .hero-copy p:last-child {{
                max-width: 42rem;
                margin: 0.65rem 0 0;
                font-size: 0.98rem;
                line-height: 1.5;
                opacity: 0.88;
            }}
            .hero-badge-row,
            .workflow-strip {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
            }}
            .hero-badge {{
                display: inline-flex;
                align-items: center;
                min-height: 2rem;
                padding: 0.45rem 0.75rem;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.12);
                font-size: 0.82rem;
                font-weight: 600;
            }}
            [data-testid="stMetric"],
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {{
                background: var(--surface);
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 24px;
                box-shadow: 0 18px 40px rgba(17, 24, 39, 0.06);
            }}
            [data-testid="stMetric"] {{
                padding: 0.7rem 0.85rem;
            }}
            [data-testid="stMetric"] label {{
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }}
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {{
                padding: 1rem 1.05rem;
            }}
            .entity-card p:first-child,
            .detail-card span,
            .readout-card span,
            .info-panel span,
            .glance-head p {{
                margin: 0;
                color: rgba(22, 33, 27, 0.62);
                font-size: 0.78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }}
            .entity-card strong,
            .detail-card strong,
            .readout-card strong,
            .info-panel strong {{
                display: block;
                margin: 0.45rem 0 0.2rem;
                font-size: 1.5rem;
                line-height: 1.1;
                color: var(--ink);
            }}
            .entity-card span {{
                display: block;
                margin-bottom: 0.4rem;
                color: rgba(22, 33, 27, 0.62);
                font-size: 0.86rem;
            }}
            .glance-head {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
                margin-bottom: 0.5rem;
            }}
            .glance-card h3 {{
                margin: 0 0 0.8rem;
                font-size: 1.2rem;
            }}
            .glance-list,
            .plain-list {{
                margin: 0.7rem 0 0;
                padding: 0;
                list-style: none;
                display: grid;
                gap: 0.45rem;
            }}
            .glance-list li,
            .plain-list li {{
                display: flex;
                justify-content: space-between;
                gap: 0.75rem;
                font-size: 0.88rem;
                color: rgba(22, 33, 27, 0.72);
            }}
            .glance-list li strong,
            .plain-list li strong {{
                margin: 0;
                font-size: 0.9rem;
            }}
            .readout-card strong {{
                font-size: 1.85rem;
            }}
            .workflow-strip {{
                margin-bottom: 1rem;
            }}
            .workflow-pill {{
                display: inline-flex;
                align-items: center;
                min-height: 2rem;
                padding: 0.4rem 0.75rem;
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.72);
                color: rgba(22, 33, 27, 0.7);
                font-size: 0.82rem;
                font-weight: 700;
            }}
            .workflow-pill-start {{
                background: var(--accent-soft);
                border-color: rgba(31, 97, 81, 0.18);
                color: var(--accent);
            }}
            .workflow-pill-terminal {{
                background: rgba(17, 24, 39, 0.08);
                color: var(--ink);
            }}
            .section-label {{
                color: rgba(22, 33, 27, 0.55);
                margin-top: 1.3rem;
            }}
            .empty-state-card h3 {{
                margin: 0 0 0.35rem;
            }}
            .empty-state-card p,
            .info-panel p,
            .readout-card p,
            .entity-card p:last-child {{
                margin: 0;
                color: rgba(22, 33, 27, 0.68);
                line-height: 1.5;
            }}
            .stButton > button {{
                border-radius: 999px;
                border: 0;
                background: linear-gradient(135deg, var(--hero-start), var(--hero-end));
                color: white;
                font-weight: 700;
                min-height: 2.9rem;
                padding: 0.7rem 1.2rem;
                box-shadow: 0 18px 30px rgba(17, 24, 39, 0.12);
            }}
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input,
            .stSelectbox > div > div,
            .stMultiSelect > div > div {{
                border-radius: 18px !important;
                border-color: rgba(17, 24, 39, 0.09) !important;
                background: rgba(255, 255, 255, 0.92) !important;
            }}
            .stDataFrame,
            [data-testid="stDataFrame"] {{
                border-radius: 24px;
                overflow: hidden;
                border: 1px solid rgba(17, 24, 39, 0.08);
                box-shadow: 0 18px 40px rgba(17, 24, 39, 0.06);
            }}
            .stRadio > div {{
                background: rgba(255, 255, 255, 0.66);
                border-radius: 18px;
                padding: 0.35rem 0.45rem;
            }}
            @media (max-width: 900px) {{
                .hero-header {{
                    flex-direction: column;
                }}
                .hero-copy h1 {{
                    font-size: 1.95rem;
                }}
            }}"""


def _variant_css(theme: dict, variant: str) -> str:
    builders = {
        "clean": _variant_clean,
        "warm_corporate": _variant_warm_corporate,
        "cool_professional": _variant_cool_professional,
        "formal_gold": _variant_formal_gold,
        "warm_urgent": _variant_warm_urgent,
    }
    builder = builders.get(variant, _variant_clean)
    return builder(theme)


def _variant_clean(theme: dict) -> str:
    return ""


def _variant_warm_corporate(theme: dict) -> str:
    return f"""
            [data-testid="stMetric"],
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {{
                border-radius: 22px;
                box-shadow: 0 22px 48px rgba(17, 24, 39, 0.09);
                border-top: 3px solid {theme["accent"]};
            }}
            .hero-header {{
                border-radius: 26px;
            }}
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input,
            .stSelectbox > div > div,
            .stMultiSelect > div > div {{
                border-radius: 16px !important;
            }}
            .stDataFrame,
            [data-testid="stDataFrame"] {{
                border-radius: 22px;
            }}"""


def _variant_cool_professional(theme: dict) -> str:
    return """
            .main .block-container {
                max-width: 1400px;
            }
            [data-testid="stMetric"],
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {
                border-radius: 14px;
                border: 1px solid rgba(41, 95, 131, 0.12);
                box-shadow: 0 8px 24px rgba(17, 24, 39, 0.05);
            }
            .hero-header {
                border-radius: 18px;
            }
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input,
            .stSelectbox > div > div,
            .stMultiSelect > div > div {
                border-radius: 12px !important;
            }
            .stDataFrame,
            [data-testid="stDataFrame"] {
                border-radius: 14px;
            }
            .studio-brand {
                border-radius: 14px;
            }"""


def _variant_formal_gold(theme: dict) -> str:
    return f"""
            [data-testid="stMetric"],
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {{
                border-radius: 8px;
                border-left: 4px solid {theme["accent"]};
                box-shadow: 0 6px 18px rgba(17, 24, 39, 0.06);
            }}
            .hero-header {{
                border-radius: 10px;
            }}
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input,
            .stSelectbox > div > div,
            .stMultiSelect > div > div {{
                border-radius: 8px !important;
            }}
            .stDataFrame,
            [data-testid="stDataFrame"] {{
                border-radius: 8px;
            }}
            .studio-brand {{
                border-radius: 8px;
            }}
            .stButton > button {{
                border-radius: 8px;
            }}
            .hero-badge,
            .workflow-pill {{
                border-radius: 6px;
            }}
            .entity-card strong,
            .detail-card strong,
            .readout-card strong,
            .info-panel strong {{
                font-weight: 800;
            }}"""


def _variant_warm_urgent(theme: dict) -> str:
    return f"""
            [data-testid="stMetric"],
            .entity-card,
            .glance-card,
            .detail-card,
            .readout-card,
            .info-panel,
            .empty-state-card {{
                border-radius: 12px;
                border-left: 4px solid {theme["accent"]};
                padding: 0.85rem 1rem;
            }}
            .hero-header {{
                border-radius: 14px;
            }}
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input,
            .stSelectbox > div > div,
            .stMultiSelect > div > div {{
                border-radius: 12px !important;
            }}
            .stDataFrame,
            [data-testid="stDataFrame"] {{
                border-radius: 12px;
            }}
            .studio-brand {{
                border-radius: 12px;
            }}"""
