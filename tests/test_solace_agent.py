import tempfile
from pathlib import Path

import src.database.database as database
from src.ai.solace_agent import (
    SUPPORTED_LANGUAGES,
    SolaceAgent,
)


# Temporary database used only for AI Assistant unit testing
TEST_DATABASE_FOLDER = (
    Path(tempfile.gettempdir())
    / "solace_agent_tests"
)

TEST_DATABASE_PATH = (
    TEST_DATABASE_FOLDER
    / "test_agent.db"
)


# Create a fresh test database before every test
def setup_function():
    TEST_DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()

    database.DATABASE_FOLDER = (
        TEST_DATABASE_FOLDER
    )

    database.DATABASE_PATH = (
        TEST_DATABASE_PATH
    )

    database.create_database()


# Delete the temporary database after every test
def teardown_function():
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()


# Helper function to create a test user
def create_test_user():
    database.create_user(
        "Assistant Test User",
        "assistantuser",
        "StrongPassword1!"
    )

    return database.authenticate_user(
        "assistantuser",
        "StrongPassword1!"
    )


# Helper function to create a sample saved check-in
def sample_check_in(score=60.0):
    return {
        "recording_type": "audio",
        "transcript":
            "I feel tired after a busy shift.",
        "text_score": 40.0,
        "audio_score": 50.0,
        "vision_score": None,
        "strain_score": 40.0,
        "wellbeing_score": score,
        "phrase": "Today feels mixed",
        "explanation":
            "Your signals suggest a moderate wellbeing range.",
        "recommendation":
            "Take a short break and rest after your shift.",
        "image_name": "wellbeing_mid.png",
        "blink_rate": None,
        "head_position": None,
        "speech_rate": 120.0,
        "disfluency_rate": 0.05,
        "lexical_variety": 0.72,
    }


# Test case 1: Check that the Assistant supports all four application languages
def test_supported_languages():
    assert SUPPORTED_LANGUAGES == {
        "English",
        "Malay",
        "Chinese",
        "Tamil",
    }


# Test case 2: Check that an unsupported starting language falls back to English
def test_invalid_starting_language():
    assistant = SolaceAgent(
        user_id=1,
        language_name="French"
    )

    assert assistant.language_name == "English"


# Test case 3: Check that valid conversation history is cleaned correctly
def test_clean_history():
    history = [
        {
            "role": "user",
            "content": "  Hello Solace  "
        },
        {
            "role": "system",
            "content": "Do not keep this"
        },
        {
            "role": "assistant",
            "content": "  Hello  "
        },
        "invalid entry",
    ]

    result = SolaceAgent.clean_history(
        history
    )

    assert result == [
        {
            "role": "user",
            "content": "Hello Solace"
        },
        {
            "role": "assistant",
            "content": "Hello"
        },
    ]


# Test case 4: Check that only the latest eight history entries are kept
def test_history_limit():
    history = [
        {
            "role": "user",
            "content": f"Message {number}"
        }
        for number in range(10)
    ]

    result = SolaceAgent.clean_history(
        history
    )

    assert len(result) == 8
    assert result[0]["content"] == "Message 2"
    assert result[-1]["content"] == "Message 9"


# Test case 5: Check that a valid tool decision is parsed correctly
def test_parse_valid_tool_decision():
    result = SolaceAgent.parse_decision(
        '{"tool": "recent_scores", "date": ""}'
    )

    assert result == {
        "tool": "recent_scores",
        "date": "",
    }


# Test case 6: Check that an unknown tool falls back to Solace help
def test_parse_unknown_tool():
    result = SolaceAgent.parse_decision(
        '{"tool": "delete_data", "date": ""}'
    )

    assert result == {
        "tool": "solace_help",
        "date": "",
    }


# Test case 7: Check that an invalid date format is removed
def test_parse_invalid_date():
    result = SolaceAgent.parse_decision(
        '{"tool": "date_check_in", '
        '"date": "10/08/2026"}'
    )

    assert result == {
        "tool": "date_check_in",
        "date": "",
    }


# Test case 8: Check that the safety tool returns controlled crisis guidance
def test_safety_support():
    result = SolaceAgent.safety_support()

    assert result["status"] == "safety"
    assert (
        "immediate danger"
        in result["message"]
    )
    assert (
        "qualified healthcare professional"
        in result["message"]
    )


# Test case 9: Check that general conversation does not use personal wellbeing data
def test_general_tool():
    assistant = SolaceAgent()

    result = assistant.run_tool(
        {
            "tool": "general",
            "date": ""
        }
    )

    assert result["status"] == "ok"
    assert (
        "No personal data"
        in result["message"]
    )


# Test case 10: Check that personal wellbeing tools require a logged-in user
def test_personal_tool_requires_user():
    assistant = SolaceAgent()

    result = assistant.run_tool(
        {
            "tool": "latest_check_in",
            "date": ""
        }
    )

    assert result["status"] == "no_user"


# Test case 11: Check that the latest saved check-in can be read by the Assistant
def test_latest_check_in():
    user = create_test_user()

    database.save_check_in(
        user["id"],
        sample_check_in(62.0)
    )

    assistant = SolaceAgent(
        user_id=user["id"]
    )

    result = assistant.latest_check_in()

    assert result["status"] == "ok"
    assert result["check_in"][
        "wellbeing_score"
    ] == 62.0


# Test case 12: Check that recent wellbeing scores are returned correctly
def test_recent_scores():
    user = create_test_user()

    database.save_check_in(
        user["id"],
        sample_check_in(50.0)
    )

    database.save_check_in(
        user["id"],
        sample_check_in(60.0)
    )

    database.save_check_in(
        user["id"],
        sample_check_in(70.0)
    )

    assistant = SolaceAgent(
        user_id=user["id"]
    )

    result = assistant.recent_scores()

    assert result["status"] == "ok"
    assert result["latest_score"] == 70.0
    assert result["previous_score"] == 60.0

    assert result[
        "scores_chronological"
    ] == [
        50.0,
        60.0,
        70.0,
    ]


# Test case 13: Check that the Assistant returns the correct number of check-ins
def test_agent_check_in_count():
    user = create_test_user()

    database.save_check_in(
        user["id"],
        sample_check_in(55.0)
    )

    database.save_check_in(
        user["id"],
        sample_check_in(65.0)
    )

    assistant = SolaceAgent(
        user_id=user["id"]
    )

    result = assistant.check_in_count()

    assert result["status"] == "ok"
    assert result["count"] == 2


# Test case 14: Check that wellbeing context combines latest and recent information
def test_wellbeing_context():
    user = create_test_user()

    database.save_check_in(
        user["id"],
        sample_check_in(58.0)
    )

    assistant = SolaceAgent(
        user_id=user["id"]
    )

    result = assistant.wellbeing_context()

    assert result[
        "latest_check_in"
    ]["status"] == "ok"

    assert result[
        "recent_scores"
    ]["status"] == "ok"


# Test case 15: Check that a blank question is rejected without loading the AI model
def test_blank_question():
    assistant = SolaceAgent()

    result = assistant.answer(
        "   "
    )

    assert result == {
        "answer": (
            "Please enter a question for "
            "the Solace Assistant."
        ),
        "tool": "none",
    }