import streamlit as st
from app.db.database import init_db, get_prior_sessions, get_kb_snapshot, get_weak_areas
from app.core.pdf_parser import extract_sections
from app.core.prep_engine import generate_questions_only

# Initialize DB
init_db()

# Page config
st.set_page_config(
    page_title="Adaptive Doc Prep System",
    page_icon="📚",
    layout="wide"
)

# Load sections once
@st.cache_resource
def load_sections():
    return extract_sections("SLATEFALL_DOSSIER.pdf")

sections = load_sections()

# --- Sidebar ---
st.sidebar.title("📚 Adaptive Prep System")
st.sidebar.markdown("**SLATEFALL Dossier**")
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📝 Prep Session", "📊 History", "🗄️ KB Snapshot"]
)

# ========== HOME PAGE ==========
if page == "🏠 Home":
    st.title("Adaptive Document Preparation System")
    st.markdown("""
    An AI-powered study prep system that learns from your mistakes.

    **How it works:**
    1. Select sections from the SLATEFALL dossier to study
    2. Answer AI-generated MCQs
    3. Get scored with explanations for wrong answers
    4. On return visits, the system focuses on your weak areas
    """)
    st.divider()
    st.subheader("Available Sections")
    for num, data in sections.items():
        st.markdown(f"**Section {num}:** {data['title']}")

# ========== PREP SESSION PAGE ==========
elif page == "📝 Prep Session":
    st.title("📝 Start a Prep Session")

    # Reset button at top if session exists
    if "result" in st.session_state:
        if st.button("🔄 Start New Session"):
            for key in ["result", "submitted", "scored"]:
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()

    # Only show section selector if no active session
    if "result" not in st.session_state:
        st.subheader("Select sections to study:")
        selected = []
        cols = st.columns(2)
        for i, (num, data) in enumerate(sections.items()):
            col = cols[i % 2]
            if col.checkbox(f"Section {num}: {data['title']}", key=f"sec_{num}"):
                selected.append(num)

        st.divider()

        if st.button("🚀 Start Prep Session", disabled=len(selected) == 0):

            # Show weak areas if returning user
            prior = get_prior_sessions(selected)
            if prior:
                weak = get_weak_areas(selected)
                if weak:
                    st.info("🎯 **Adaptive Mode** — You've studied these sections before. Focusing on your weak areas:")
                    for w in weak[:5]:
                        st.markdown(f"- _{w['question_text']}_")
                    st.divider()

            # Progress bar while generating
            progress = st.progress(0, text="Starting question generation...")
            
            progress.progress(20, text="Loading SLATEFALL dossier...")
            result = None
            
            progress.progress(40, text="Analyzing sections...")
            
            import time
            
            # Generate in steps with progress updates
            progress.progress(60, text="Generating MCQs with AI...")
            result = generate_questions_only(section_ids=selected)
            
            progress.progress(90, text="Saving to knowledge base...")
            time.sleep(0.3)
            
            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

            st.session_state["result"] = result
            st.session_state["submitted"] = False
            st.session_state["scored"] = None
            st.rerun()

    # Show questions form
    if (
        "result" in st.session_state
        and not st.session_state.get("submitted", False)
    ):
        result = st.session_state["result"]
        questions = result["questions"]

        st.divider()

        # Adaptive mode banner
        if result.get("is_adaptive"):
            st.info("🎯 **Adaptive Mode ON** — Questions are focused on your previous weak areas")
        else:
            st.info("📖 **First Session** — Generating fresh questions from selected sections")

        st.subheader(f"Answer {len(questions)} Questions")
        st.caption("Select one answer per question, then submit at the bottom.")
        st.divider()

        with st.form("answer_form"):
            answers = {}
            for i, q in enumerate(questions, 1):
                st.markdown(
                    f"**Q{i} [Section {q['section_id']}]:** {q['question_text']}"
                )
                options = [f"{k}: {v}" for k, v in q["options"].items()]
                choice = st.radio(
                    "Your answer:",
                    options,
                    key=f"q_{q['id']}",
                    index=None,
                    horizontal=True
                )
                if choice:
                    answers[q["id"]] = choice[0]
                st.divider()

            submitted = st.form_submit_button("✅ Submit Answers", use_container_width=True)

        if submitted:
            if len(answers) < len(questions):
                st.warning(
                    f"Please answer all questions before submitting. "
                    f"({len(answers)}/{len(questions)} answered)"
                )
            else:
                from app.core.scorer import score_session
                from app.db.database import save_answer, update_session_score

                scored = score_session(questions, answers)
                for r in scored["results"]:
                    save_answer(r["question_id"], r["user_answer"], r["is_correct"])
                update_session_score(
                    result["session_id"], scored["score"], scored["total"]
                )
                st.session_state["scored"] = scored
                st.session_state["submitted"] = True
                st.rerun()

    # Show results
    if st.session_state.get("submitted") and "result" in st.session_state:
        result = st.session_state["result"]
        scored = st.session_state.get("scored")

        if scored:
            st.divider()
            st.subheader("📊 Session Results")

            # Score metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Score", f"{scored['score']}/{scored['total']}")
            col2.metric("Percentage", f"{scored['score_percent']}%")
            col3.metric(
                "Adaptive Mode",
                "ON ✅" if result.get("is_adaptive") else "OFF"
            )

            # Score feedback message
            pct = scored["score_percent"]
            if pct == 100:
                st.success("🏆 Perfect score! Outstanding work!")
            elif pct >= 80:
                st.success("🎉 Great job! You're doing really well!")
            elif pct >= 60:
                st.warning("📈 Good effort! Review the wrong answers below.")
            else:
                st.error("📚 Keep studying! Focus on the explanations below.")

            st.divider()

            # Per question breakdown
            correct_count = 0
            wrong_count = 0
            for i, r in enumerate(scored["results"], 1):
                if r["is_correct"]:
                    correct_count += 1
                    st.success(
                        f"**Q{i}:** {r['question_text']}\n\n"
                        f"✓ Correct — **{r['correct_answer']}**"
                    )
                else:
                    wrong_count += 1
                    st.error(
                        f"**Q{i}:** {r['question_text']}\n\n"
                        f"✗ Your answer: **{r['user_answer']}** | "
                        f"Correct: **{r['correct_answer']}**\n\n"
                        f"💡 {r['explanation']}"
                    )

            st.divider()

            # Weak areas summary
            if wrong_count > 0:
                st.subheader("🎯 Your Weak Areas This Session")
                st.markdown(
                    "These topics will be prioritized in your **next session** "
                    "on these sections:"
                )
                for r in scored["results"]:
                    if not r["is_correct"]:
                        st.markdown(f"- {r['question_text']}")

            st.divider()

            # Start new session button at bottom of results
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Start New Session", use_container_width=True):
                    for key in ["result", "submitted", "scored"]:
                        st.session_state.pop(key, None)
                    st.rerun()
            with col2:
                if st.button("📊 View Full History", use_container_width=True):
                    st.session_state["nav"] = "📊 History"
                    st.rerun()

# ========== HISTORY PAGE ==========
elif page == "📊 History":
    st.title("📊 Session History")

    section_input = st.number_input(
        "Enter section ID to view history:",
        min_value=1, max_value=10, value=1
    )

    if st.button("Load History"):
        sessions = get_prior_sessions([section_input])
        if not sessions:
            st.info("No history found for this section.")
        else:
            st.success(f"Found {len(sessions)} session(s) for Section {section_input}")
            for s in sessions:
                score = s['score']
                total = s['total_questions']
                pct = round((score/total)*100) if total > 0 else 0
                with st.expander(
                    f"Session {s['id']} — {s['created_at']} — "
                    f"Score: {score}/{total} ({pct}%)"
                ):
                    st.json(s)

# ========== KB SNAPSHOT PAGE ==========
elif page == "🗄️ KB Snapshot":
    st.title("🗄️ Knowledge Base Snapshot")
    st.markdown("Last 5 sessions stored in the knowledge base.")

    snapshot = get_kb_snapshot()
    if not snapshot:
        st.info("No sessions in the knowledge base yet.")
    else:
        st.success(f"{len(snapshot)} session(s) found.")
        for s in snapshot:
            score = s['score']
            total = s['total_questions']
            pct = round((score/total)*100) if total > 0 else 0
            with st.expander(
                f"Session {s['id']} — Sections: {s['section_ids']} — "
                f"Score: {score}/{total} ({pct}%)"
            ):
                st.json(s)