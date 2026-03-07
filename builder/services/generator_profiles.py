from __future__ import annotations

from ..models import ProjectTemplate


THEME_PROFILES = {
    ProjectTemplate.BLANK: {
        'label': 'Prototype Studio export',
        'page_icon': 'PS',
        'accent': '#1f6151',
        'accent_soft': '#e6f1ed',
        'accent_alt': '#5f877a',
        'ink': '#16211b',
        'hero_start': '#17362d',
        'hero_end': '#5f877a',
        'app_bg': 'linear-gradient(160deg, #f5f1ea 0%, #eef4f0 48%, #ebf1f6 100%)',
        'sidebar_bg': 'linear-gradient(180deg, rgba(15, 37, 32, 0.96) 0%, rgba(31, 97, 81, 0.94) 100%)',
        'surface_tint': 'rgba(255, 255, 255, 0.9)',
    },
    ProjectTemplate.QUOTE_BUILDER: {
        'label': 'Commercial quote prototype',
        'page_icon': 'QB',
        'accent': '#8b5e34',
        'accent_soft': '#f4e8d8',
        'accent_alt': '#b38251',
        'ink': '#24170d',
        'hero_start': '#4f321d',
        'hero_end': '#b38251',
        'app_bg': 'linear-gradient(160deg, #f7efe4 0%, #f7f2ea 45%, #eef4ee 100%)',
        'sidebar_bg': 'linear-gradient(180deg, rgba(58, 35, 19, 0.98) 0%, rgba(139, 94, 52, 0.94) 100%)',
        'surface_tint': 'rgba(255, 250, 245, 0.92)',
    },
    ProjectTemplate.CRM: {
        'label': 'Pipeline operations prototype',
        'page_icon': 'CRM',
        'accent': '#295f83',
        'accent_soft': '#e4eef5',
        'accent_alt': '#5b89a9',
        'ink': '#11202b',
        'hero_start': '#193447',
        'hero_end': '#5b89a9',
        'app_bg': 'linear-gradient(160deg, #eef3f7 0%, #edf5f6 46%, #f4f5ef 100%)',
        'sidebar_bg': 'linear-gradient(180deg, rgba(18, 35, 48, 0.98) 0%, rgba(41, 95, 131, 0.95) 100%)',
        'surface_tint': 'rgba(250, 252, 255, 0.92)',
    },
    ProjectTemplate.APPROVAL_FLOW: {
        'label': 'Decision flow prototype',
        'page_icon': 'AF',
        'accent': '#7f5b24',
        'accent_soft': '#f5ecd9',
        'accent_alt': '#ad8340',
        'ink': '#22180a',
        'hero_start': '#3a2a11',
        'hero_end': '#ad8340',
        'app_bg': 'linear-gradient(160deg, #f7f0e3 0%, #f2f0e8 44%, #ecf1f4 100%)',
        'sidebar_bg': 'linear-gradient(180deg, rgba(47, 32, 11, 0.98) 0%, rgba(127, 91, 36, 0.94) 100%)',
        'surface_tint': 'rgba(255, 252, 246, 0.92)',
    },
    ProjectTemplate.CASE_TRACKER: {
        'label': 'Casework prototype',
        'page_icon': 'CT',
        'accent': '#8a4d3d',
        'accent_soft': '#f2e5e0',
        'accent_alt': '#b17464',
        'ink': '#241511',
        'hero_start': '#4a261e',
        'hero_end': '#b17464',
        'app_bg': 'linear-gradient(160deg, #f8efec 0%, #f2f2ef 46%, #edf3f6 100%)',
        'sidebar_bg': 'linear-gradient(180deg, rgba(55, 27, 21, 0.98) 0%, rgba(138, 77, 61, 0.94) 100%)',
        'surface_tint': 'rgba(255, 250, 249, 0.92)',
    },
}


TEMPLATE_PROFILES = {
    ProjectTemplate.BLANK: {
        'nav_style': 'sidebar_radio',
        'dashboard_layout': 'metrics_grid',
        'dashboard_charts': [],
        'list_style': 'dataframe',
        'list_column_config': False,
        'detail_style': 'two_column',
        'form_style': 'inline',
        'use_toasts': False,
        'use_badges': False,
        'use_download': False,
        'logo_emoji': None,
        'css_variant': 'clean',
    },
    ProjectTemplate.QUOTE_BUILDER: {
        'nav_style': 'sidebar_pills',
        'dashboard_layout': 'financial_kpi',
        'dashboard_charts': ['bar_totals', 'state_dist'],
        'list_style': 'rich_dataframe',
        'list_column_config': True,
        'detail_style': 'tabbed',
        'form_style': 'dialog_create',
        'use_toasts': True,
        'use_badges': True,
        'use_download': True,
        'logo_emoji': ':page_with_curl:',
        'css_variant': 'warm_corporate',
    },
    ProjectTemplate.CRM: {
        'nav_style': 'top_pills',
        'dashboard_layout': 'pipeline_funnel',
        'dashboard_charts': ['area_pipeline', 'state_bar'],
        'list_style': 'rich_dataframe',
        'list_column_config': True,
        'detail_style': 'tabbed',
        'form_style': 'dialog_create',
        'use_toasts': True,
        'use_badges': True,
        'use_download': True,
        'logo_emoji': ':handshake:',
        'css_variant': 'cool_professional',
    },
    ProjectTemplate.APPROVAL_FLOW: {
        'nav_style': 'sidebar_radio',
        'dashboard_layout': 'status_board',
        'dashboard_charts': ['state_dist'],
        'list_style': 'grouped_expanders',
        'list_column_config': True,
        'detail_style': 'tabbed',
        'form_style': 'inline',
        'use_toasts': True,
        'use_badges': True,
        'use_download': False,
        'logo_emoji': ':white_check_mark:',
        'css_variant': 'formal_gold',
    },
    ProjectTemplate.CASE_TRACKER: {
        'nav_style': 'sidebar_segmented',
        'dashboard_layout': 'operations_hub',
        'dashboard_charts': ['line_trend', 'state_bar'],
        'list_style': 'rich_dataframe',
        'list_column_config': True,
        'detail_style': 'tabbed',
        'form_style': 'inline',
        'use_toasts': True,
        'use_badges': True,
        'use_download': True,
        'logo_emoji': ':mag:',
        'css_variant': 'warm_urgent',
    },
}


def get_theme_profile(kind: str) -> dict:
    return dict(THEME_PROFILES.get(kind, THEME_PROFILES[ProjectTemplate.BLANK]))


def get_template_profile(kind: str) -> dict:
    return dict(TEMPLATE_PROFILES.get(kind, TEMPLATE_PROFILES[ProjectTemplate.BLANK]))


def render_config_toml(spec: dict) -> str:
    kind = spec.get('template_kind', ProjectTemplate.BLANK)
    theme = get_theme_profile(kind)
    return (
        '[theme]\n'
        f'primaryColor = "{theme["accent"]}"\n'
        'backgroundColor = "#fafafa"\n'
        f'secondaryBackgroundColor = "{theme["accent_soft"]}"\n'
        f'textColor = "{theme["ink"]}"\n'
        'font = "sans serif"\n'
    )
