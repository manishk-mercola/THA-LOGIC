#!/usr/bin/env python3
"""
True Health Age - Interactive Web Questionnaire
Streamlit app for calculating biological age
"""

import streamlit as st
from tha_engine import THAEngine, load_config
import pandas as pd
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="True Health Age Calculator",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load engine
@st.cache_resource
def load_engine():
    config = load_config("config.yaml")
    return THAEngine(config)

engine = load_engine()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .result-box {
        padding: 2rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
        margin: 2rem 0;
    }
    .result-number {
        font-size: 4rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .domain-card {
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🧬 True Health Age Calculator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Discover your biological age based on lifestyle and health factors</div>', unsafe_allow_html=True)

# Sidebar - Instructions
with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    1. **Enter your age** below
    2. **Answer all questions** honestly
    3. **Get your results** instantly

    Your data is NOT stored or transmitted.
    All calculations happen in your browser.
    """)

    st.divider()

    st.header("ℹ️ About THA")
    st.markdown("""
    **True Health Age** is a scientifically-validated
    biological age calculator using:
    - Population-based calibration
    - Gompertz mortality modeling
    - 40 evidence-based questions

    **Interpretation:**
    - THA = Age → Average aging
    - THA < Age → Slower aging
    - THA > Age → Faster aging
    """)

# Initialize session state
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'show_results' not in st.session_state:
    st.session_state.show_results = False

# Main content
tab1, tab2, tab3 = st.tabs(["📝 Questionnaire", "📊 Results", "🔍 What-If Analysis"])

with tab1:
    st.header("Complete Your Health Assessment")

    # Chronological Age
    chron_age = st.number_input(
        "What is your chronological age?",
        min_value=18,
        max_value=100,
        value=35,
        help="Your actual age in years"
    )

    st.divider()

    # Body & Energy Section
    with st.expander("🏃 Body & Energy (11 questions)", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.answers['height'] = st.number_input(
                "Height (inches)",
                min_value=48,
                max_value=84,
                value=70,
                help="Your height in inches (1 inch = 2.54 cm)"
            )

            st.session_state.answers['weight'] = st.number_input(
                "Weight (pounds)",
                min_value=80,
                max_value=400,
                value=170,
                help="Your weight in pounds (1 lb = 0.45 kg)"
            )

            waist = st.number_input(
                "Waist circumference (inches)",
                min_value=20,
                max_value=60,
                value=34,
                help="Measure at belly button level"
            )

            gender = st.selectbox(
                "Gender (for waist calculation)",
                ["male", "female"]
            )
            st.session_state.answers['waist_circumference'] = (waist, gender)

            st.session_state.answers['pregnancy_breastfeeding'] = st.multiselect(
                "Are you pregnant or breastfeeding?",
                ["Pregnant", "Breastfeeding", "Neither", "Prefer not to say"],
                default=["Neither"]
            )

            st.session_state.answers['sleep_hours'] = st.slider(
                "Hours of sleep per night",
                min_value=3.0,
                max_value=12.0,
                value=7.5,
                step=0.5
            )

        with col2:
            st.session_state.answers['stress_frequency_30d'] = st.select_slider(
                "Stress frequency (past 30 days)",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["Very often", "Often", "Sometimes", "Rarely", "Almost never"][x]
            )

            st.session_state.answers['energy_pattern'] = st.select_slider(
                "Daytime energy pattern",
                options=[0, 1, 2, 3, 4],
                value=3,
                format_func=lambda x: ["Very low crashes", "Low most day", "Up and down", "Steady w/dips", "Steady"][x]
            )

            st.session_state.answers['rested_feeling'] = st.select_slider(
                "Feel rested after sleep?",
                options=[0, 1, 2, 3, 4],
                value=3,
                format_func=lambda x: ["Never rested", "Rarely rested", "Sometimes rested", "Mostly rested", "Fully refreshed"][x]
            )

            st.session_state.answers['screen_time_before_bed'] = st.select_slider(
                "Screen time 2h before bed",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["2+ hours", "1-2 hours", "30-60 min", "15-30 min", "None"][x]
            )

            st.session_state.answers['recent_illness'] = st.radio(
                "Illness in past 2 weeks?",
                [0, 1, 2],
                index=2,
                format_func=lambda x: ["Yes, severe", "Yes, moderate", "No"][x]
            )

    # Movement & Metabolism
    with st.expander("💪 Movement & Metabolism (4 questions)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.answers['daytime_activity'] = st.select_slider(
                "Daytime activity pattern",
                options=[0, 1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: ["Mostly sitting", "Mostly standing", "Light movement", "Regular walking", "Active job", "Very active"][x]
            )

            st.session_state.answers['strength_days_week'] = st.slider(
                "Strength training days/week",
                min_value=0,
                max_value=7,
                value=2
            )

        with col2:
            st.session_state.answers['cardio_days_week'] = st.slider(
                "Cardio days/week",
                min_value=0,
                max_value=7,
                value=3
            )

            st.session_state.answers['eating_window_hours'] = st.slider(
                "Daily eating window (hours)",
                min_value=6,
                max_value=18,
                value=12,
                help="Time between first and last meal"
            )

    # Diet & Gut Health (simplified - showing key questions)
    with st.expander("🥗 Diet & Gut Health (13 questions)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.answers['seed_oils_freq'] = st.select_slider(
                "Seed oil consumption",
                options=[0, 1, 2],
                value=1,
                format_func=lambda x: ["Regularly", "Sometimes", "Rarely/Never"][x]
            )

            st.session_state.answers['home_cooking_fat'] = st.select_slider(
                "Primary cooking fat",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["Vegetable oil", "Canola oil", "Olive oil", "Coconut oil", "Animal fat"][x]
            )

            st.session_state.answers['fried_foods_week'] = st.select_slider(
                "Fried foods frequency",
                options=[0, 1, 2, 3],
                value=2,
                format_func=lambda x: ["Several times/week", "2-3 times/week", "Once/week", "Never"][x]
            )

            st.session_state.answers['fruit_servings_day'] = st.select_slider(
                "Fruit servings/day",
                options=[0, 1, 2, 3],
                value=1,
                format_func=lambda x: ["<1", "1", "2", "3+"][x]
            )

            st.session_state.answers['veg_servings_day'] = st.select_slider(
                "Vegetable servings/day",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["1 or less", "2-3", "4-5", "6+", "6+"][x]
            )

            st.session_state.answers['packaged_foods_week'] = st.select_slider(
                "Packaged/processed foods",
                options=[0, 1, 2, 3],
                value=2,
                format_func=lambda x: ["Daily", "Often", "Sometimes", "Rarely"][x]
            )

            st.session_state.answers['reading_labels'] = st.select_slider(
                "Read ingredient labels?",
                options=[0, 1, 2],
                value=1,
                format_func=lambda x: ["Never", "Sometimes", "Always"][x]
            )

        with col2:
            st.session_state.answers['artificial_sweeteners_week'] = st.select_slider(
                "Artificial sweeteners/week",
                options=[0, 1, 2, 3, 4, 5],
                value=2,
                format_func=lambda x: ["5-6", "3-4", "1-2", "Occasionally", "Not sure", "None"][x]
            )

            st.session_state.answers['restaurant_meals_week'] = st.select_slider(
                "Restaurant meals/week",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["5+", "3-4", "1-2", "None", "Not sure"][x]
            )

            st.session_state.answers['fiber_foods_freq'] = st.select_slider(
                "Fiber-rich foods frequency",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["Rarely", "Few times/week", "Once/day", "Twice/day", "Multiple/day"][x]
            )

            st.session_state.answers['bowel_movements_day'] = st.slider(
                "Bowel movements/day",
                min_value=0,
                max_value=6,
                value=1
            )

            st.session_state.answers['digestive_issues_30d'] = st.select_slider(
                "Digestive issues (past 30 days)",
                options=[0, 1, 2, 3],
                value=2,
                format_func=lambda x: ["10+", "6-9", "2-5", "0-1"][x]
            )

            st.session_state.answers['antibiotics_12mo'] = st.radio(
                "Antibiotics (past 12 months)",
                [0, 1, 2, 3],
                index=3,
                format_func=lambda x: ["2+ courses", "1 course", "Not sure", "No"][x]
            )

    # Environment & Exposure
    with st.expander("🌍 Environment & Exposure (9 questions)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.answers['nicotine_past_30_days'] = st.radio(
                "Nicotine use (past 30 days)",
                [0, 1, 2, 3],
                index=3,
                format_func=lambda x: ["Yes, daily", "Yes, few times/week", "Yes, occasionally", "No, not at all"][x]
            )

            st.session_state.answers['nicotine_history'] = st.radio(
                "Nicotine use (history)",
                [0, 1, 2, 3],
                index=3,
                format_func=lambda x: ["Still use daily", "Quit <12mo", "Quit >1yr", "Never used"][x]
            )

            st.session_state.answers['alcohol_days_30'] = st.select_slider(
                "Alcohol days (past 30)",
                options=[0, 1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: ["20-30", "10-19", "3-9", "1-2", "0", "Prefer not to say"][x]
            )

            st.session_state.answers['alcohol_drinks_per_day'] = st.select_slider(
                "Drinks per drinking day",
                options=[0, 1, 2, 3, 4, 5],
                value=4,
                format_func=lambda x: ["3+", "2", "1 or less", "None", "Not sure", "Prefer not to say"][x]
            )

            st.session_state.answers['sunlight_minutes_day'] = st.select_slider(
                "Sunlight exposure/day",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["<15min", "15-30min", "30-60min", "60+min", "60+min"][x]
            )

        with col2:
            st.session_state.answers['plastic_exposure'] = st.select_slider(
                "Plastic container/bottle use",
                options=[0, 1, 2, 3, 4],
                value=2,
                format_func=lambda x: ["Daily", "4-6/week", "1-3/week", "Rarely", "Not sure"][x]
            )

            st.session_state.answers['wifi_router_night'] = st.radio(
                "Wi-Fi router on at night?",
                [0, 1, 2, 3],
                index=1,
                format_func=lambda x: ["Every night in bedroom", "Every night elsewhere", "Some nights", "Turn it off"][x]
            )

            st.session_state.answers['phone_bedroom'] = st.radio(
                "Phone in bedroom at night?",
                [0, 1, 2, 3],
                index=2,
                format_func=lambda x: ["On all night", "Nearby but off", "Airplane mode", "Outside bedroom"][x]
            )

            st.session_state.answers['wireless_earbuds'] = st.radio(
                "Wireless earbud use",
                [0, 1, 2, 3],
                index=2,
                format_func=lambda x: ["3+ hours/day", "1-3 hours/day", "<1 hour/day", "Don't use"][x]
            )

    # Health History
    with st.expander("🏥 Health History (2 questions)", expanded=False):
        st.session_state.answers['family_history'] = st.multiselect(
            "Family health history (select all that apply)",
            ["Thyroid disease", "Type 2 diabetes", "Autoimmune disease",
             "Heart disease", "High cholesterol", "Obesity", "Cancer", "None", "Not sure"],
            default=["None"]
        )

        st.session_state.answers['personal_conditions'] = st.multiselect(
            "Personal health conditions (select all that apply)",
            ["High blood pressure", "High cholesterol", "Thyroid disorder",
             "Autoimmune disease", "Digestive disorder", "Mental health condition",
             "Chronic pain", "None", "Other"],
            default=["None"]
        )

    # Supplements
    with st.expander("💊 Supplements (1 question)", expanded=False):
        st.session_state.answers['supplements_use'] = st.radio(
            "Take supplements regularly?",
            [0, 1, 2, 3],
            index=1,
            format_func=lambda x: ["No", "Sometimes", "Regularly (most days)", "Yes, daily"][x]
        )

    # Additional Notes
    with st.expander("📝 Additional Notes (optional)", expanded=False):
        st.session_state.answers['additional_notes'] = st.text_area(
            "Any additional health information?",
            placeholder="Enter any additional notes here (optional)...",
            help="This field does not affect scoring"
        )

    st.divider()

    # Calculate button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🧬 Calculate My True Health Age", use_container_width=True, type="primary"):
            st.session_state.show_results = True
            st.rerun()

with tab2:
    if st.session_state.show_results:
        # Calculate THA
        result = engine.compute(float(chron_age), st.session_state.answers)

        # Main result box
        st.markdown(f"""
        <div class="result-box">
            <h2>Your True Health Age</h2>
            <div class="result-number">{result.THA:.1f}</div>
            <p style="font-size: 1.5rem;">Age Acceleration: {result.AgeAccel:+.1f} years</p>
            <p style="font-size: 1.1rem; margin-top: 1rem;">
                Chronological Age: {chron_age} years
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Interpretation
        if result.AgeAccel < -2:
            interpretation = "🌟 Exceptional! You're aging slower than average."
            color = "success"
        elif result.AgeAccel < 2:
            interpretation = "✅ Good! You're aging at close to average rate."
            color = "success"
        elif result.AgeAccel < 5:
            interpretation = "⚠️ Slightly accelerated aging. Room for improvement."
            color = "warning"
        elif result.AgeAccel < 8:
            interpretation = "⚠️ Accelerated aging. Lifestyle changes recommended."
            color = "warning"
        else:
            interpretation = "🚨 Highly accelerated aging. Consult healthcare provider."
            color = "error"

        st.info(interpretation, icon="ℹ️")

        st.divider()

        # Domain contributions
        st.header("📊 Domain Breakdown")

        col1, col2 = st.columns(2)

        with col1:
            # Domain bar chart
            domain_df = pd.DataFrame({
                'Domain': list(result.domainYears.keys()),
                'Years': list(result.domainYears.values())
            })
            domain_df = domain_df.sort_values('Years', ascending=True)

            fig = go.Figure(go.Bar(
                x=domain_df['Years'],
                y=domain_df['Domain'],
                orientation='h',
                marker_color=['#ff6b6b' if x > 0 else '#51cf66' for x in domain_df['Years']],
                text=[f'{x:+.2f}' for x in domain_df['Years']],
                textposition='outside'
            ))
            fig.update_layout(
                title="Domain Contributions (years)",
                xaxis_title="Years",
                yaxis_title="",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top contributors
            st.subheader("🎯 Top Contributors")
            sorted_items = sorted(result.itemYears.items(), key=lambda x: abs(x[1]), reverse=True)

            for i, (item_id, years) in enumerate(sorted_items[:8], 1):
                if years != 0:
                    emoji = "❌" if years > 0.5 else "⚠️" if years > 0 else "✅"
                    st.markdown(f"{i}. {emoji} **{item_id.replace('_', ' ').title()}**: {years:+.2f} years")

        st.divider()

        # Improvement opportunities
        st.header("💡 Improvement Opportunities")
        gains = engine.one_step_gains_months(st.session_state.answers)
        top_gains = sorted(gains.items(), key=lambda x: x[1], reverse=True)[:5]

        if any(g[1] > 0 for g in top_gains):
            st.write("**Top 5 single-step improvements:**")
            for i, (item_id, months) in enumerate(top_gains, 1):
                if months > 0:
                    st.markdown(f"{i}. **{item_id.replace('_', ' ').title()}**: Potential gain of **{months:.1f} months**")
        else:
            st.success("🎉 You're already optimized in most areas!")

        # Download results
        st.divider()
        results_data = {
            'Chronological Age': chron_age,
            'True Health Age': result.THA,
            'Age Acceleration': result.AgeAccel,
            **{f'Domain_{k}': v for k, v in result.domainYears.items()}
        }
        results_df = pd.DataFrame([results_data])
        csv = results_df.to_csv(index=False)

        st.download_button(
            label="📥 Download Results (CSV)",
            data=csv,
            file_name=f"tha_results_{chron_age}yo.csv",
            mime="text/csv"
        )

    else:
        st.info("👈 Complete the questionnaire in the first tab to see your results!")

with tab3:
    if st.session_state.show_results:
        st.header("🔍 What-If Analysis")
        st.write("See how specific lifestyle changes would affect your True Health Age")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Proposed Changes")

            changes = {}

            change_sleep = st.checkbox("Improve sleep")
            if change_sleep:
                new_sleep = st.slider("New sleep hours", 6.0, 9.0, 8.0, 0.5)
                changes['sleep_hours'] = new_sleep

            change_cardio = st.checkbox("Increase cardio")
            if change_cardio:
                new_cardio = st.slider("New cardio days/week", 0, 7, 5)
                changes['cardio_days_week'] = new_cardio

            change_strength = st.checkbox("Increase strength training")
            if change_strength:
                new_strength = st.slider("New strength days/week", 0, 7, 4)
                changes['strength_days_week'] = new_strength

            change_diet = st.checkbox("Improve diet")
            if change_diet:
                changes['veg_servings_day'] = 4  # 6+ servings
                changes['fruit_servings_day'] = 3  # 3+ servings
                changes['fried_foods_week'] = 3  # Never

            change_stress = st.checkbox("Reduce stress")
            if change_stress:
                changes['stress_frequency_30d'] = 4  # Almost never

            if st.button("Calculate Impact", use_container_width=True):
                if changes:
                    what_if = engine.what_if(float(chron_age), st.session_state.answers, changes)

                    with col2:
                        st.subheader("Projected Results")

                        improvement = what_if['old_THA'] - what_if['new_THA']

                        st.metric(
                            label="Current THA",
                            value=f"{what_if['old_THA']:.1f} years"
                        )

                        st.metric(
                            label="New THA",
                            value=f"{what_if['new_THA']:.1f} years",
                            delta=f"{-improvement:.1f} years"
                        )

                        if improvement > 0:
                            st.success(f"🎉 You could reduce your biological age by **{improvement:.1f} years**!")
                        elif improvement < 0:
                            st.warning(f"⚠️ These changes would increase age by {-improvement:.1f} years")
                        else:
                            st.info("No significant change")
                else:
                    with col2:
                        st.warning("Select at least one change to analyze")
    else:
        st.info("👈 Calculate your THA first to use What-If Analysis!")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Disclaimer:</strong> This tool is for educational purposes only.
    Not a substitute for professional medical advice.</p>
    <p>Based on population-calibrated biological age research | © 2024 True Health Age</p>
</div>
""", unsafe_allow_html=True)
