import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import time
import logging
import os
import threading
import random
import base64
import traceback
import openai
import re
import difflib
from datetime import datetime, timedelta
from io import BytesIO
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("impactguard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImpactGuard")

# Set page configuration with custom theme
st.set_page_config(
    page_title="ImpactGuard - AI Security & Sustainability Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Setup OpenAI API key securely (for reporting functionality)
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    logger.warning("OpenAI API key not found in secrets. Some features may be limited.")

# ----------------------------------------------------------------
# Session State Management
# ----------------------------------------------------------------

def initialize_session_state():
    """Initialize all session state variables with proper error handling"""
    try:
        # Core session states
        if 'targets' not in st.session_state:
            st.session_state.targets = []

        if 'test_results' not in st.session_state:
            st.session_state.test_results = {}

        if 'running_test' not in st.session_state:
            st.session_state.running_test = False

        if 'progress' not in st.session_state:
            st.session_state.progress = 0

        if 'vulnerabilities_found' not in st.session_state:
            st.session_state.vulnerabilities_found = 0

        if 'current_theme' not in st.session_state:
            st.session_state.current_theme = "dark"  # Default to dark theme
            
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"

        # Thread management
        if 'active_threads' not in st.session_state:
            st.session_state.active_threads = []
            
        # Error handling
        if 'error_message' not in st.session_state:
            st.session_state.error_message = None
            
        # Initialize bias testing state
        if 'bias_results' not in st.session_state:
            st.session_state.bias_results = {}
            
        if 'show_bias_results' not in st.session_state:
            st.session_state.show_bias_results = False
            
        # Carbon tracking states
        if 'carbon_tracking_active' not in st.session_state:
            st.session_state.carbon_tracking_active = False
            
        if 'carbon_measurements' not in st.session_state:
            st.session_state.carbon_measurements = []

        # Citation tool states
        if 'VALIDATION_STRICTNESS' not in st.session_state:
            st.session_state.VALIDATION_STRICTNESS = 2
            
        # Reporting states
        if 'reports' not in st.session_state:
            st.session_state.reports = []
            
        # Insight report states
        if 'insights' not in st.session_state:
            st.session_state.insights = []
            
        logger.info("Session state initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing session state: {str(e)}")
        display_error(f"Failed to initialize application state: {str(e)}")

# Thread cleanup
def cleanup_threads():
    """Remove completed threads from session state"""
    try:
        if 'active_threads' in st.session_state:
            # Filter out completed threads
            active_threads = []
            for thread in st.session_state.active_threads:
                if thread.is_alive():
                    active_threads.append(thread)
            
            # Update session state with only active threads
            st.session_state.active_threads = active_threads
            
            if len(st.session_state.active_threads) > 0:
                logger.info(f"Active threads: {len(st.session_state.active_threads)}")
    except Exception as e:
        logger.error(f"Error cleaning up threads: {str(e)}")

# ----------------------------------------------------------------
# UI Theme & Styling
# ----------------------------------------------------------------

# Define color schemes
themes = {
    "dark": {
        "bg_color": "#121212",
        "card_bg": "#1E1E1E",
        "primary": "#003b7a",    # ImpactGuard blue
        "secondary": "#BB86FC",  # Purple
        "accent": "#03DAC6",     # Teal
        "warning": "#FF9800",    # Orange
        "error": "#CF6679",      # Red
        "text": "#FFFFFF"
    },
    "light": {
        "bg_color": "#F5F5F5",
        "card_bg": "#FFFFFF",
        "primary": "#003b7a",    # ImpactGuard blue
        "secondary": "#7C4DFF",  # Deep purple
        "accent": "#00BCD4",     # Cyan
        "warning": "#FF9800",    # Orange
        "error": "#F44336",      # Red
        "text": "#212121"
    }
}

# Get current theme colors safely
def get_theme():
    """Get current theme with error handling"""
    try:
        return themes[st.session_state.current_theme]
    except Exception as e:
        logger.error(f"Error getting theme: {str(e)}")
        # Return dark theme as fallback
        return themes["dark"]

# CSS styles
def load_css():
    """Load CSS with the current theme"""
    try:
        theme = get_theme()
        
        return f"""
        <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: {theme["primary"]};
        }}
        
        .stProgress > div > div > div > div {{
            background-color: {theme["primary"]};
        }}
        
        div[data-testid="stExpander"] {{
            border: none;
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            margin-bottom: 1rem;
        }}
        
        div[data-testid="stVerticalBlock"] {{
            gap: 1.5rem;
        }}
        
        .card {{
            border-radius: 10px;
            background-color: {theme["card_bg"]};
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border-left: 3px solid {theme["primary"]};
        }}
        
        .warning-card {{
            border-left: 3px solid {theme["warning"]};
        }}
        
        .error-card {{
            border-left: 3px solid {theme["error"]};
        }}
        
        .success-card {{
            border-left: 3px solid {theme["primary"]};
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .metric-label {{
            font-size: 14px;
            color: {theme["text"]};
            opacity: 0.7;
        }}
        
        .sidebar-title {{
            margin-left: 15px;
            font-size: 1.2rem;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .target-card {{
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 3px solid {theme["secondary"]};
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .status-badge.active {{
            background-color: {theme["primary"]};
            color: white;
        }}
        
        .status-badge.inactive {{
            background-color: gray;
            color: white;
        }}
        
        .hover-card:hover {{
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }}
        
        .card-title {{
            color: {theme["primary"]};
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .nav-item {{
            padding: 8px 15px;
            border-radius: 5px;
            margin-bottom: 5px;
            cursor: pointer;
        }}
        
        .nav-item:hover {{
            background-color: rgba(0, 59, 122, 0.1);
        }}
        
        .nav-item.active {{
            background-color: rgba(0, 59, 122, 0.2);
            font-weight: bold;
        }}
        
        .tag {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 5px;
            margin-bottom: 5px;
        }}
        
        .tag.owasp {{
            background-color: rgba(187, 134, 252, 0.2);
            color: {theme["secondary"]};
        }}
        
        .tag.nist {{
            background-color: rgba(3, 218, 198, 0.2);
            color: {theme["accent"]};
        }}
        
        .tag.fairness {{
            background-color: rgba(255, 152, 0, 0.2);
            color: {theme["warning"]};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            border-radius: 5px 5px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {theme["card_bg"]};
            border-bottom: 3px solid {theme["primary"]};
        }}
        
        .error-message {{
            background-color: #CF6679;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        /* Modern sidebar styling */
        section[data-testid="stSidebar"] {{
            background-color: {theme["card_bg"]};
            border-right: 1px solid rgba(0,0,0,0.1);
        }}
        
        /* Modern navigation categories */
        .nav-category {{
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            color: {theme["text"]};
            opacity: 0.6;
            margin: 10px 15px 5px 15px;
        }}
        
        /* Main content area padding */
        .main-content {{
            padding: 20px;
        }}
        
        /* Modern cards with hover effects */
        .modern-card {{
            background-color: {theme["card_bg"]};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            transition: all 0.3s ease;
            border-left: none;
            border-top: 4px solid {theme["primary"]};
        }}
        
        .modern-card:hover {{
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            transform: translateY(-5px);
        }}
        
        .modern-card.warning {{
            border-top: 4px solid {theme["warning"]};
        }}
        
        .modern-card.error {{
            border-top: 4px solid {theme["error"]};
        }}
        
        .modern-card.secondary {{
            border-top: 4px solid {theme["secondary"]};
        }}
        
        .modern-card.accent {{
            border-top: 4px solid {theme["accent"]};
        }}
        
        /* App header styles */
        .app-header {{
            display: flex;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .app-title {{
            font-size: 24px;
            font-weight: bold;
            margin: 0;
            color: {theme["primary"]};
        }}
        
        .app-subtitle {{
            font-size: 14px;
            opacity: 0.7;
            margin: 0;
        }}
        </style>
        """
    except Exception as e:
        logger.error(f"Error loading CSS: {str(e)}")
        # Return minimal CSS as fallback
        return "<style>.error-message { background-color: #CF6679; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }</style>"

# ----------------------------------------------------------------
# Navigation and Control
# ----------------------------------------------------------------

# Helper function to set page
def set_page(page_name):
    """Set the current page safely"""
    try:
        st.session_state.current_page = page_name
        logger.info(f"Navigation: Switched to {page_name} page")
    except Exception as e:
        logger.error(f"Error setting page to {page_name}: {str(e)}")
        display_error(f"Failed to navigate to {page_name}")

# Safe rerun function
def safe_rerun():
    """Safely rerun the app, handling different Streamlit versions"""
    try:
        st.rerun()  # For newer Streamlit versions
    except Exception as e1:
        try:
            st.experimental_rerun()  # For older Streamlit versions
        except Exception as e2:
            logger.error(f"Failed to rerun app: {str(e1)} then {str(e2)}")
            # Do nothing - at this point we can't fix it

# Error handling
def display_error(message):
    """Display error message to the user"""
    try:
        st.session_state.error_message = message
        logger.error(f"UI Error: {message}")
    except Exception as e:
        logger.critical(f"Failed to display error message: {str(e)}")

# ----------------------------------------------------------------
# Custom UI Components
# ----------------------------------------------------------------

# Custom components
def card(title, content, card_type="default"):
    """Generate HTML card with error handling"""
    try:
        card_class = "card"
        if card_type == "warning":
            card_class += " warning-card"
        elif card_type == "error":
            card_class += " error-card"
        elif card_type == "success":
            card_class += " success-card"
        
        return f"""
        <div class="{card_class} hover-card">
            <div class="card-title">{title}</div>
            {content}
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering card: {str(e)}")
        return f"""
        <div class="card error-card">
            <div class="card-title">Error Rendering Card</div>
            <p>Failed to render card content: {str(e)}</p>
        </div>
        """

def modern_card(title, content, card_type="default", icon=None):
    """Generate a modern style card with optional icon"""
    try:
        card_class = "modern-card"
        if card_type == "warning":
            card_class += " warning"
        elif card_type == "error":
            card_class += " error"
        elif card_type == "secondary":
            card_class += " secondary"
        elif card_type == "accent":
            card_class += " accent"
        
        icon_html = f'<span style="margin-right: 8px;">{icon}</span>' if icon else ''
        
        return f"""
        <div class="{card_class}">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                {icon_html}
                <div class="card-title">{title}</div>
            </div>
            <div>{content}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering modern card: {str(e)}")
        return f"""
        <div class="modern-card error">
            <div class="card-title">Error Rendering Card</div>
            <p>Failed to render card content: {str(e)}</p>
        </div>
        """

def metric_card(label, value, description="", prefix="", suffix=""):
    """Generate HTML metric card with error handling"""
    try:
        return f"""
        <div class="modern-card hover-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{prefix}{value}{suffix}</div>
            <div style="font-size: 14px; opacity: 0.7;">{description}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering metric card: {str(e)}")
        return f"""
        <div class="modern-card error">
            <div class="metric-label">Error</div>
            <div class="metric-value">N/A</div>
            <div style="font-size: 14px; opacity: 0.7;">Failed to render metric: {str(e)}</div>
        </div>
        """

# Logo and header
def render_header():
    """Render the application header safely"""
    try:
        logo_html = """
        <div class="app-header">
            <div style="margin-right: 15px; width: 38px; height: 38px;">
                <svg width="38" height="38" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                    <path d="M100 10 L180 50 V120 C180 150 150 180 100 190 C50 180 20 150 20 120 V50 L100 10Z" fill="#003b7a" />
                    <path d="M75 70 C95 70 110 125 140 110" stroke="white" strokeWidth="15" fill="none" />
                </svg>
            </div>
            <div>
                <div class="app-title">ImpactGuard</div>
                <div class="app-subtitle">Supercharging progress in AI Ethics and Governance – ORAIG</div>
            </div>
        </div>
        """
        st.markdown(logo_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering header: {str(e)}")
        st.markdown("# 🛡️ ImpactGuard")

# ----------------------------------------------------------------
# Sidebar Navigation
# ----------------------------------------------------------------

def sidebar_navigation():
    """Render the sidebar navigation with organized categories"""
    try:
        st.sidebar.markdown("""
        <div style="display: flex; align-items: center; padding: 1rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div style="margin-right: 10px;">
                <svg width="28" height="28" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                    <path d="M100 10 L180 50 V120 C180 150 150 180 100 190 C50 180 20 150 20 120 V50 L100 10Z" fill="#003b7a" />
                    <path d="M75 70 C95 70 110 125 140 110" stroke="white" strokeWidth="15" fill="none" />
                </svg>
            </div>
            <div>
                <div style="font-weight: bold; font-size: 1.2rem; color: #4299E1;">ImpactGuard</div>
                <div style="font-size: 0.7rem; opacity: 0.7;">By HCLTech</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Organize navigation options by category
        navigation_categories = {
            "Core Security": [
                {"icon": "🏠", "name": "Dashboard"},
                {"icon": "🎯", "name": "Target Management"},
                {"icon": "🧪", "name": "Test Configuration"},
                {"icon": "▶️", "name": "Run Assessment"},
                {"icon": "📊", "name": "Results Analyzer"}
            ],
            "AI Ethics & Bias": [
                {"icon": "🔍", "name": "Ethical AI Testing"},
                {"icon": "⚖️", "name": "Bias Testing"},
                {"icon": "📏", "name": "Bias Comparison"},
                {"icon": "🧠", "name": "HELM Evaluation"}
            ],
            "Sustainability": [
                {"icon": "🌱", "name": "Environmental Impact"},
                {"icon": "🌍", "name": "Sustainability Dashboard"}
            ],
            "Reports & Knowledge": [
                {"icon": "📝", "name": "Report Generator"},
                {"icon": "📚", "name": "Citation Tool"},
                {"icon": "💡", "name": "Insight Assistant"}
            ],
            "Integration & Tools": [
                {"icon": "📁", "name": "Multi-Format Import"},
                {"icon": "🚀", "name": "High-Volume Testing"},
                {"icon": "📚", "name": "Knowledge Base"}
            ],
            "System": [
                {"icon": "⚙️", "name": "Settings"}
            ]
        }
        
        # Render each category and its navigation options
        for category, options in navigation_categories.items():
            st.sidebar.markdown(f'<div class="nav-category">{category}</div>', unsafe_allow_html=True)
            
            for option in options:
                # Create a button for each navigation option
                if st.sidebar.button(
                    f"{option['icon']} {option['name']}", 
                    key=f"nav_{option['name']}",
                    use_container_width=True,
                    type="secondary" if st.session_state.current_page != option["name"] else "primary"
                ):
                    set_page(option["name"])
                    safe_rerun()
        
        # Theme toggle
        st.sidebar.markdown("---")
        if st.sidebar.button("🔄 Toggle Theme", key="toggle_theme", use_container_width=True):
            st.session_state.current_theme = "light" if st.session_state.current_theme == "dark" else "dark"
            logger.info(f"Theme toggled to {st.session_state.current_theme}")
            safe_rerun()
        
        # System status
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="sidebar-title">📡 System Status</div>', unsafe_allow_html=True)
        
        if st.session_state.running_test:
            st.sidebar.success("⚡ Test Running")
        else:
            st.sidebar.info("⏸️ Idle")
        
        st.sidebar.markdown(f"🎯 Targets: {len(st.session_state.targets)}")
        
        # Active threads info
        if len(st.session_state.active_threads) > 0:
            st.sidebar.markdown(f"🧵 Active threads: {len(st.session_state.active_threads)}")
        
        # Add carbon tracking status if active
        if st.session_state.get("carbon_tracking_active", False):
            st.sidebar.markdown("🌱 Carbon tracking active")
        
        # Add version info
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"v1.0.0 | {datetime.now().strftime('%Y-%m-%d')}", unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering sidebar: {str(e)}")
        st.sidebar.error("Navigation Error")
        st.sidebar.markdown(f"Error: {str(e)}")

# ----------------------------------------------------------------
# Utility Classes and Functions (Common)
# ----------------------------------------------------------------

# Mock data functions with error handling
def get_mock_test_vectors():
    """Get mock test vector data with error handling"""
    try:
        return [
            {
                "id": "sql_injection",
                "name": "SQL Injection",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "xss",
                "name": "Cross-Site Scripting",
                "category": "owasp",
                "severity": "medium"
            },
            {
                "id": "prompt_injection",
                "name": "Prompt Injection",
                "category": "owasp",
                "severity": "critical"
            },
            {
                "id": "insecure_output",
                "name": "Insecure Output Handling",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "nist_governance",
                "name": "AI Governance",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "nist_transparency",
                "name": "Transparency",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "fairness_demographic",
                "name": "Demographic Parity",
                "category": "fairness",
                "severity": "high"
            },
            {
                "id": "privacy_gdpr",
                "name": "GDPR Compliance",
                "category": "privacy",
                "severity": "critical"
            },
            {
                "id": "jailbreaking",
                "name": "Jailbreaking Resistance",
                "category": "exploit",
                "severity": "critical"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting mock test vectors: {str(e)}")
        display_error("Failed to load test vectors")
        return []  # Return empty list as fallback

def run_mock_test(target, test_vectors, duration=30):
    """Simulate running a test in the background with proper error handling"""
    try:
        # Initialize progress
        st.session_state.progress = 0
        st.session_state.vulnerabilities_found = 0
        st.session_state.running_test = True
        
        logger.info(f"Starting mock test against {target['name']} with {len(test_vectors)} test vectors")
        
        # Create mock results data structure
        results = {
            "summary": {
                "total_tests": 0,
                "vulnerabilities_found": 0,
                "risk_score": 0
            },
            "vulnerabilities": [],
            "test_details": {}
        }
        
        # Simulate test execution
        total_steps = 100
        step_sleep = duration / total_steps
        
        for i in range(total_steps):
            # Check if we should stop (for handling cancellations)
            if not st.session_state.running_test:
                logger.info("Test was cancelled")
                break
                
            time.sleep(step_sleep)
            st.session_state.progress = (i + 1) / total_steps
            
            # Occasionally "find" a vulnerability
            if random.random() < 0.2:  # 20% chance each step
                vector = random.choice(test_vectors)
                severity_weight = {"low": 1, "medium": 2, "high": 3, "critical": 5}
                weight = severity_weight.get(vector["severity"], 1)
                
                # Add vulnerability to results
                vulnerability = {
                    "id": f"VULN-{len(results['vulnerabilities']) + 1}",
                    "test_vector": vector["id"],
                    "test_name": vector["name"],
                    "severity": vector["severity"],
                    "details": f"Mock vulnerability found in {target['name']} using {vector['name']} test vector.",
                    "timestamp": datetime.now().isoformat()
                }
                results["vulnerabilities"].append(vulnerability)
                
                # Update counters
                st.session_state.vulnerabilities_found += 1
                results["summary"]["vulnerabilities_found"] += 1
                results["summary"]["risk_score"] += weight
                
                logger.info(f"Found vulnerability: {vulnerability['id']} ({vulnerability['severity']})")
        
        # Complete the test results
        results["summary"]["total_tests"] = len(test_vectors) * 10  # Assume 10 variations per vector
        results["timestamp"] = datetime.now().isoformat()
        results["target"] = target["name"]
        
        logger.info(f"Test completed: {results['summary']['vulnerabilities_found']} vulnerabilities found")
        
        # Set the results in session state
        st.session_state.test_results = results
        return results
    
    except Exception as e:
        error_details = {
            "error": True,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        logger.error(f"Error in test execution: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Create error result
        st.session_state.error_message = f"Test execution failed: {str(e)}"
        return error_details
# Continuing from previous code block
                                severity_color = {
                                    "low": "blue",
                                    "medium": "orange",
                                    "high": "red",
                                    "critical": "darkred"
                                }.get(insight_data["severity"], "gray")
                                
                                st.markdown(f"""
                                <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                                    <div style="font-weight: bold;">{insight_data["vulnerability_id"]}: {insight_data["vulnerability_name"]}</div>
                                    <div>{insight_data["insight"]}</div>
                                    <div style="font-size: 0.8em; opacity: 0.7;">Severity: {insight_data["severity"].upper()}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Export option
                            insights_df = pd.DataFrame(insights)
                            st.download_button(
                                "Export Insights",
                                insights_df.to_csv(index=False).encode('utf-8'),
                                file_name="security_insights.csv",
                                mime="text/csv"
                            )
                else:
                    st.warning("No vulnerabilities found in current test results.")
            else:
                st.error("No test results available. Please run a security assessment first.")
        
        # Option 2: Upload CSV data
        st.markdown("### Or Upload CSV Data")
        
        # Sample data for download
        sample_data = "User,Category,Prompt,Response\nJohn Doe,Security,How secure is our API?,Several vulnerabilities were found\nJane Smith,Performance,Is the model efficient?,Response time averages 200ms"
        
        st.download_button(
            "Download Sample CSV",
            sample_data,
            "sample_insights.csv",
            "text/csv",
            key="download_sample_insights"
        )
        
        uploaded_file = st.file_uploader("Upload CSV", type="csv", key="upload_insights_csv")
        
        if uploaded_file:
            df = process_csv(uploaded_file)
            if df is not None:
                st.success("CSV uploaded successfully!")
                st.dataframe(df.head())
                
                if st.button("Generate Insights from CSV", key="gen_csv_insights"):
                    with st.spinner("Generating insights..."):
                        insights = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, row in df.iterrows():
                            status_text.text(f"Processing {idx + 1}/{len(df)}")
                            
                            insight = generate_insight(
                                row['User'],
                                row['Category'],
                                row['Prompt'],
                                row['Response'],
                                knowledge_base_input,
                                context_input,
                                temperature,
                                max_tokens
                            )
                            
                            insights.append(insight)
                            progress_bar.progress((idx + 1) / len(df))
                        
                        # Add insights to dataframe
                        df['Generated Insight'] = insights
                        status_text.text("Processing complete!")
                        
                        # Store in session state
                        if 'insights_dataframes' not in st.session_state:
                            st.session_state.insights_dataframes = []
                        
                        st.session_state.insights_dataframes.append({
                            "name": uploaded_file.name,
                            "data": df
                        })
                        
                        # Show results
                        st.success("Insights generated successfully!")
                        st.dataframe(df)
                        
                        # Export options
                        st.download_button(
                            "Download Results CSV",
                            df.to_csv(index=False).encode('utf-8'),
                            "insights_report.csv",
                            "text/csv",
                            key="download_insights_report"
                        )
        
        # Option 3: Manual entry
        st.markdown("### Or Enter Data Manually")
        
        with st.form("manual_insight_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                manual_user = st.text_input("User/Role", key="manual_insight_user")
                manual_category = st.text_input("Category", key="manual_insight_category")
            
            with col2:
                manual_prompt = st.text_input("Prompt/Question", key="manual_insight_prompt")
                manual_response = st.text_area("Response/Data", key="manual_insight_response", height=100)
            
            submit_button = st.form_submit_button("Generate Insight")
        
        if submit_button:
            if not manual_user or not manual_category or not manual_prompt or not manual_response:
                st.error("All fields are required")
            else:
                with st.spinner("Generating insight..."):
                    insight = generate_insight(
                        manual_user,
                        manual_category,
                        manual_prompt,
                        manual_response,
                        knowledge_base_input,
                        context_input,
                        temperature,
                        max_tokens
                    )
                    
                    # Store the insight
                    if 'manual_insights' not in st.session_state:
                        st.session_state.manual_insights = []
                    
                    st.session_state.manual_insights.append({
                        "user": manual_user,
                        "category": manual_category,
                        "prompt": manual_prompt,
                        "response": manual_response,
                        "insight": insight,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Show result
                    st.success("Insight generated successfully!")
                    
                    st.markdown("### Generated Insight")
                    st.markdown(f"""
                    <div style="padding: 15px; border-left: 4px solid {get_theme()["primary"]}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{manual_category} Insight</div>
                        <div>{insight}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Generated for: {manual_user}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # View previous insights
        if (('insights' in st.session_state and st.session_state.insights) or 
            ('manual_insights' in st.session_state and st.session_state.manual_insights) or
            ('insights_dataframes' in st.session_state and st.session_state.insights_dataframes)):
            
            st.markdown("### Previous Insights")
            
            insight_sources = []
            
            if 'insights' in st.session_state and st.session_state.insights:
                insight_sources.append("Security Test Insights")
            
            if 'manual_insights' in st.session_state and st.session_state.manual_insights:
                insight_sources.append("Manual Insights")
            
            if 'insights_dataframes' in st.session_state and st.session_state.insights_dataframes:
                for df_info in st.session_state.insights_dataframes:
                    insight_sources.append(f"CSV: {df_info['name']}")
            
            selected_source = st.selectbox("Select Source", insight_sources, key="insight_source_select")
            
            if selected_source == "Security Test Insights" and 'insights' in st.session_state:
                insights = st.session_state.insights
                
                for i, insight_data in enumerate(insights):
                    severity_color = {
                        "low": "blue",
                        "medium": "orange",
                        "high": "red",
                        "critical": "darkred"
                    }.get(insight_data["severity"], "gray")
                    
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{insight_data["vulnerability_id"]}: {insight_data["vulnerability_name"]}</div>
                        <div>{insight_data["insight"]}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Severity: {insight_data["severity"].upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif selected_source == "Manual Insights" and 'manual_insights' in st.session_state:
                manual_insights = st.session_state.manual_insights
                
                for i, insight_data in enumerate(manual_insights):
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 4px solid {get_theme()["primary"]}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{insight_data["category"]} Insight</div>
                        <div>{insight_data["insight"]}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Generated for: {insight_data["user"]} on {insight_data["timestamp"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif selected_source.startswith("CSV:") and 'insights_dataframes' in st.session_state:
                csv_name = selected_source[5:].strip()
                
                for df_info in st.session_state.insights_dataframes:
                    if df_info["name"] == csv_name:
                        st.dataframe(df_info["data"])
                        break
    
    except Exception as e:
        logger.error(f"Error rendering insight assistant: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in insight assistant: {str(e)}")

# ----------------------------------------------------------------
# Main Application Routing
# ----------------------------------------------------------------

def main():
    """Main application entry point with error handling"""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Clean up threads
        cleanup_threads()
        
        # Apply CSS
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # Show error message if exists
        if st.session_state.error_message:
            st.markdown(f"""
            <div class="error-message">
                <strong>Error:</strong> {st.session_state.error_message}
            </div>
            """, unsafe_allow_html=True)
            
            # Add button to clear error
            if st.button("Clear Error"):
                st.session_state.error_message = None
                safe_rerun()
        
        # Render sidebar
        sidebar_navigation()
        
        # Render content based on current page
        if st.session_state.current_page == "Dashboard":
            render_dashboard()
        elif st.session_state.current_page == "Target Management":
            render_target_management()
        elif st.session_state.current_page == "Test Configuration":
            render_test_configuration()
        elif st.session_state.current_page == "Run Assessment":
            render_run_assessment()
        elif st.session_state.current_page == "Results Analyzer":
            render_results_analyzer()
        elif st.session_state.current_page == "Ethical AI Testing":
            render_ethical_ai_testing()
        elif st.session_state.current_page == "Environmental Impact":
            render_environmental_impact()
        elif st.session_state.current_page == "Bias Testing":
            render_bias_testing()
        elif st.session_state.current_page == "Bias Comparison":
            render_bias_comparison()
        elif st.session_state.current_page == "Bias Labs Integration":
            render_bias_labs_integration()
        elif st.session_state.current_page == "HELM Evaluation":
            render_helm_evaluation()
        elif st.session_state.current_page == "Multi-Format Import":
            render_file_import()
        elif st.session_state.current_page == "High-Volume Testing":
            render_high_volume_testing()
        elif st.session_state.current_page == "Sustainability Dashboard":
            render_sustainability_dashboard()
        elif st.session_state.current_page == "Sustainability Integration":
            render_sustainability_integration()
        elif st.session_state.current_page == "Engine Room Integration":
            render_engine_room_integration()
        elif st.session_state.current_page == "Knowledge Base":
            render_knowledge_base_integration()
        elif st.session_state.current_page == "HTML Portal":
            render_html_portal()
        elif st.session_state.current_page == "Model Evaluation":
            render_model_evaluation()
        elif st.session_state.current_page == "Report Generator":
            render_report_generator()
        elif st.session_state.current_page == "Citation Tool":
            render_citation_tool()
        elif st.session_state.current_page == "Insight Assistant":
            render_insight_assistant()
        elif st.session_state.current_page == "Settings":
            render_settings()
        else:
            # Default to dashboard if invalid page
            logger.warning(f"Invalid page requested: {st.session_state.current_page}")
            st.session_state.current_page = "Dashboard"
            render_dashboard()
    
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}")
        logger.critical(traceback.format_exc())
        st.error(f"Critical application error: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import time
import logging
import os
import threading
import random
import base64
import traceback
import openai
import re
import difflib
from datetime import datetime, timedelta
from io import BytesIO
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("impactguard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImpactGuard")

# Set page configuration with custom theme
st.set_page_config(
    page_title="ImpactGuard - AI Security & Sustainability Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Setup OpenAI API key securely (for reporting functionality)
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    logger.warning("OpenAI API key not found in secrets. Some features may be limited.")

# ----------------------------------------------------------------
# Session State Management
# ----------------------------------------------------------------

def initialize_session_state():
    """Initialize all session state variables with proper error handling"""
    try:
        # Core session states
        if 'targets' not in st.session_state:
            st.session_state.targets = []

        if 'test_results' not in st.session_state:
            st.session_state.test_results = {}

        if 'running_test' not in st.session_state:
            st.session_state.running_test = False

        if 'progress' not in st.session_state:
            st.session_state.progress = 0

        if 'vulnerabilities_found' not in st.session_state:
            st.session_state.vulnerabilities_found = 0

        if 'current_theme' not in st.session_state:
            st.session_state.current_theme = "dark"  # Default to dark theme
            
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"

        # Thread management
        if 'active_threads' not in st.session_state:
            st.session_state.active_threads = []
            
        # Error handling
        if 'error_message' not in st.session_state:
            st.session_state.error_message = None
            
        # Initialize bias testing state
        if 'bias_results' not in st.session_state:
            st.session_state.bias_results = {}
            
        if 'show_bias_results' not in st.session_state:
            st.session_state.show_bias_results = False
            
        # Carbon tracking states
        if 'carbon_tracking_active' not in st.session_state:
            st.session_state.carbon_tracking_active = False
            
        if 'carbon_measurements' not in st.session_state:
            st.session_state.carbon_measurements = []

        # Citation tool states
        if 'VALIDATION_STRICTNESS' not in st.session_state:
            st.session_state.VALIDATION_STRICTNESS = 2
            
        # Reporting states
        if 'reports' not in st.session_state:
            st.session_state.reports = []
            
        # Insight report states
        if 'insights' not in st.session_state:
            st.session_state.insights = []
            
        logger.info("Session state initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing session state: {str(e)}")
        display_error(f"Failed to initialize application state: {str(e)}")

# Thread cleanup
def cleanup_threads():
    """Remove completed threads from session state"""
    try:
        if 'active_threads' in st.session_state:
            # Filter out completed threads
            active_threads = []
            for thread in st.session_state.active_threads:
                if thread.is_alive():
                    active_threads.append(thread)
            
            # Update session state with only active threads
            st.session_state.active_threads = active_threads
            
            if len(st.session_state.active_threads) > 0:
                logger.info(f"Active threads: {len(st.session_state.active_threads)}")
    except Exception as e:
        logger.error(f"Error cleaning up threads: {str(e)}")

# ----------------------------------------------------------------
# UI Theme & Styling
# ----------------------------------------------------------------

# Define color schemes
themes = {
    "dark": {
        "bg_color": "#121212",
        "card_bg": "#1E1E1E",
        "primary": "#003b7a",    # ImpactGuard blue
        "secondary": "#BB86FC",  # Purple
        "accent": "#03DAC6",     # Teal
        "warning": "#FF9800",    # Orange
        "error": "#CF6679",      # Red
        "text": "#FFFFFF"
    },
    "light": {
        "bg_color": "#F5F5F5",
        "card_bg": "#FFFFFF",
        "primary": "#003b7a",    # ImpactGuard blue
        "secondary": "#7C4DFF",  # Deep purple
        "accent": "#00BCD4",     # Cyan
        "warning": "#FF9800",    # Orange
        "error": "#F44336",      # Red
        "text": "#212121"
    }
}

# Get current theme colors safely
def get_theme():
    """Get current theme with error handling"""
    try:
        return themes[st.session_state.current_theme]
    except Exception as e:
        logger.error(f"Error getting theme: {str(e)}")
        # Return dark theme as fallback
        return themes["dark"]

# CSS styles
def load_css():
    """Load CSS with the current theme"""
    try:
        theme = get_theme()
        
        return f"""
        <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: {theme["primary"]};
        }}
        
        .stProgress > div > div > div > div {{
            background-color: {theme["primary"]};
        }}
        
        div[data-testid="stExpander"] {{
            border: none;
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            margin-bottom: 1rem;
        }}
        
        div[data-testid="stVerticalBlock"] {{
            gap: 1.5rem;
        }}
        
        .card {{
            border-radius: 10px;
            background-color: {theme["card_bg"]};
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border-left: 3px solid {theme["primary"]};
        }}
        
        .warning-card {{
            border-left: 3px solid {theme["warning"]};
        }}
        
        .error-card {{
            border-left: 3px solid {theme["error"]};
        }}
        
        .success-card {{
            border-left: 3px solid {theme["primary"]};
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .metric-label {{
            font-size: 14px;
            color: {theme["text"]};
            opacity: 0.7;
        }}
        
        .sidebar-title {{
            margin-left: 15px;
            font-size: 1.2rem;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .target-card {{
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 3px solid {theme["secondary"]};
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .status-badge.active {{
            background-color: {theme["primary"]};
            color: white;
        }}
        
        .status-badge.inactive {{
            background-color: gray;
            color: white;
        }}
        
        .hover-card:hover {{
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }}
        
        .card-title {{
            color: {theme["primary"]};
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .nav-item {{
            padding: 8px 15px;
            border-radius: 5px;
            margin-bottom: 5px;
            cursor: pointer;
        }}
        
        .nav-item:hover {{
            background-color: rgba(0, 59, 122, 0.1);
        }}
        
        .nav-item.active {{
            background-color: rgba(0, 59, 122, 0.2);
            font-weight: bold;
        }}
        
        .tag {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 5px;
            margin-bottom: 5px;
        }}
        
        .tag.owasp {{
            background-color: rgba(187, 134, 252, 0.2);
            color: {theme["secondary"]};
        }}
        
        .tag.nist {{
            background-color: rgba(3, 218, 198, 0.2);
            color: {theme["accent"]};
        }}
        
        .tag.fairness {{
            background-color: rgba(255, 152, 0, 0.2);
            color: {theme["warning"]};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            border-radius: 5px 5px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {theme["card_bg"]};
            border-bottom: 3px solid {theme["primary"]};
        }}
        
        .error-message {{
            background-color: #CF6679;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        /* Modern sidebar styling */
        section[data-testid="stSidebar"] {{
            background-color: {theme["card_bg"]};
            border-right: 1px solid rgba(0,0,0,0.1);
        }}
        
        /* Modern navigation categories */
        .nav-category {{
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            color: {theme["text"]};
            opacity: 0.6;
            margin: 10px 15px 5px 15px;
        }}
        
        /* Main content area padding */
        .main-content {{
            padding: 20px;
        }}
        
        /* Modern cards with hover effects */
        .modern-card {{
            background-color: {theme["card_bg"]};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            transition: all 0.3s ease;
            border-left: none;
            border-top: 4px solid {theme["primary"]};
        }}
        
        .modern-card:hover {{
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            transform: translateY(-5px);
        }}
        
        .modern-card.warning {{
            border-top: 4px solid {theme["warning"]};
        }}
        
        .modern-card.error {{
            border-top: 4px solid {theme["error"]};
        }}
        
        .modern-card.secondary {{
            border-top: 4px solid {theme["secondary"]};
        }}
        
        .modern-card.accent {{
            border-top: 4px solid {theme["accent"]};
        }}
        
        /* App header styles */
        .app-header {{
            display: flex;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .app-title {{
            font-size: 24px;
            font-weight: bold;
            margin: 0;
            color: {theme["primary"]};
        }}
        
        .app-subtitle {{
            font-size: 14px;
            opacity: 0.7;
            margin: 0;
        }}
        </style>
        """
    except Exception as e:
        logger.error(f"Error loading CSS: {str(e)}")
        # Return minimal CSS as fallback
        return "<style>.error-message { background-color: #CF6679; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }</style>"

# ----------------------------------------------------------------
# Navigation and Control
# ----------------------------------------------------------------

# Helper function to set page
def set_page(page_name):
    """Set the current page safely"""
    try:
        st.session_state.current_page = page_name
        logger.info(f"Navigation: Switched to {page_name} page")
    except Exception as e:
        logger.error(f"Error setting page to {page_name}: {str(e)}")
        display_error(f"Failed to navigate to {page_name}")

# Safe rerun function
def safe_rerun():
    """Safely rerun the app, handling different Streamlit versions"""
    try:
        st.rerun()  # For newer Streamlit versions
    except Exception as e1:
        try:
            st.experimental_rerun()  # For older Streamlit versions
        except Exception as e2:
            logger.error(f"Failed to rerun app: {str(e1)} then {str(e2)}")
            # Do nothing - at this point we can't fix it

# Error handling
def display_error(message):
    """Display error message to the user"""
    try:
        st.session_state.error_message = message
        logger.error(f"UI Error: {message}")
    except Exception as e:
        logger.critical(f"Failed to display error message: {str(e)}")

# ----------------------------------------------------------------
# Custom UI Components
# ----------------------------------------------------------------

# Custom components
def card(title, content, card_type="default"):
    """Generate HTML card with error handling"""
    try:
        card_class = "card"
        if card_type == "warning":
            card_class += " warning-card"
        elif card_type == "error":
            card_class += " error-card"
        elif card_type == "success":
            card_class += " success-card"
        
        return f"""
        <div class="{card_class} hover-card">
            <div class="card-title">{title}</div>
            {content}
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering card: {str(e)}")
        return f"""
        <div class="card error-card">
            <div class="card-title">Error Rendering Card</div>
            <p>Failed to render card content: {str(e)}</p>
        </div>
        """

def modern_card(title, content, card_type="default", icon=None):
    """Generate a modern style card with optional icon"""
    try:
        card_class = "modern-card"
        if card_type == "warning":
            card_class += "
card_class = "modern-card"
        if card_type == "warning":
            card_class += " warning"
        elif card_type == "error":
            card_class += " error"
        elif card_type == "secondary":
            card_class += " secondary"
        elif card_type == "accent":
            card_class += " accent"
        
        icon_html = f'<span style="margin-right: 8px;">{icon}</span>' if icon else ''
        
        return f"""
        <div class="{card_class}">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                {icon_html}
                <div class="card-title">{title}</div>
            </div>
            <div>{content}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering modern card: {str(e)}")
        return f"""
        <div class="modern-card error">
            <div class="card-title">Error Rendering Card</div>
            <p>Failed to render card content: {str(e)}</p>
        </div>
        """

def metric_card(label, value, description="", prefix="", suffix=""):
    """Generate HTML metric card with error handling"""
    try:
        return f"""
        <div class="modern-card hover-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{prefix}{value}{suffix}</div>
            <div style="font-size: 14px; opacity: 0.7;">{description}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering metric card: {str(e)}")
        return f"""
        <div class="modern-card error">
            <div class="metric-label">Error</div>
            <div class="metric-value">N/A</div>
            <div style="font-size: 14px; opacity: 0.7;">Failed to render metric: {str(e)}</div>
        </div>
        """

# Logo and header
def render_header():
    """Render the application header safely"""
    try:
        logo_html = """
        <div class="app-header">
            <div style="margin-right: 15px; width: 38px; height: 38px;">
                <svg width="38" height="38" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                    <path d="M100 10 L180 50 V120 C180 150 150 180 100 190 C50 180 20 150 20 120 V50 L100 10Z" fill="#003b7a" />
                    <path d="M75 70 C95 70 110 125 140 110" stroke="white" strokeWidth="15" fill="none" />
                </svg>
            </div>
            <div>
                <div class="app-title">ImpactGuard</div>
                <div class="app-subtitle">Supercharging progress in AI Ethics and Governance – ORAIG</div>
            </div>
        </div>
        """
        st.markdown(logo_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering header: {str(e)}")
        st.markdown("# 🛡️ ImpactGuard")

# ----------------------------------------------------------------
# Sidebar Navigation
# ----------------------------------------------------------------

def sidebar_navigation():
    """Render the sidebar navigation with organized categories"""
    try:
        st.sidebar.markdown("""
        <div style="display: flex; align-items: center; padding: 1rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div style="margin-right: 10px;">
                <svg width="28" height="28" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                    <path d="M100 10 L180 50 V120 C180 150 150 180 100 190 C50 180 20 150 20 120 V50 L100 10Z" fill="#003b7a" />
                    <path d="M75 70 C95 70 110 125 140 110" stroke="white" strokeWidth="15" fill="none" />
                </svg>
            </div>
            <div>
                <div style="font-weight: bold; font-size: 1.2rem; color: #4299E1;">ImpactGuard</div>
                <div style="font-size: 0.7rem; opacity: 0.7;">By HCLTech</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Organize navigation options by category
        navigation_categories = {
            "Core Security": [
                {"icon": "🏠", "name": "Dashboard"},
                {"icon": "🎯", "name": "Target Management"},
                {"icon": "🧪", "name": "Test Configuration"},
                {"icon": "▶️", "name": "Run Assessment"},
                {"icon": "📊", "name": "Results Analyzer"}
            ],
            "AI Ethics & Bias": [
                {"icon": "🔍", "name": "Ethical AI Testing"},
                {"icon": "⚖️", "name": "Bias Testing"},
                {"icon": "📏", "name": "Bias Comparison"},
                {"icon": "🧠", "name": "HELM Evaluation"}
            ],
            "Sustainability": [
                {"icon": "🌱", "name": "Environmental Impact"},
                {"icon": "🌍", "name": "Sustainability Dashboard"}
            ],
            "Reports & Knowledge": [
                {"icon": "📝", "name": "Report Generator"},
                {"icon": "📚", "name": "Citation Tool"},
                {"icon": "💡", "name": "Insight Assistant"}
            ],
            "Integration & Tools": [
                {"icon": "📁", "name": "Multi-Format Import"},
                {"icon": "🚀", "name": "High-Volume Testing"},
                {"icon": "📚", "name": "Knowledge Base"}
            ],
            "System": [
                {"icon": "⚙️", "name": "Settings"}
            ]
        }
        
        # Render each category and its navigation options
        for category, options in navigation_categories.items():
            st.sidebar.markdown(f'<div class="nav-category">{category}</div>', unsafe_allow_html=True)
            
            for option in options:
                # Create a button for each navigation option
                if st.sidebar.button(
                    f"{option['icon']} {option['name']}", 
                    key=f"nav_{option['name']}",
                    use_container_width=True,
                    type="secondary" if st.session_state.current_page != option["name"] else "primary"
                ):
                    set_page(option["name"])
                    safe_rerun()
        
        # Theme toggle
        st.sidebar.markdown("---")
        if st.sidebar.button("🔄 Toggle Theme", key="toggle_theme", use_container_width=True):
            st.session_state.current_theme = "light" if st.session_state.current_theme == "dark" else "dark"
            logger.info(f"Theme toggled to {st.session_state.current_theme}")
            safe_rerun()
        
        # System status
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="sidebar-title">📡 System Status</div>', unsafe_allow_html=True)
        
        if st.session_state.running_test:
            st.sidebar.success("⚡ Test Running")
        else:
            st.sidebar.info("⏸️ Idle")
        
        st.sidebar.markdown(f"🎯 Targets: {len(st.session_state.targets)}")
        
        # Active threads info
        if len(st.session_state.active_threads) > 0:
            st.sidebar.markdown(f"🧵 Active threads: {len(st.session_state.active_threads)}")
        
        # Add carbon tracking status if active
        if st.session_state.get("carbon_tracking_active", False):
            st.sidebar.markdown("🌱 Carbon tracking active")
        
        # Add version info
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"v1.0.0 | {datetime.now().strftime('%Y-%m-%d')}", unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering sidebar: {str(e)}")
        st.sidebar.error("Navigation Error")
        st.sidebar.markdown(f"Error: {str(e)}")

# ----------------------------------------------------------------
# Utility Classes and Functions (Common)
# ----------------------------------------------------------------

# Mock data functions with error handling
def get_mock_test_vectors():
    """Get mock test vector data with error handling"""
    try:
        return [
            {
                "id": "sql_injection",
                "name": "SQL Injection",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "xss",
                "name": "Cross-Site Scripting",
                "category": "owasp",
                "severity": "medium"
            },
            {
                "id": "prompt_injection",
                "name": "Prompt Injection",
                "category": "owasp",
                "severity": "critical"
            },
            {
                "id": "insecure_output",
                "name": "Insecure Output Handling",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "nist_governance",
                "name": "AI Governance",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "nist_transparency",
                "name": "Transparency",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "fairness_demographic",
                "name": "Demographic Parity",
                "category": "fairness",
                "severity": "high"
            },
            {
                "id": "privacy_gdpr",
                "name": "GDPR Compliance",
                "category": "privacy",
                "severity": "critical"
            },
            {
                "id": "jailbreaking",
                "name": "Jailbreaking Resistance",
                "category": "exploit",
                "severity": "critical"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting mock test vectors: {str(e)}")
        display_error("Failed to load test vectors")
        return []  # Return empty list as fallback

def run_mock_test(target, test_vectors, duration=30):
    """Simulate running a test in the background with proper error handling"""
    try:
        # Initialize progress
        st.session_state.progress = 0
        st.session_state.vulnerabilities_found = 0
        st.session_state.running_test = True
        
        logger.info(f"Starting mock test against {target['name']} with {len(test_vectors)} test vectors")
        
        # Create mock results data structure
        results = {
            "summary": {
                "total_tests": 0,
                "vulnerabilities_found": 0,
                "risk_score": 0
            },
            "vulnerabilities": [],
            "test_details": {}
        }
        
        # Simulate test execution
        total_steps = 100
        step_sleep = duration / total_steps
        
        for i in range(total_steps):
            # Check if we should stop (for handling cancellations)
            if not st.session_state.running_test:
                logger.info("Test was cancelled")
                break
                
            time.sleep(step_sleep)
            st.session_state.progress = (i + 1) / total_steps
            
            # Occasionally "find" a vulnerability
            if random.random() < 0.2:  # 20% chance each step
                vector = random.choice(test_vectors)
                severity_weight = {"low": 1, "medium": 2, "high": 3, "critical": 5}
                weight = severity_weight.get(vector["severity"], 1)
                
                # Add vulnerability to results
                vulnerability = {
                    "id": f"VULN-{len(results['vulnerabilities']) + 1}",
                    "test_vector": vector["id"],
                    "test_name": vector["name"],
                    "severity": vector["severity"],
                    "details": f"Mock vulnerability found in {target['name']} using {vector['name']} test vector.",
                    "timestamp": datetime.now().isoformat()
                }
                results["vulnerabilities"].append(vulnerability)
                
                # Update counters
                st.session_state.vulnerabilities_found += 1
                results["summary"]["vulnerabilities_found"] += 1
                results["summary"]["risk_score"] += weight
                
                logger.info(f"Found vulnerability: {vulnerability['id']} ({vulnerability['severity']})")
        
        # Complete the test results
        results["summary"]["total_tests"] = len(test_vectors) * 10  # Assume 10 variations per vector
        results["timestamp"] = datetime.now().isoformat()
        results["target"] = target["name"]
        
        logger.info(f"Test completed: {results['summary']['vulnerabilities_found']} vulnerabilities found")
        
        # Set the results in session state
        st.session_state.test_results = results
        return results
    
    except Exception as e:
        error_details = {
            "error": True,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        logger.error(f"Error in test execution: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Create error result
        st.session_state.error_message = f"Test execution failed: {str(e)}"
        return error_details
    
    finally:
        # Always ensure we reset the running state
        st.session_state.running_test = False

# File Format Support Functions
def handle_multiple_file_formats(uploaded_file):
    """Process different file formats for impact assessments"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # JSON (already supported)
        if file_extension == 'json':
            import json
            return json.loads(uploaded_file.read())
        
        # CSV
        elif file_extension == 'csv':
            import pandas as pd
            import io
            return pd.read_csv(uploaded_file)
        
        # Excel
        elif file_extension in ['xlsx', 'xls']:
            import pandas as pd
            return pd.read_excel(uploaded_file)
        
        # PDF
        elif file_extension == 'pdf':
            from pypdf import PdfReader
            import io
            
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return {"text": text}
        
        # XML
        elif file_extension == 'xml':
            import xml.etree.ElementTree as ET
            import io
            
            tree = ET.parse(io.BytesIO(uploaded_file.read()))
            root = tree.getroot()
            
            # Convert XML to dict (simplified)
            def xml_to_dict(element):
                result = {}
                for child in element:
                    child_data = xml_to_dict(child)
                    if child.tag in result:
                        if type(result[child.tag]) is list:
                            result[child.tag].append(child_data)
                        else:
                            result[child.tag] = [result[child.tag], child_data]
                    else:
                        result[child.tag] = child_data
                
                if len(result) == 0:
                    return element.text
                return result
            
            return xml_to_dict(root)
        
        # YAML/YML
        elif file_extension in ['yaml', 'yml']:
            import yaml
            return yaml.safe_load(uploaded_file)
        
        # Other formats are supported similarly...
        else:
            return {"error": f"Unsupported file format: {file_extension}"}
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return {"error": f"Failed to process file: {str(e)}"}

# ----------------------------------------------------------------
# Main Class for WhyLabs Bias Testing
# ----------------------------------------------------------------

class WhyLabsBiasTest:
    """Class for WhyLabs-based bias testing functionality"""
    
    def __init__(self):
        # This would normally import whylogs, but for demonstration we'll create a mock
        self.session = None
        self.results = {}
    
    def initialize_session(self, dataset_name):
        """Initialize a WhyLogs profiling session"""
        try:
            self.session = True  # Mock initialization
            logger.info(f"WhyLogs session initialized for {dataset_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WhyLogs session: {str(e)}")
            return False
    
    def profile_dataset(self, df, dataset_name):
        """Profile a dataset for bias analysis"""
        try:
            if self.session is None:
                self.initialize_session(dataset_name)
                
            # Create a mock profile
            profile = {"name": dataset_name, "columns": list(df.columns)}
            self.results[dataset_name] = {"profile": profile}
            logger.info(f"Dataset {dataset_name} profiled successfully")
            return profile
        except Exception as e:
            logger.error(f"Failed to profile dataset: {str(e)}")
            return None
    
    def analyze_bias(self, df, protected_features, target_column, dataset_name):
        """Analyze bias in a dataset based on protected features"""
        try:
            # Profile the dataset first
            profile = self.profile_dataset(df, dataset_name)
            
            bias_metrics = {}
            
            # Calculate basic bias metrics
            for feature in protected_features:
                # Statistical parity difference
                feature_groups = df.groupby(feature)
                
                outcomes = {}
                disparities = {}
                
                for group_name, group_data in feature_groups:
                    # For binary target variable
                    if df[target_column].nunique() == 2:
                        positive_outcome_rate = group_data[target_column].mean()
                        outcomes[group_name] = positive_outcome_rate
                
                # Calculate disparities between groups
                baseline = max(outcomes.values())
                for group, rate in outcomes.items():
                    disparities[group] = baseline - rate
                
                bias_metrics[feature] = {
                    "outcomes": outcomes,
                    "disparities": disparities,
                    "max_disparity": max(disparities.values())
                }
            
            self.results[dataset_name]["bias_metrics"] = bias_metrics
            logger.info(f"Bias analysis completed for {dataset_name}")
            return bias_metrics
        except Exception as e:
            logger.error(f"Failed to analyze bias: {str(e)}")
            return {"error": str(e)}
    
    def get_results(self, dataset_name=None):
        """Get analysis results"""
        if dataset_name:
            return self.results.get(dataset_name, {})
        return self.results

# ----------------------------------------------------------------
# Main Class for Carbon Impact Tracking
# ----------------------------------------------------------------

class CarbonImpactTracker:
    """Class for tracking environmental impact of AI systems"""
    
    def __init__(self):
        # Placeholder for codecarbon import
        self.tracker = None
        self.measurements = []
        self.total_emissions = 0.0
        self.is_tracking = False
    
    def initialize_tracker(self, project_name, api_endpoint=None):
        """Initialize the carbon tracker"""
        try:
            # Mock initialization for demonstration
            self.tracker = {"project_name": project_name, "initialized": True}
            logger.info(f"Carbon tracker initialized for {project_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize carbon tracker: {str(e)}")
            return False
    
    def start_tracking(self):
        """Start tracking carbon emissions"""
        try:
            if self.tracker is None:
                return False
                
            self.is_tracking = True
            logger.info("Carbon emission tracking started")
            return True
        except Exception as e:
            logger.error(f"Failed to start carbon tracking: {str(e)}")
            return False
    
    def stop_tracking(self):
        """Stop tracking and get the emissions data"""
        try:
            if not self.is_tracking or self.tracker is None:
                return 0.0
                
            # Generate a random emissions value for demonstration
            emissions = random.uniform(0.001, 0.1)
            self.is_tracking = False
            self.measurements.append(emissions)
            self.total_emissions += emissions
            
            logger.info(f"Carbon emission tracking stopped. Measured: {emissions} kg CO2eq")
            return emissions
        except Exception as e:
            logger.error(f"Failed to stop carbon tracking: {str(e)}")
            return 0.0
    
    def get_total_emissions(self):
        """Get total emissions tracked so far"""
        return self.total_emissions
    
    def get_all_measurements(self):
        """Get all measurements"""
        return self.measurements
    
    def generate_report(self):
        """Generate a report of carbon emissions"""
        try:
            energy_solutions = [
                {
                    "name": "Optimize AI Model Size",
                    "description": "Reduce model parameters and optimize architecture",
                    "potential_savings": "20-60% reduction in emissions",
                    "implementation_difficulty": "Medium"
                },
                {
                    "name": "Implement Model Distillation",
                    "description": "Create smaller, efficient versions of larger models",
                    "potential_savings": "40-80% reduction in emissions",
                    "implementation_difficulty": "High"
                },
                {
                    "name": "Use Efficient Hardware",
                    "description": "Deploy on energy-efficient hardware (e.g., specialized AI chips)",
                    "potential_savings": "30-50% reduction in emissions",
                    "implementation_difficulty": "Medium"
                }
            ]
            
            # Calculate the impact
            kwh_per_kg_co2 = 0.6  # Approximate conversion factor
            energy_consumption = self.total_emissions / kwh_per_kg_co2
            
            trees_equivalent = self.total_emissions * 16.5  # Each kg CO2 ~ 16.5 trees for 1 day
            
            return {
                "total_emissions_kg": self.total_emissions,
                "energy_consumption_kwh": energy_consumption,
                "measurements": self.measurements,
                "trees_equivalent": trees_equivalent,
                "mitigation_strategies": energy_solutions
            }
        except Exception as e:
            logger.error(f"Failed to generate emissions report: {str(e)}")
            return {"error": str(e)}

# ----------------------------------------------------------------
# Report Generation and Citation Functions (Merged from research assistant)
# ----------------------------------------------------------------

def generate_insight(user, category, prompt_text, response_text, knowledge_base, context, temperature, max_tokens):
    """Generate an insight using OpenAI API"""
    system_prompt = f"{knowledge_base}\n\n{context}"
    user_prompt = f"""
    Given the following information:
    User: {user}
    Category: {category}
    Prompt: {prompt_text}
    Response: {response_text}
    Generate a concise, meaningful insight based on this information.
    """
    
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response['choices'][0]['message']['content'].strip()
        except openai.error.RateLimitError:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            return f"Error: {str(e)}"
    return "Error: Rate limit exceeded"

def process_csv(uploaded_file):
    """Process a CSV file for insight generation"""
    try:
        df = pd.read_csv(uploaded_file)
        required_columns = {'User', 'Category', 'Prompt', 'Response'}
        if not required_columns.issubset(df.columns):
            st.error(f"Required columns: {required_columns}")
            return None
        return df
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        return None

def generate_report(title, test_results, bias_results, sustainability_results, include_recommendations=True):
    """Generate a comprehensive report combining security, bias, and sustainability data"""
    try:
        # Create report structure
        report = {
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "security": test_results if test_results else {"summary": {"total_tests": 0, "vulnerabilities_found": 0, "risk_score": 0}, "vulnerabilities": []},
            "bias": bias_results if bias_results else {},
            "sustainability": sustainability_results if sustainability_results else {},
            "recommendations": []
        }
        
        # Generate recommendations
        if include_recommendations:
            # Security recommendations
            if test_results and "vulnerabilities" in test_results and test_results["vulnerabilities"]:
                for vuln in test_results["vulnerabilities"][:3]:  # Top 3 vulnerabilities
                    report["recommendations"].append({
                        "area": "security",
                        "severity": vuln.get("severity", "medium"),
                        "recommendation": f"Address {vuln.get('test_name', 'unknown vulnerability')} issue.",
                        "details": vuln.get("details", "No details")
                    })
            
            # Bias recommendations
            if bias_results and "bias_metrics" in bias_results:
                for feature, metrics in bias_results.get("bias_metrics", {}).items():
                    if metrics.get("max_disparity", 0) > 0.1:  # Threshold for recommendation
                        report["recommendations"].append({
                            "area": "bias",
                            "severity": "high" if metrics.get("max_disparity", 0) > 0.2 else "medium",
                            "recommendation": f"Address bias in {feature} attribute.",
                            "details": f"Disparity of {metrics.get('max_disparity', 0):.2f} detected in {feature}."
                        })
            
            # Sustainability recommendations
            if sustainability_results and "total_emissions_kg" in sustainability_results:
                emissions = sustainability_results.get("total_emissions_kg", 0)
                if emissions > 1.0:
                    report["recommendations"].append({
                        "area": "sustainability",
                        "severity": "medium",
                        "recommendation": "Optimize model size and deployment to reduce carbon footprint.",
                        "details": f"Current emissions of {emissions:.2f} kg CO2e could be reduced with efficiency improvements."
                    })
        
        # Add timestamp and report ID
        report["id"] = f"REP-{int(time.time())}"
        
        return report
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return {"error": str(e), "title": title, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ----------------------------------------------------------------
# Citation Helper Functions (From research assistant)
# ----------------------------------------------------------------

def retry_request(url, method='head', retries=3, timeout=5):
    """Make HTTP request with retries for citation validation"""
    for attempt in range(retries):
        try:
            if method == 'head':
                response = requests.head(url, allow_redirects=True, timeout=timeout)
            elif method == 'get':
                response = requests.get(url, allow_redirects=True, timeout=timeout)
            else:
                return None
            if response.status_code == 200:
                return response
        except requests.RequestException as e:
            logger.error(f"Network error on attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)
    return None

def is_valid_doi_format(doi):
    """Check if DOI format is valid"""
    pattern = r'^10.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(pattern, doi, re.IGNORECASE) is not None

def validate_doi(doi):
    """Validate DOI by checking if it resolves"""
    if not is_valid_doi_format(doi):
        return False
    url = f"https://doi.org/{doi}"
    response = retry_request(url, method='head')
    return response is not None

def validate_url(url):
    """Validate a URL by checking if it resolves"""
    response = retry_request(url, method='head')
    return response is not None

def is_metadata_complete(article):
    """Check if article metadata is complete according to validation strictness level"""
    essential_fields = ['author', 'title', 'issued']
    missing_fields = [field for field in essential_fields if field not in article or not article[field]]
    if missing_fields:
        logger.warning(f"Missing fields: {missing_fields}")
    return len(missing_fields) <= st.session_state.VALIDATION_STRICTNESS

def format_authors_apa(authors):
    """Format authors for APA style citation"""
    authors_list = []
    for author in authors:
        last_name = author.get('family', '')
        initials = ''.join([name[0] + '.' for name in author.get('given', '').split()])
        authors_list.append(f"{last_name}, {initials}")
    
    if not authors_list:
        return "Anonymous"
    elif len(authors_list) == 1:
        return authors_list[0]
    elif len(authors_list) <= 20:
        return ', '.join(authors_list[:-1]) + ', & ' + authors_list[-1]
    else:
        return ', '.join(authors_list[:19]) + ', ... ' + authors_list[-1]

def format_citation(article, style="APA"):
    """Format a citation in the specified style"""
    if not article:
        return None
    
    authors = article.get('author', [])
    authors_str = format_authors_apa(authors)
    
    year = article.get('published-print', {}).get('date-parts', [[None]])[0][0]
    if not year:
        year = article.get('published-online', {}).get('date-parts', [[None]])[0][0]
    if not year:
        year = article.get('issued', {}).get('date-parts', [[None]])[0][0]
    ifif not year:
        year = article.get('issued', {}).get('date-parts', [[None]])[0][0]
    if not year:
        year = 'n.d.'
        
    title = article.get('title', [''])[0]
    journal = article.get('container-title', [''])[0]
    doi = article.get('DOI', '')
    
    citation = f"{authors_str} ({year}). {title}"
    if journal:
        citation += f". {journal}"
    if doi:
        citation += f". https://doi.org/{doi}"
    
    return citation

@st.cache_data(show_spinner=False)
def search_articles(query):
    """Search for articles using CrossRef API"""
    try:
        response = requests.get(
            f"https://api.crossref.org/works?query={query}&rows=10",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("items", [])
    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return []

# ----------------------------------------------------------------
# Page Renderers - Core Security Pages
# ----------------------------------------------------------------

def render_dashboard():
    """Render the dashboard page safely"""
    try:
        render_header()
        
        st.markdown("""
        <div style="margin-bottom: 20px;">
        Welcome to your AI Security & Sustainability Hub. This dashboard provides an overview of your security posture,
        sustainability metrics, and ethical AI evaluation results.
        </div>
        """, unsafe_allow_html=True)
        
        # Quick stats in a row of cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(metric_card("Targets", len(st.session_state.targets), "Configured AI models"), unsafe_allow_html=True)
        
        with col2:
            st.markdown(metric_card("Test Vectors", "9", "Available security tests"), unsafe_allow_html=True)
        
        with col3:
            vuln_count = len(st.session_state.test_results.get("vulnerabilities", [])) if st.session_state.test_results else 0
            st.markdown(metric_card("Vulnerabilities", vuln_count, "Identified issues"), unsafe_allow_html=True)
        
        with col4:
            risk_score = st.session_state.test_results.get("summary", {}).get("risk_score", 0) if st.session_state.test_results else 0
            st.markdown(metric_card("Risk Score", risk_score, "Overall security risk"), unsafe_allow_html=True)
        
        # Recent activity and status
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(modern_card("Recent Activity", "Your latest security findings and events.", "default", "🔔"), unsafe_allow_html=True)
            
            if not st.session_state.test_results:
                st.markdown(modern_card("No Recent Activity", "Run your first assessment to generate results.", "warning", "⚠️"), unsafe_allow_html=True)
            else:
                # Show the most recent vulnerabilities
                vulnerabilities = st.session_state.test_results.get("vulnerabilities", [])
                if vulnerabilities:
                    for vuln in vulnerabilities[:3]:  # Show top 3
                        severity_color = {
                            "low": get_theme()["text"],
                            "medium": get_theme()["warning"],
                            "high": get_theme()["warning"],
                            "critical": get_theme()["error"]
                        }.get(vuln["severity"], get_theme()["text"])
                        
                        st.markdown(f"""
                        <div class="modern-card hover-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div class="card-title">{vuln["id"]}: {vuln["test_name"]}</div>
                                <div style="color: {severity_color}; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                                    {vuln["severity"]}
                                </div>
                            </div>
                            <p>{vuln["details"]}</p>
                            <div style="font-size: 12px; opacity: 0.7;">Found in: {vuln["timestamp"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(modern_card("System Status", "Current operational status", "default", "📡"), unsafe_allow_html=True)
            
            if st.session_state.running_test:
                st.markdown(modern_card("Test in Progress", f"""
                <div style="margin-bottom: 10px;">
                    <div style="margin-bottom: 5px;">Progress:</div>
                    <div style="height: 10px; background-color: rgba(255,255,255,0.1); border-radius: 5px;">
                        <div style="height: 10px; width: {st.session_state.progress*100}%; background-color: {get_theme()["primary"]}; border-radius: 5px;"></div>
                    </div>
                    <div style="text-align: right; font-size: 12px; margin-top: 5px;">{int(st.session_state.progress*100)}%</div>
                </div>
                <div>Vulnerabilities found: {st.session_state.vulnerabilities_found}</div>
                """, "warning", "⚠️"), unsafe_allow_html=True)
            else:
                st.markdown(modern_card("System Ready", """
                <p>All systems operational and ready to run assessments.</p>
                <div style="display: flex; align-items: center;">
                    <div style="width: 10px; height: 10px; background-color: #4CAF50; border-radius: 50%; margin-right: 5px;"></div>
                    <div>API Connection: Active</div>
                </div>
                """, "default", "✅"), unsafe_allow_html=True)
        
        # Test vector overview
        st.markdown("<h3>Test Vector Overview</h3>", unsafe_allow_html=True)
        
        # Create a radar chart for test coverage
        try:
            test_vectors = get_mock_test_vectors()
            categories = list(set(tv["category"] for tv in test_vectors))
            
            # Count test vectors by category
            category_counts = {}
            for cat in categories:
                category_counts[cat] = sum(1 for tv in test_vectors if tv["category"] == cat)
            
            # Create the data for the radar chart
            fig = go.Figure()
            
            primary_color = get_theme()["primary"]
            # Convert hex to rgb for plotly
            r_value = int(primary_color[1:3], 16) if len(primary_color) >= 7 else 29
            g_value = int(primary_color[3:5], 16) if len(primary_color) >= 7 else 185
            b_value = int(primary_color[5:7], 16) if len(primary_color) >= 7 else 84
            
            fig.add_trace(go.Scatterpolar(
                r=list(category_counts.values()),
                theta=list(category_counts.keys()),
                fill='toself',
                fillcolor=f'rgba({r_value}, {g_value}, {b_value}, 0.3)',
                line=dict(color=primary_color),
                name='Test Coverage'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(category_counts.values()) + 1]
                    )
                ),
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=get_theme()["text"])
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.error(f"Error rendering radar chart: {str(e)}")
            st.error("Failed to render radar chart")
        
        # Environmental impact summary
        st.markdown("<h3>Environmental Impact Summary</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_carbon = sum(st.session_state.carbon_measurements) if hasattr(st.session_state, 'carbon_measurements') else 0
            st.markdown(metric_card("Carbon Emissions", f"{total_carbon:.5f}", "kg CO2 equivalent", suffix=" kg"), unsafe_allow_html=True)
        
        with col2:
            # Convert to equivalent metrics
            energy_consumption = total_carbon / 0.6 if total_carbon > 0 else 0  # Approximate conversion
            st.markdown(metric_card("Energy Consumed", f"{energy_consumption:.5f}", "Kilowatt-hours", suffix=" kWh"), unsafe_allow_html=True)
        
        with col3:
            # Trees needed to offset
            trees_needed = total_carbon * 0.06 if total_carbon > 0 else 0  # ~0.06 trees per kg CO2 per year
            st.markdown(metric_card("Trees Needed", f"{trees_needed:.2f}", "To offset emissions (1 year)"), unsafe_allow_html=True)
        
        # Quick actions with Streamlit buttons
        st.markdown("<h3>Quick Actions</h3>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("➕ Add New Target", use_container_width=True, key="dashboard_add_target"):
                set_page("Target Management")
                safe_rerun()
        
        with col2:
            if st.button("🧪 Run Assessment", use_container_width=True, key="dashboard_run_assessment"):
                set_page("Run Assessment")
                safe_rerun()
        
        with col3:
            if st.button("📊 View Results", use_container_width=True, key="dashboard_view_results"):
                set_page("Results Analyzer")
                safe_rerun()
                
        with col4:
            if st.button("📝 Generate Report", use_container_width=True, key="dashboard_gen_report"):
                set_page("Report Generator")
                safe_rerun()
                
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error rendering dashboard: {str(e)}")

def render_target_management():
    """Render the target management page safely"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Target Management</h2>
        <p>Add and configure AI models to test</p>
        """, unsafe_allow_html=True)
        
        # Show existing targets
        if st.session_state.targets:
            st.markdown("<h3>Your Targets</h3>", unsafe_allow_html=True)
            
            # Use columns for better layout
            cols = st.columns(3)
            for i, target in enumerate(st.session_state.targets):
                col = cols[i % 3]
                with col:
                    with st.container():
                        st.markdown(f"### {target['name']}")
                        st.markdown(f"**Endpoint:** {target['endpoint']}")
                        st.markdown(f"**Type:** {target.get('type', 'Unknown')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_target_{i}", use_container_width=True):
                                # In a real app, this would open an edit dialog
                                st.info("Edit functionality would open here")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_target_{i}", use_container_width=True):
                                # Remove the target
                                st.session_state.targets.pop(i)
                                st.success(f"Target '{target['name']}' deleted")
                                safe_rerun()
        
        # Add new target form
        st.markdown("<h3>Add New Target</h3>", unsafe_allow_html=True)
        
        with st.form("add_target_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                target_name = st.text_input("Target Name")
                target_endpoint = st.text_input("API Endpoint URL")
                target_type = st.selectbox("Model Type", ["LLM", "Content Filter", "Embedding", "Classification", "Other"])
            
            with col2:
                api_key = st.text_input("API Key", type="password")
                target_description = st.text_area("Description")
            
            submit_button = st.form_submit_button("Add Target")
            
            if submit_button:
                try:
                    if not target_name or not target_endpoint:
                        st.error("Name and endpoint are required")
                    else:
                        new_target = {
                            "name": target_name,
                            "endpoint": target_endpoint,
                            "type": target_type,
                            "api_key": api_key,
                            "description": target_description
                        }
                        st.session_state.targets.append(new_target)
                        st.success(f"Target '{target_name}' added successfully!")
                        logger.info(f"Added new target: {target_name}")
                        safe_rerun()
                except Exception as e:
                    logger.error(f"Error adding target: {str(e)}")
                    st.error(f"Failed to add target: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering target management: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in target management: {str(e)}")

def render_test_configuration():
    """Render the test configuration page safely"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Test Configuration</h2>
        <p>Customize your security assessment</p>
        """, unsafe_allow_html=True)
        
        # Implementing just enough to show the structure and functionality
        test_vectors = get_mock_test_vectors()
        
        # Create tabs for each category
        categories = {}
        for tv in test_vectors:
            if tv["category"] not in categories:
                categories[tv["category"]] = []
            categories[tv["category"]].append(tv)
            
        tabs = st.tabs(list(categories.keys()))
        
        for i, (category, tab) in enumerate(zip(categories.keys(), tabs)):
            with tab:
                st.markdown(f"<h3>{category.upper()} Test Vectors</h3>", unsafe_allow_html=True)
                
                # Create a list of test vectors
                for j, tv in enumerate(categories[category]):
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"### {tv['name']}")
                            st.markdown(f"**Severity:** {tv['severity'].upper()}")
                            st.markdown(f"**Category:** {tv['category'].upper()}")
                        
                        with col2:
                            # Use a checkbox to enable/disable
                            is_enabled = st.checkbox("Enable", value=True, key=f"enable_{tv['id']}")
    except Exception as e:
        logger.error(f"Error rendering test configuration: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in test configuration: {str(e)}")

def render_run_assessment():
    """Render the run assessment page safely"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Run Assessment</h2>
        <p>Execute security tests against your targets</p>
        """, unsafe_allow_html=True)
        
        # Check if targets exist
        if not st.session_state.targets:
            st.warning("No targets configured. Please add a target first.")
            if st.button("Add Target", key="run_add_target"):
                set_page("Target Management")
                safe_rerun()
            return
        
        # Check if a test is already running
        if st.session_state.running_test:
            # Show progress
            progress_placeholder = st.empty()
            with progress_placeholder.container():
                progress_bar = st.progress(st.session_state.progress)
                st.markdown(f"**Progress:** {int(st.session_state.progress*100)}%")
                st.markdown(f"**Vulnerabilities found:** {st.session_state.vulnerabilities_found}")
            
            # Stop button
            if st.button("Stop Test", key="stop_test"):
                st.session_state.running_test = False
                logger.info("Test stopped by user")
                st.warning("Test stopped by user")
                safe_rerun()
        else:
            # Test configuration
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h3>Select Target</h3>", unsafe_allow_html=True)
                target_options = [t["name"] for t in st.session_state.targets]
                selected_target = st.selectbox("Target", target_options, key="run_target")
            
            with col2:
                st.markdown("<h3>Test Parameters</h3>", unsafe_allow_html=True)
                test_duration = st.slider("Test Duration (seconds)", 5, 60, 30, key="run_duration", 
                                         help="For demonstration purposes, we're using seconds. In a real system, this would be minutes.")
            
            # Environmental impact tracking option
            st.markdown("<h3>Environmental Impact Tracking</h3>", unsafe_allow_html=True)
            track_carbon = st.checkbox("Track Carbon Emissions During Test", value=True, key="track_carbon_emissions")
            
            if track_carbon:
                st.info("Carbon tracking will be enabled during the test to measure environmental impact")
            
            # Run test button
            if st.button("Run Assessment", use_container_width=True, type="primary", key="start_assessment"):
                try:
                    # Find the selected target object
                    target = next((t for t in st.session_state.targets if t["name"] == selected_target), None)
                    test_vectors = get_mock_test_vectors()
                    
                    if target:
                        # Initialize carbon tracking if requested
                        if track_carbon and 'carbon_tracker' not in st.session_state:
                            st.session_state.carbon_tracker = CarbonImpactTracker()
                            st.session_state.carbon_tracker.initialize_tracker(f"Security Test - {target['name']}")
                        
                        if track_carbon:
                            st.session_state.carbon_tracker.start_tracking()
                            st.session_state.carbon_tracking_active = True
                        
                        # Start the test in a background thread
                        test_thread = threading.Thread(
                            target=run_mock_test,
                            args=(target, test_vectors, test_duration)
                        )
                        test_thread.daemon = True
                        test_thread.start()
                        
                        # Track the thread
                        st.session_state.active_threads.append(test_thread)
                        
                        st.session_state.running_test = True
                        logger.info(f"Started test against {target['name']} with {len(test_vectors)} vectors")
                        st.success("Test started!")
                        safe_rerun()
                    else:
                        st.error("Selected target not found")
                except Exception as e:
                    logger.error(f"Error starting test: {str(e)}")
                    st.error(f"Failed to start test: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering run assessment: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in run assessment: {str(e)}")

def render_results_analyzer():
    """Render the results analyzer page safely"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Results Analyzer</h2>
        <p>Explore and analyze security assessment results</p>
        """, unsafe_allow_html=True)
        
        # Check if there are results to display
        if not st.session_state.test_results:
            st.warning("No Results Available - Run an assessment to generate results.")
            
            if st.button("Go to Run Assessment", key="results_goto_run"):
                set_page("Run Assessment")
                safe_rerun()
            return
        
        # Display results summary
        results = st.session_state.test_results
        vulnerabilities = results.get("vulnerabilities", [])
        summary = results.get("summary", {})
        
        # Create header with summary metrics
        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h3>Assessment Results: {results.get("target", "Unknown Target")}</h3>
            <div style="opacity: 0.7;">Completed: {results.get("timestamp", "Unknown")}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Tests Run", summary.get("total_tests", 0))
        
        with col2:
            st.metric("Vulnerabilities", summary.get("vulnerabilities_found", 0))
        
        with col3:
            st.metric("Risk Score", summary.get("risk_score", 0))
        
        # Visualizations
        st.markdown("<h3>Vulnerability Overview</h3>", unsafe_allow_html=True)
        
        # Display vulnerabilities in a table
        if vulnerabilities:
            # Create a dataframe for display
            vuln_data = []
            for vuln in vulnerabilities:
                vuln_data.append({
                    "ID": vuln.get("id", "Unknown"),
                    "Test Name": vuln.get("test_name", "Unknown"),
                    "Severity": vuln.get("severity", "Unknown"),
                    "Details": vuln.get("details", "No details")
                })
            
            df = pd.DataFrame(vuln_data)
            st.dataframe(df, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Error rendering results analyzer: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in results analyzer: {str(e)}")

# ----------------------------------------------------------------
# Report Generator Page
# ----------------------------------------------------------------

def render_report_generator():
    """Render the report generator page"""
    try:
        render_header()
        
        st.markdown("""
        <h2>AI Security Report Generator</h2>
        <p>Generate comprehensive reports based on assessment results</p>
        """, unsafe_allow_html=True)
        
        # Report configuration
        st.markdown("<h3>Report Configuration</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_title = st.text_input("Report Title", value="AI Security and Ethics Assessment Report")
            
            report_type = st.selectbox(
                "Report Type",
                ["Comprehensive", "Security-focused", "Ethics-focused", "Sustainability-focused"],
                index=0
            )
            
            if st.session_state.targets:
                target_options = ["All Targets"] + [t["name"] for t in st.session_state.targets]
                selected_target = st.selectbox("Target System", target_options)
            else:
                st.warning("No targets available. Please add a target first.")
                selected_target = "None"
        
        with col2:
            include_security = st.checkbox("Include Security Assessment", 
                                          value=report_type in ["Comprehensive", "Security-focused"])
            
            include_ethics = st.checkbox("Include Ethics & Bias Assessment", 
                                        value=report_type in ["Comprehensive", "Ethics-focused"])
            
            include_sustainability = st.checkbox("Include Sustainability Assessment", 
                                               value=report_type in ["Comprehensive", "Sustainability-focused"])
            
            include_recommendations = st.checkbox("Include Recommendations", value=True)
            
            include_citations = st.checkbox("Include Citations & References", value=True)
        
        # Check if we have test results 
        if not st.session_state.test_results and include_security:
            st.warning("No security test results available. Run an assessment first or disable the security section.")
        
        # Source data selection
        st.markdown("<h3>Report Data Sources</h3>", unsafe_allow_html=True)
        
        test_results = st.session_state.test_results if include_security else None
        bias_results = st.session_state.bias_results if include_ethics else None
        
        # Get sustainability results
        sustainability_results = None
        if include_sustainability and hasattr(st.session_state, 'carbon_tracker'):
            total_carbon = st.session_state.carbon_tracker.get_total_emissions()
            sustainability_results = {
                "total_emissions_kg": total_carbon,
                "energy_consumption_kwh": total_carbon / 0.6,  # Approximate conversion
                "measurements": st.session_state.carbon_tracker.get_all_measurements()
            }
        
        # Custom content section
        st.markdown("<h3>Additional Content</h3>", unsafe_allow_html=True)
        
        executive_summary = st.text_area(
            "Executive Summary", 
            height=100,
            help="Provide a brief overview of the report purpose and key findings"
        )
        
        with st.expander("Custom Notes & Observations", expanded=False):
            custom_notes = st.text_area(
                "Notes", 
                height=150,
                help="Add any additional observations or context"
            )
        
        # Generate the report
        if st.button("Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating comprehensive report..."):
                # Generate report data structure
                report = generate_report(
                    report_title, 
                    test_results,
                    bias_results,
                    sustainability_results,
                    include_recommendations
                )
                
                # Add custom content
                report["executive_summary"] = executive_summary
                report["custom_notes"] = custom_notes
                
                # Store report in session state
                if 'reports' not in st.session_state:
                    st.session_state.reports = []
                
                st.session_state.reports.append(report)
                
                # Display success message
                st.success(f"Report '{report_title}' generated successfully!")
                
                # Show report preview
                st.markdown("<h3>Report Preview</h3>", unsafe_allow_html=True)
                
                # Executive summary section
                st.markdown("#### Executive Summary")
                st.write(executive_summary if executive_summary else "No executive summary provided.")
                
                # Display report sections based on inclusion settings
                if include_security and test_results:
                    st.markdown("#### Security Assessment")
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Tests Run", test_results.get("summary", {}).get("total_tests", 0))
                    
                    with col2:
                        st.metric("Vulnerabilities", test_results.get("summary", {}).get("vulnerabilities_found", 0))
                    
                    with col3:
                        st.metric("Risk Score", test_results.get("summary", {}).get("risk_score", 0))
                    
                    # Vulnerabilities
                    vulnerabilities = test_results.get("vulnerabilities", [])
                    if vulnerabilities:
                        st.markdown("**Identified Vulnerabilities:**")
                        for vuln in vulnerabilities[:5]:  # Show top 5
                            severity_color = {
                                "low": "blue",
                                "medium": "orange",
                                "high": "red",
                                "critical": "darkred"
                            }.get(vuln.get("severity", "medium"), "gray")
                            
                            st.markdown(f"""
                            <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                                <div style="font-weight: bold;">{vuln.get("id", "VULN")}: {vuln.get("test_name", "Unknown")}</div>
                                <div>{vuln.get("details", "No details")}</div>
                                <div style="font-size: 0.8em; opacity: 0.7;">Severity: {vuln.get("severity", "medium").upper()}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                if include_ethics and bias_results:
                    st.markdown("#### Ethics & Bias Assessment")
                    
                    if "bias_metrics" in bias_results:
                        for feature, metrics in bias_results["bias_metrics"].items():
                            st.markdown(f"**{feature} Analysis:**")
                            st.markdown(f"Maximum disparity: {metrics.get('max_disparity', 0):.4f}")
                            
                            # Create a bar chart for the feature outcomes
                            if "outcomes" in metrics:
                                outcomes_df = pd.DataFrame({
                                    "Group": list(metrics["outcomes"].keys()),
                                    "Rate": list(metrics["outcomes"].values())
                                })
                                
                                fig = px.bar(
                                    outcomes_df,
                                    x="Group",
                                    y="Rate",
                                    title=f"Outcomes by {feature}",
                                    color="Rate"
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                
                if include_sustainability and sustainability_results:
                    st.markdown("#### Sustainability Assessment")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        emissions = sustainability_results.get("total_emissions_kg", 0)
                        st.metric("Total Emissions", f"{emissions:.4f} kg CO2e")
                    
                    with col2:
                        energy = sustainability_results.get("energy_consumption_kwh", 0)
                        st.metric("Energy Consumption", f"{energy:.2f} kWh")with col3:
                        # Trees needed to offset
                        trees_needed = emissions * 0.06 if emissions > 0 else 0  # ~0.06 trees per kg CO2 per year
                        st.metric("Trees Needed (1 year)", f"{trees_needed:.2f}")
                
                if include_recommendations and "recommendations" in report and report["recommendations"]:
                    st.markdown("#### Recommendations")
                    
                    for i, rec in enumerate(report["recommendations"]):
                        rec_type = rec.get("area", "general").capitalize()
                        severity = rec.get("severity", "medium")
                        
                        severity_color = {
                            "low": "blue",
                            "medium": "orange",
                            "high": "red"
                        }.get(severity, "gray")
                        
                        st.markdown(f"""
                        <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                            <div style="font-weight: bold;">{rec_type} Recommendation {i+1}</div>
                            <div>{rec.get("recommendation", "No recommendation")}</div>
                            <div style="font-size: 0.8em; opacity: 0.7;">{rec.get("details", "")}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                if custom_notes:
                    st.markdown("#### Additional Notes")
                    st.write(custom_notes)
                
                # Report ID and date
                st.markdown(f"""
                <div style="margin-top: 30px; font-size: 0.8em; opacity: 0.7;">
                    Report ID: {report["id"]}<br>
                    Generated: {report["date"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Export options
                export_col1, export_col2 = st.columns(2)
                
                with export_col1:
                    st.download_button(
                        "Export as PDF",
                        "PDF export would be implemented here",
                        file_name=f"{report_title.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                with export_col2:
                    st.download_button(
                        "Export as JSON",
                        json.dumps(report, indent=2),
                        file_name=f"{report_title.replace(' ', '_')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
    
    except Exception as e:
        logger.error(f"Error rendering report generator: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in report generator: {str(e)}")

# ----------------------------------------------------------------
# Citation Tool Page
# ----------------------------------------------------------------

def render_citation_tool():
    """Render the citation tool page"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Auto Citation Tool</h2>
        <p>Search and generate citations for your reports</p>
        """, unsafe_allow_html=True)
        
        # Citation style selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input("Search Query:", placeholder="Enter keywords to search for articles")
        
        with col2:
            citation_style = st.selectbox("Citation Style:", ["APA", "MLA", "Chicago"], key="citation_style")
        
        # Validation strictness in sidebar
        with st.sidebar:
            st.markdown("#### Citation Settings")
            validation_level = st.radio(
                "Validation Level:",
                options=[1, 2, 3],
                format_func=lambda x: {1: "Strict", 2: "Moderate", 3: "Lenient"}[x],
                key="validation_level"
            )
            st.session_state.VALIDATION_STRICTNESS = validation_level
        
        # Search action
        if st.button("Search", key="search_citation"):
            if query:
                with st.spinner('Searching for articles...'):
                    articles = search_articles(query)
                    
                    if articles:
                        st.markdown("### Search Results")
                        
                        # Create a container for selected citations
                        selected_citations = []
                        
                        # Display each result with selection option
                        for idx, article in enumerate(articles):
                            title = article.get('title', ['No title'])[0]
                            
                            with st.container():
                                col1, col2 = st.columns([5, 1])
                                
                                with col1:
                                    st.markdown(f"**{idx+1}. {title}**")
                                    
                                    # Display authors if available
                                    authors = article.get('author', [])
                                    if authors:
                                        author_names = [f"{author.get('family', '')}, {author.get('given', '')}" for author in authors[:3]]
                                        st.markdown(f"*{', '.join(author_names)}{' et al.' if len(authors) > 3 else ''}*")
                                    
                                    # Display journal if available
                                    journal = article.get('container-title', [''])[0]
                                    if journal:
                                        st.markdown(f"Journal: {journal}")
                                
                                with col2:
                                    if st.checkbox("Include", key=f"include_{idx}"):
                                        citation = format_citation(article, citation_style)
                                        if citation:
                                            selected_citations.append(citation)
                                            st.success("Added")
                                        else:
                                            st.error("Invalid citation")
                            
                            st.markdown("---")
                        
                        # Show the selected citations as a bibliography
                        if selected_citations:
                            st.markdown("### Bibliography")
                            for cite in selected_citations:
                                st.markdown(f"- {cite}")
                            
                            # Export options
                            if st.button("Copy to Clipboard", key="copy_citations"):
                                st.success("Citations copied to clipboard!")
                            
                            # Store in session state for use in reports
                            if 'citations' not in st.session_state:
                                st.session_state.citations = []
                            
                            st.session_state.citations.extend(selected_citations)
                            
                            # Export as text
                            st.download_button(
                                "Export Bibliography",
                                "\n\n".join(selected_citations),
                                file_name="bibliography.txt",
                                mime="text/plain"
                            )
                    else:
                        st.warning("No results found. Try different keywords.")
            else:
                st.error("Please enter a search query.")
        
        # Manual citation entry section
        st.markdown("### Manual Citation Entry")
        
        with st.expander("Add Citation Manually", expanded=False):
            with st.form("manual_citation_form"):
                manual_title = st.text_input("Title", key="manual_title")
                manual_authors = st.text_input("Authors (comma separated)", key="manual_authors")
                manual_year = st.text_input("Year", key="manual_year")
                manual_journal = st.text_input("Journal/Source", key="manual_journal", help="Leave blank if not applicable")
                manual_doi = st.text_input("DOI", key="manual_doi", help="Optional")
                manual_url = st.text_input("URL", key="manual_url", help="Optional")
                
                manual_submit = st.form_submit_button("Add Citation")
            
            if manual_submit:
                if manual_title and manual_authors and manual_year:
                    # Format manual citation
                    manual_citation = f"{manual_authors} ({manual_year}). {manual_title}"
                    if manual_journal:
                        manual_citation += f". {manual_journal}"
                    if manual_doi:
                        manual_citation += f". https://doi.org/{manual_doi}"
                    elif manual_url:
                        manual_citation += f". {manual_url}"
                    
                    # Add to session state
                    if 'citations' not in st.session_state:
                        st.session_state.citations = []
                    
                    st.session_state.citations.append(manual_citation)
                    
                    st.success("Manual citation added successfully!")
                    st.markdown(f"**Added citation:**\n{manual_citation}")
                else:
                    st.error("Title, authors, and year are required.")
        
        # Show current bibliography in session state
        if 'citations' in st.session_state and st.session_state.citations:
            st.markdown("### Your Bibliography")
            
            for i, citation in enumerate(st.session_state.citations):
                col1, col2 = st.columns([10, 1])
                
                with col1:
                    st.markdown(f"{i+1}. {citation}")
                
                with col2:
                    if st.button("🗑️", key=f"delete_citation_{i}"):
                        st.session_state.citations.pop(i)
                        st.success("Citation removed")
                        st.rerun()
            
            # Export all citations
            st.download_button(
                "Export Complete Bibliography",
                "\n\n".join(st.session_state.citations),
                file_name="complete_bibliography.txt",
                mime="text/plain"
            )
    
    except Exception as e:
        logger.error(f"Error rendering citation tool: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in citation tool: {str(e)}")

# ----------------------------------------------------------------
# Insight Assistant Page
# ----------------------------------------------------------------

def render_insight_assistant():
    """Render the insight report assistant page"""
    try:
        render_header()
        
        st.markdown("""
        <h2>Insight Report Assistant</h2>
        <p>Generate insights from AI evaluation data</p>
        """, unsafe_allow_html=True)
        
        # Default guidelines for insight reports
        DEFAULT_KNOWLEDGE_BASE = """
        Insight report writing involves analyzing data to extract meaningful patterns and actionable
        information. Key aspects include:
        1. Clarity: Present findings in a clear, concise manner.
        2. Relevance: Focus on insights that are relevant to the business or research question.
        3. Data-driven: Back up insights with data and evidence.
        4. Actionable: Provide recommendations or next steps based on the insights.
        5. Visual aids: Use charts, graphs, or tables to illustrate key points.
        6. Structure: Organize the report with an executive summary, main findings, and conclusion.
        7. Context: Explain the significance of the insights in the broader context.
        8. Objectivity: Present unbiased analysis, acknowledging limitations or uncertainties.
        """
        
        # Configuration sidebar
        with st.sidebar:
            st.markdown("#### Insight Generation Settings")
            temperature = st.slider("Temperature:", 0.0, 1.0, 0.7, key="insight_temperature")
            max_tokens = st.number_input("Max Tokens:", 50, 2048, 150, key="insight_max_tokens")
        
        # Guidelines section
        st.markdown("### Report Guidelines")
        knowledge_base_input = st.text_area(
            "Guidelines:",
            value=DEFAULT_KNOWLEDGE_BASE,
            height=150,
            key="knowledge_base"
        )
        
        # Additional context
        st.markdown("### Additional Context")
        context_input = st.text_area(
            "Context:",
            height=100,
            key="context_input",
            help="Add any specific context for the insight generation"
        )
        
        # Data input methods
        st.markdown("### Data Input")
        
        # Option 1: Use security test results
        use_test_results = st.checkbox("Use Current Security Test Results", key="use_test_results")
        
        if use_test_results:
            if st.session_state.test_results:
                vulnerabilities = st.session_state.test_results.get("vulnerabilities", [])
                
                if vulnerabilities:
                    st.success(f"Using {len(vulnerabilities)} vulnerability findings from current test results")
                    
                    if st.button("Generate Insights from Test Results", key="gen_test_insights"):
                        with st.spinner("Generating insights..."):
                            insights = []
                            progress_bar = st.progress(0)
                            
                            for i, vuln in enumerate(vulnerabilities):
                                # Create input for insight generation
                                user = "Security Analyst"
                                category = vuln.get("severity", "medium")
                                prompt = f"Analyze vulnerability: {vuln.get('test_name', 'Unknown')}"
                                response = vuln.get("details", "No details")
                                
                                # Generate insight
                                insight = generate_insight(
                                    user, 
                                    category,
                                    prompt,
                                    response,
                                    knowledge_base_input,
                                    context_input,
                                    temperature,
                                    max_tokens
                                )
                                
                                insights.append({
                                    "vulnerability_id": vuln.get("id", "Unknown"),
                                    "vulnerability_name": vuln.get("test_name", "Unknown"),
                                    "severity": vuln.get("severity", "medium"),
                                    "insight": insight
                                })
                                
                                # Update progress
                                progress_bar.progress((i + 1) / len(vulnerabilities))
                            
                            # Store in session state
                            if 'insights' not in st.session_state:
                                st.session_state.insights = []
                            
                            st.session_state.insights.extend(insights)
                            
                            # Show insights
                            st.success("Insights generated successfully!")
                            
                            st.markdown("### Generated Insights")
                            for insight_data in insights:
                                severity_color = {
                                    "low": "blue",
                                    "medium": "orange",
                                    "high": "red",
                                    "critical": "darkred"
                                }.get(insight_data["severity"], "gray")
                                
                                st.markdown(f"""
                                <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                                    <div style="font-weight: bold;">{insight_data["vulnerability_id"]}: {insight_data["vulnerability_name"]}</div>
                                    <div>{insight_data["insight"]}</div>
                                    <div style="font-size: 0.8em; opacity: 0.7;">Severity: {insight_data["severity"].upper()}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Export option
                            insights_df = pd.DataFrame(insights)
                            st.download_button(
                                "Export Insights",
                                insights_df.to_csv(index=False).encode('utf-8'),
                                file_name="security_insights.csv",
                                mime="text/csv"
                            )
                else:
                    st.warning("No vulnerabilities found in current test results.")
            else:
                st.error("No test results available. Please run a security assessment first.")
        
        # Option 2: Upload CSV data
        st.markdown("### Or Upload CSV Data")
        
        # Sample data for download
        sample_data = "User,Category,Prompt,Response\nJohn Doe,Security,How secure is our API?,Several vulnerabilities were found\nJane Smith,Performance,Is the model efficient?,Response time averages 200ms"
        
        st.download_button(
            "Download Sample CSV",
            sample_data,
            "sample_insights.csv",
            "text/csv",
            key="download_sample_insights"
        )
        
        uploaded_file = st.file_uploader("Upload CSV", type="csv", key="upload_insights_csv")
        
        if uploaded_file:
            df = process_csv(uploaded_file)
            if df is not None:
                st.success("CSV uploaded successfully!")
                st.dataframe(df.head())
                
                if st.button("Generate Insights from CSV", key="gen_csv_insights"):
                    with st.spinner("Generating insights..."):
                        insights = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, row in df.iterrows():
                            status_text.text(f"Processing {idx + 1}/{len(df)}")
                            
                            insight = generate_insight(
                                row['User'],
                                row['Category'],
                                row['Prompt'],
                                row['Response'],
                                knowledge_base_input,
                                context_input,
                                temperature,
                                max_tokens
                            )
                            
                            insights.append(insight)
                            progress_bar.progress((idx + 1) / len(df))
                        
                        # Add insights to dataframe
                        df['Generated Insight'] = insights
                        status_text.text("Processing complete!")
                        
                        # Store in session state
                        if 'insights_dataframes' not in st.session_state:
                            st.session_state.insights_dataframes = []
                        
                        st.session_state.insights_dataframes.append({
                            "name": uploaded_file.name,
                            "data": df
                        })
                        
                        # Show results
                        st.success("Insights generated successfully!")
                        st.dataframe(df)
                        
                        # Export options
                        st.download_button(
                            "Download Results CSV",
                            df.to_csv(index=False).encode('utf-8'),
                            "insights_report.csv",
                            "text/csv",
                            key="download_insights_report"
                        )
        
        # Option 3: Manual entry
        st.markdown("### Or Enter Data Manually")
        
        with st.form("manual_insight_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                manual_user = st.text_input("User/Role", key="manual_insight_user")
                manual_category = st.text_input("Category", key="manual_insight_category")
            
            with col2:
                manual_prompt = st.text_input("Prompt/Question", key="manual_insight_prompt")
                manual_response = st.text_area("Response/Data", key="manual_insight_response", height=100)
            
            submit_button = st.form_submit_button("Generate Insight")
        
        if submit_button:
            if not manual_user or not manual_category or not manual_prompt or not manual_response:
                st.error("All fields are required")
            else:
                with st.spinner("Generating insight..."):
                    insight = generate_insight(
                        manual_user,
                        manual_category,
                        manual_prompt,
                        manual_response,
                        knowledge_base_input,
                        context_input,
                        temperature,
                        max_tokens
                    )
                    
                    # Store the insight
                    if 'manual_insights' not in st.session_state:
                        st.session_state.manual_insights = []
                    
                    st.session_state.manual_insights.append({
                        "user": manual_user,
                        "category": manual_category,
                        "prompt": manual_prompt,
                        "response": manual_response,
                        "insight": insight,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Show result
                    st.success("Insight generated successfully!")
                    
                    st.markdown("### Generated Insight")
                    st.markdown(f"""
                    <div style="padding: 15px; border-left: 4px solid {get_theme()["primary"]}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{manual_category} Insight</div>
                        <div>{insight}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Generated for: {manual_user}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # View previous insights
        if (('insights' in st.session_state and st.session_state.insights) or 
            ('manual_insights' in st.session_state and st.session_state.manual_insights) or
            ('insights_dataframes' in st.session_state and st.session_state.insights_dataframes)):
            
            st.markdown("### Previous Insights")
            
            insight_sources = []
            
            if 'insights' in st.session_state and st.session_state.insights:
                insight_sources.append("Security Test Insights")
            
            if 'manual_insights' in st.session_state and st.session_state.manual_insights:
                insight_sources.append("Manual Insights")
            
            if 'insights_dataframes' in st.session_state and st.session_state.insights_dataframes:
                for df_info in st.session_state.insights_dataframes:
                    insight_sources.append(f"CSV: {df_info['name']}")
            
            selected_source = st.selectbox("Select Source", insight_sources, key="insight_source_select")
            
            if selected_source == "Security Test Insights" and 'insights' in st.session_state:
                insights = st.session_state.insights
                
                for i, insight_data in enumerate(insights):
                    severity_color = {
                        "low": "blue",
                        "medium": "orange",
                        "high": "red",
                        "critical": "darkred"
                    }.get(insight_data["severity"], "gray")
                    
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{insight_data["vulnerability_id"]}: {insight_data["vulnerability_name"]}</div>
                        <div>{insight_data["insight"]}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Severity: {insight_data["severity"].upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif selected_source == "Manual Insights" and 'manual_insights' in st.session_state:
                manual_insights = st.session_state.manual_insights
                
                for i, insight_data in enumerate(manual_insights):
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 4px solid {get_theme()["primary"]}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
                        <div style="font-weight: bold;">{insight_data["category"]} Insight</div>
                        <div>{insight_data["insight"]}</div>
                        <div style="font-size: 0.8em; opacity: 0.7;">Generated for: {insight_data["user"]} on {insight_data["timestamp"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif selected_source.startswith("CSV:") and 'insights_dataframes' in st.session_state:
                csv_name = selected_source[5:].strip()
                
                for df_info in st.session_state.insights_dataframes:
                    if df_info["name"] == csv_name:
                        st.dataframe(df_info["data"])
                        break
    
    except Exception as e:
        logger.error(f"Error rendering insight assistant: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in insight assistant: {str(e)}")

# ----------------------------------------------------------------
# Main Application Routing
# ----------------------------------------------------------------

def main():
    """Main application entry point with error handling"""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Clean up threads
        cleanup_threads()
        
        # Apply CSS
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # Show error message if exists
        if st.session_state.error_message:
            st.markdown(f"""
            <div class="error-message">
                <strong>Error:</strong> {st.session_state.error_message}
            </div>
            """, unsafe_allow_html=True)
            
            # Add button to clear error
            if st.button("Clear Error"):
                st.session_state.error_message = None
                safe_rerun()
        
        # Render sidebar
        sidebar_navigation()
        
        # Render content based on current page
        if st.session_state.current_page == "Dashboard":
            render_dashboard()
        elif st.session_state.current_page == "Target Management":
            render_target_management()
        elif st.session_state.current_page == "Test Configuration":
            render_test_configuration()
        elif st.session_state.current_page == "Run Assessment":
            render_run_assessment()
        elif st.session_state.current_page == "Results Analyzer":
            render_results_analyzer()
        elif st.session_state.current_page == "Ethical AI Testing":
            render_ethical_ai_testing()
        elif st.session_state.current_page == "Environmental Impact":
            render_environmental_impact()
        elif st.session_state.current_page == "Bias Testing":
            render_bias_testing()
        elif st.session_state.current_page == "Bias Comparison":
            render_bias_comparison()
        elif st.session_state.current_page == "Bias Labs Integration":
            render_bias_labs_integration()
        elif st.session_state.current_page == "HELM Evaluation":
            render_helm_evaluation()
        elif st.session_state.current_page == "Multi-Format Import":
            render_file_import()
        elif st.session_state.current_page == "High-Volume Testing":
            render_high_volume_testing()
        elif st.session_state.current_page == "Sustainability Dashboard":
            render_sustainability_dashboard()
        elif st.session_state.current_page == "Report Generator":
            render_report_generator()
        elif st.session_state.current_page == "Citation Tool":
            render_citation_tool()
        elif st.session_state.current_page == "Insight Assistant":
            render_insight_assistant()
        elif st.session_state.current_page == "Knowledge Base":
            render_knowledge_base_integration()
        elif st.session_state.current_page == "Settings":
            render_settings()
        else:
            # Default to dashboard if invalid page
            logger.warning(f"Invalid page requested: {st.session_state.current_page}")
            st.session_state.current_page = "Dashboard"
            render_dashboard()
    
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}")
        logger.critical(traceback.format_exc())
        st.error(f"Critical application error: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
