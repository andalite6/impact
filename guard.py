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

# Set page configuration with custom theme - this must be the first Streamlit command!
try:
    st.set_page_config(
        page_title="ImpactGuard - AI Security & Sustainability Hub",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception as e:
    st.error(f"Error setting page config: {e}")
    st.stop()

# Setup OpenAI API key securely (for reporting functionality)
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    logger.info("OpenAI API key loaded from secrets")
except Exception as e:
    # For development, allow user to input their API key
    st.session_state.openai_api_missing = True
    logger.warning("OpenAI API key not found in secrets. Will prompt user for key.")

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
            
        # API key management
        if 'openai_api_missing' not in st.session_state:
            st.session_state.openai_api_missing = False
            
        if 'user_provided_api_key' not in st.session_state:
            st.session_state.user_provided_api_key = ""
            
        # Target selection state
        if 'selected_target' not in st.session_state:
            st.session_state.selected_target = None
            
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

# Severity color mapping
def get_severity_color(severity):
    """Get color for a severity level"""
    severity_colors = {
        "low": "blue",
        "medium": "orange",
        "high": "red",
        "critical": "darkred"
    }
    return severity_colors.get(severity, "gray")

# Display insight data
def display_insight(insight_data):
    """Display an insight with proper formatting"""
    severity_color = get_severity_color(insight_data["severity"])
    
    st.markdown(f"""
    <div style="padding: 10px; border-left: 4px solid {severity_color}; margin-bottom: 10px; background-color: rgba(0,0,0,0.05);">
        <div style="font-weight: bold;">{insight_data["vulnerability_id"]}: {insight_data["vulnerability_name"]}</div>
        <div>{insight_data["insight"]}</div>
        <div style="font-size: 0.8em; opacity: 0.7;">Severity: {insight_data["severity"].upper()}</div>
    </div>
    """, unsafe_allow_html=True)

# Export insights
def export_insights(insights):
    """Provide export functionality for insights"""
    insights_df = pd.DataFrame(insights)
    return st.download_button(
        "Export Insights",
        insights_df.to_csv(index=False).encode('utf-8'),
        file_name="security_insights.csv",
        mime="text/csv"
    )

# Process CSV data
def process_csv(uploaded_file):
    """Process uploaded CSV data safely"""
    try:
        return pd.read_csv(uploaded_file)
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        st.error(f"Failed to process CSV: {str(e)}")
        return None

# Generate insight
def generate_insight(user, category, prompt, response, knowledge_base, context, temperature=0.7, max_tokens=500):
    """Generate an insight based on input data"""
    try:
        # In a real app, this would use the OpenAI API
        # For this mock, we'll return a placeholder
        return f"Analysis shows that the {category} aspect needs attention based on the response pattern. Recommended action: review {category} settings and implement additional validation."
    except Exception as e:
        logger.error(f"Error generating insight: {str(e)}")
        return f"Error generating insight: {str(e)}"

# ----------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------

if __name__ == "__main__":
    try:
        # Initialize session state
        initialize_session_state()
        
        # Clean up any completed threads
        cleanup_threads()
        
        # Apply CSS
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # Render header
        render_header()
        
        # Display sidebar navigation
        sidebar_navigation()
        
        # Check for OpenAI API key if missing
        if st.session_state.openai_api_missing and st.session_state.user_provided_api_key == "":
            st.warning("OpenAI API key not found in application secrets. Some features will be limited.")
            with st.expander("Enter your API key to enable all features"):
                api_key = st.text_input("OpenAI API Key", type="password", 
                                        help="Your key will only be stored in this session and not saved.")
                if st.button("Save API Key"):
                    if api_key and api_key.startswith("sk-"):
                        openai.api_key = api_key
                        st.session_state.user_provided_api_key = api_key
                        st.success("API key saved for this session!")
                        st.rerun()
                    else:
                        st.error("Invalid API key format. Should start with 'sk-'")
        
        # Display any error messages
        if st.session_state.error_message:
            st.error(st.session_state.error_message)
            st.session_state.error_message = None  # Clear after displaying
            
        # Simple placeholder content for the dashboard
        if st.session_state.current_page == "Dashboard":
            st.title("🏠 Dashboard")
            st.subheader("Welcome to ImpactGuard")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(metric_card("Targets", len(st.session_state.targets)), unsafe_allow_html=True)
            with col2:
                st.markdown(metric_card("Tests Run", len(st.session_state.test_results)), unsafe_allow_html=True)
            with col3:
                st.markdown(metric_card("Vulnerabilities", st.session_state.vulnerabilities_found), unsafe_allow_html=True)
                
            st.markdown(modern_card("Getting Started", 
                        """
                        1. Add a target system in Target Management
                        2. Configure tests in Test Configuration
                        3. Run an assessment against your target
                        4. View results and generate reports
                        """, 
                        card_type="primary", 
                        icon="🚀"), 
                       unsafe_allow_html=True)
            
            # Show quick setup if no targets
            if not st.session_state.targets:
                st.write("---")
                st.subheader("Quick Setup")
                with st.form("quick_setup"):
                    target_name = st.text_input("Add your first target name")
                    target_url = st.text_input("Target URL or Endpoint")
                    if st.form_submit_button("Create Target"):
                        if target_name and target_url:
                            new_target = {
                                "id": f"target_1",
                                "name": target_name,
                                "url": target_url,
                                "type": "LLM",
                                "added": datetime.now().isoformat()
                            }
                            st.session_state.targets.append(new_target)
                            st.success(f"Added new target: {target_name}")
                            st.session_state.current_page = "Run Assessment"
                            st.rerun()
                       
        elif st.session_state.current_page == "Target Management":
            st.title("🎯 Target Management")
            st.write("Add and manage your target systems here.")
            
            # Add a simple form to add new targets
            with st.form("add_target_form"):
                target_name = st.text_input("Target Name")
                target_url = st.text_input("Target URL/Endpoint")
                target_type = st.selectbox("Target Type", ["API", "Web Application", "LLM", "ML Model"])
                submit = st.form_submit_button("Add Target")
                
                if submit and target_name and target_url:
                    new_target = {
                        "id": f"target_{len(st.session_state.targets) + 1}",
                        "name": target_name,
                        "url": target_url,
                        "type": target_type,
                        "added": datetime.now().isoformat()
                    }
                    st.session_state.targets.append(new_target)
                    st.success(f"Added new target: {target_name}")
            
            # Display existing targets
            if st.session_state.targets:
                st.subheader("Your Targets")
                cols = st.columns(2)
                for i, target in enumerate(st.session_state.targets):
                    with cols[i % 2]:
                        st.markdown(
                            f"""
                            <div class="target-card">
                                <strong>{target['name']}</strong> ({target['type']})<br>
                                URL: {target['url']}<br>
                                Added: {target['added'].split('T')[0]}
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("Test", key=f"test_{target['id']}"):
                                st.session_state.current_page = "Run Assessment"
                                st.session_state.selected_target = target['id']
                                st.rerun()
                        with col2:
                            if st.button("Delete", key=f"del_{target['id']}"):
                                st.session_state.targets.remove(target)
                                st.success(f"Deleted {target['name']}")
                                st.rerun()
            else:
                st.info("No targets added yet. Add your first target above.")
        
        elif st.session_state.current_page == "Run Assessment":
            st.title("▶️ Run Assessment")
            
            if not st.session_state.targets:
                st.warning("No targets available. Please add a target in Target Management first.")
                if st.button("Go to Target Management"):
                    st.session_state.current_page = "Target Management"
                    st.rerun()
            else:
                # Target selection
                targets_dict = {t["id"]: t["name"] for t in st.session_state.targets}
                selected_id = st.selectbox("Select Target", 
                                          options=list(targets_dict.keys()),
                                          format_func=lambda x: targets_dict[x],
                                          index=0)
                
                # Find the selected target
                selected_target = next((t for t in st.session_state.targets if t["id"] == selected_id), None)
                
                if selected_target:
                    st.write(f"Running assessment against: **{selected_target['name']}** ({selected_target['type']})")
                    
                    # Test configuration
                    st.subheader("Test Configuration")
                    col1, col2 = st.columns(2)
                    with col1:
                        test_types = [
                            "OWASP Top 10 for LLMs",
                            "NIST AI Risk Management",
                            "Fairness Assessment",
                            "Data Privacy Compliance",
                            "Jailbreak Resistance"
                        ]
                        selected_tests = []
                        for test in test_types:
                            if st.checkbox(test, value=True):
                                selected_tests.append(test)
                    
                    with col2:
                        test_depth = st.slider("Test Depth", min_value=1, max_value=5, value=3,
                                              help="Higher values perform more thorough testing but take longer")
                        carbon_track = st.checkbox("Track Carbon Impact", value=True)
                    
                    # Get test vectors based on selection
                    test_vectors = get_mock_test_vectors()
                    
                    # Run button
                    if st.button("Start Assessment", type="primary"):
                        if not selected_tests:
                            st.error("Please select at least one test type.")
                        else:
                            with st.spinner("Running tests..."):
                                # Create a progress bar
                                progress_bar = st.progress(0)
                                
                                # Start test in a thread so UI remains responsive
                                def run_test_thread():
                                    try:
                                        st.session_state.running_test = True
                                        run_mock_test(selected_target, test_vectors, duration=5)  # shortened for demo
                                        st.session_state.running_test = False
                                    except Exception as e:
                                        logger.error(f"Test thread error: {e}")
                                        st.session_state.error_message = f"Test failed: {str(e)}"
                                        st.session_state.running_test = False
                                
                                # Create and start thread
                                test_thread = threading.Thread(target=run_test_thread)
                                test_thread.start()
                                st.session_state.active_threads.append(test_thread)
                                
                                # Monitor progress
                                while st.session_state.running_test:
                                    # Update progress bar
                                    progress_bar.progress(st.session_state.progress)
                                    
                                    # Display live stats
                                    stats_cols = st.columns(3)
                                    with stats_cols[0]:
                                        st.metric("Progress", f"{int(st.session_state.progress * 100)}%")
                                    with stats_cols[1]:
                                        st.metric("Vulnerabilities", st.session_state.vulnerabilities_found)
                                    with stats_cols[2]:
                                        if carbon_track:
                                            st.metric("Carbon Impact", "Measuring...")
                                    
                                    # Brief pause to prevent UI lag
                                    time.sleep(0.1)
                                
                                # Show completion
                                progress_bar.progress(1.0)
                                st.success(f"Assessment completed for {selected_target['name']}")
                                
                                # Navigate to results
                                st.session_state.current_page = "Results Analyzer"
                                st.rerun()
                
                    # Stop button (only show if test is running)
                    if st.session_state.running_test:
                        if st.button("Stop Test", type="secondary"):
                            st.session_state.running_test = False
                            st.warning("Test was stopped before completion.")
                
                # Display sample results if available
                if st.session_state.test_results and "vulnerabilities" in st.session_state.test_results:
                    st.subheader("Recent Results")
                    for vuln in st.session_state.test_results["vulnerabilities"][:3]:
                        severity_color = get_severity_color(vuln["severity"])
                        st.markdown(f"""
                        <div style="padding: 10px; border-left: 4px solid {severity_color}; background-color: rgba(0,0,0,0.05); margin-bottom: 10px;">
                            <div style="font-weight: bold;">{vuln["id"]}: {vuln["test_name"]}</div>
                            <div>{vuln["details"]}</div>
                            <div style="font-size: 0.8em; opacity: 0.7;">Severity: {vuln["severity"].upper()}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Add simple content for other pages
        else:
            st.title(f"{st.session_state.current_page}")
            st.info(f"This is the {st.session_state.current_page} page. Content is under development.")
            
    except Exception as e:
        error_msg = f"Application error: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        st.error(error_msg)
        st.code(traceback.format_exc())
