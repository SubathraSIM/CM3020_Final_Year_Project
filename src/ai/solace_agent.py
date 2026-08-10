import gc
import json
import re
from datetime import date

import torch
from transformers import pipeline as hf_pipeline

from src.database.database import (
    get_check_in_count,
    get_check_in_for_date,
    get_month_check_ins,
    get_recent_scores,
)
from src.ui.translations import translate_text


AGENT_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

SUPPORTED_LANGUAGES = {
    "English",
    "Malay",
    "Chinese",
    "Tamil",
}

TOOL_NAMES = {
    "solace_help",
    "latest_check_in",
    "recent_scores",
    "wellbeing_context",
    "recent_history",
    "date_check_in",
    "check_in_count",
    "safety_support",
    "general",
}


# --------------------------------------------------
# Solace knowledge used by the help tool
# --------------------------------------------------

SOLACE_HELP = """
Solace is an experimental multimodal wellbeing support application designed
for healthcare workers. It is not a medical diagnostic service.

Check-ins:
- A user can complete an audio or video check-in.
- Whisper creates the speech transcript.
- RoBERTa analyses emotion in the English working transcript.
- MERaLiON analyses emotion in the voice.
- ViT analyses facial-expression emotion when video is used.
- Five supporting signals are available: blink rate, head position,
  speech rate, disfluency and lexical variety.
- The model scores and supporting signals are fused into a wellbeing score
  from 0 to 100. A higher score represents a higher estimated wellbeing range.
- Scores of 67 or above are shown as the higher range, 34 to 66 as the
  moderate range, and below 34 as the lower range.
- Qwen generates supportive recommendations after a check-in.
- NLLB translates recommendations and interface text when Malay, Chinese
  or Tamil is selected.

Pages:
- Home provides access to the main Solace features.
- Check-in is used to record or upload audio/video and run the analysis.
- Trends displays saved wellbeing history and saved supporting signals.
- Assistant explains Solace and can read the logged-in user's saved
  wellbeing information through restricted read-only tools.
- Settings allows the application language to be changed.

Languages:
- Solace supports English, Malay, Chinese and Tamil.
- The selected language is used across the interface and for future check-ins.

Privacy and safety:
- Account details and saved check-ins are stored locally on the device.
- The Assistant is read-only and cannot change or delete wellbeing data.
- Solace does not diagnose burnout, depression, anxiety or other conditions.
- AI outputs can be inaccurate and should not replace advice from a
  qualified healthcare professional.
""".strip()


# --------------------------------------------------
# Agent tool-selection instructions
# --------------------------------------------------

ROUTER_SYSTEM = """
You are the tool-selection component of the Solace Assistant.

Your only job is to choose the single best read-only tool for the
user's question.

Available tools:

solace_help
Use for questions about what Solace is, how it works, pages, models,
signals, scores, privacy, languages, settings, check-ins or limitations.

latest_check_in
Use when the user asks specifically about their latest or most recent
saved check-in and does not need a broader comparison.

recent_scores
Use when the user asks for recent scores, the previous score, whether
scores increased or decreased, or a simple numerical comparison.

wellbeing_context
Use when the user asks why a score changed, what may have contributed
to a recent result, or asks for a broader explanation requiring both
the latest check-in details and recent scores.

recent_history
Use when the user asks for several recent dated check-ins or a recent
history overview.

date_check_in
Use when the user asks about a check-in on a specific date.
Return the date as YYYY-MM-DD.

check_in_count
Use when the user asks how many check-ins they have completed.

safety_support
Use when the user describes possible immediate danger, self-harm,
suicidal intent, or an urgent medical or mental-health crisis.

general
Use only for greetings, thanks, or general conversation that does not
require Solace documentation or saved user data.

Rules:
- Choose exactly one tool.
- Never invent another tool.
- Personal wellbeing questions must use a personal-data tool.
- Medical diagnosis questions should use solace_help unless there is
  immediate danger, in which case use safety_support.
- If a specific date is mentioned, resolve it using the current date
  when possible and use date_check_in.
- Return JSON only with exactly these keys:
  {"tool": "tool_name", "date": "YYYY-MM-DD or empty string"}
""".strip()


# --------------------------------------------------
# Final response instructions
# --------------------------------------------------

ANSWER_SYSTEM = """
You are the Solace wellbeing support assistant.

Use only the supplied Solace tool result when stating facts about the
logged-in user's saved wellbeing data.

Never invent a score, signal, check-in, date, transcript or trend.

You may explain Solace using the supplied application information.

Safety boundaries:
- Do not diagnose burnout, depression, anxiety or any medical or
  mental-health condition.
- Do not claim that a Solace score proves a condition.
- Do not provide medication or treatment instructions.
- Explain that Solace is an experimental wellbeing support tool when
  medical certainty is requested.
- If information is unavailable, say that it is unavailable.
- Do not claim that you changed, deleted or sent any user data.
- Keep the response supportive, concise and clear.
- Answer in English. Another model will translate the final response
  when the user has selected another language.
""".strip()


# --------------------------------------------------
# Solace Agent
# --------------------------------------------------

class SolaceAgent:
    def __init__(
        self,
        user_id=None,
        language_name="English",
    ):
        self.user_id = user_id

        self.language_name = (
            language_name
            if language_name in SUPPORTED_LANGUAGES
            else "English"
        )

        self.qwen = None
        self.last_tool = None

    # --------------------------------------------------
    # User and language
    # --------------------------------------------------

    def set_user(self, user_id):
        self.user_id = user_id

    def set_language(self, language_name):
        if language_name in SUPPORTED_LANGUAGES:
            self.language_name = language_name

    # --------------------------------------------------
    # Qwen
    # --------------------------------------------------

    def load_qwen(self):
        if self.qwen is None:
            self.qwen = hf_pipeline(
                "text-generation",
                model=AGENT_MODEL_ID,
                device_map="auto",
                dtype="auto",
            )

        return self.qwen

    def release_qwen(self):
        self.qwen = None

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # --------------------------------------------------
    # Short conversation memory
    # --------------------------------------------------

    @staticmethod
    def clean_history(history):
        if not history:
            return []

        cleaned = []

        for item in history[-8:]:
            if not isinstance(item, dict):
                continue

            role = item.get("role")

            content = str(
                item.get("content", "")
            ).strip()

            if (
                role not in {
                    "user",
                    "assistant",
                }
                or not content
            ):
                continue

            cleaned.append(
                {
                    "role": role,
                    "content": content[:1000],
                }
            )

        return cleaned

    # --------------------------------------------------
    # Read Qwen response
    # --------------------------------------------------

    @staticmethod
    def generated_content(result):
        generated = result[0][
            "generated_text"
        ]

        if isinstance(generated, list):
            return str(
                generated[-1].get(
                    "content",
                    "",
                )
            ).strip()

        return str(generated).strip()

    # --------------------------------------------------
    # Parse tool decision
    # --------------------------------------------------

    @staticmethod
    def parse_decision(text):
        match = re.search(
            r"\{.*?\}",
            text,
            flags=re.DOTALL,
        )

        if not match:
            return {
                "tool": "solace_help",
                "date": "",
            }

        try:
            decision = json.loads(
                match.group(0)
            )

        except json.JSONDecodeError:
            return {
                "tool": "solace_help",
                "date": "",
            }

        tool = decision.get(
            "tool",
            "",
        )

        date_text = str(
            decision.get(
                "date",
                "",
            )
        ).strip()

        if tool not in TOOL_NAMES:
            tool = "solace_help"

        if (
            tool == "date_check_in"
            and not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                date_text,
            )
        ):
            date_text = ""

        return {
            "tool": tool,
            "date": date_text,
        }

    # --------------------------------------------------
    # Agent chooses a tool
    # --------------------------------------------------

    def choose_tool(
        self,
        question,
        history=None,
    ):
        generator = self.load_qwen()

        conversation = self.clean_history(
            history
        )

        context = "\n".join(
            (
                f"{item['role']}: "
                f"{item['content']}"
            )
            for item in conversation[-4:]
        )

        messages = [
            {
                "role": "system",
                "content": ROUTER_SYSTEM,
            },
            {
                "role": "user",
                "content": (
                    f"Current date: "
                    f"{date.today().isoformat()}\n"

                    f"Selected application language: "
                    f"{self.language_name}\n\n"

                    f"Recent conversation:\n"
                    f"{context or 'None'}\n\n"

                    f"Current user question:\n"
                    f"{question}\n\n"

                    "Return the tool-selection "
                    "JSON only."
                ),
            },
        ]

        result = generator(
            messages,
            max_new_tokens=80,
            do_sample=False,
            pad_token_id=(
                generator
                .tokenizer
                .eos_token_id
            ),
        )

        return self.parse_decision(
            self.generated_content(
                result
            )
        )

    # --------------------------------------------------
    # Tool 1 - latest check-in
    # --------------------------------------------------

    def latest_check_in(self):
        history = get_month_check_ins(
            self.user_id,
            31,
        )

        if not history:
            return {
                "status": "no_data",
                "message": (
                    "No saved check-ins "
                    "are available."
                ),
            }

        latest_date = history[-1][
            "date"
        ]

        check_in = get_check_in_for_date(
            self.user_id,
            latest_date,
        )

        if check_in is None:
            return {
                "status": "no_data",
                "message": (
                    "No saved check-in "
                    "could be retrieved."
                ),
            }

        return {
            "status": "ok",
            "date": latest_date,
            "check_in": check_in,
        }

    # --------------------------------------------------
    # Tool 2 - recent scores
    # --------------------------------------------------

    def recent_scores(self):
        scores = get_recent_scores(
            self.user_id,
            7,
        )

        if not scores:
            return {
                "status": "no_data",
                "message": (
                    "No saved wellbeing "
                    "scores are available."
                ),
            }

        return {
            "status": "ok",

            "scores_chronological": [
                round(
                    score,
                    2,
                )
                for score in scores
            ],

            "latest_score": round(
                scores[-1],
                2,
            ),

            "previous_score": (
                round(
                    scores[-2],
                    2,
                )
                if len(scores) >= 2
                else None
            ),
        }

    # --------------------------------------------------
    # Tool 3 - combined wellbeing context
    # --------------------------------------------------

    def wellbeing_context(self):
        latest = self.latest_check_in()

        scores = self.recent_scores()

        return {
            "latest_check_in": latest,
            "recent_scores": scores,
        }

    # --------------------------------------------------
    # Tool 4 - recent history
    # --------------------------------------------------

    def recent_history(self):
        history = get_month_check_ins(
            self.user_id,
            10,
        )

        if not history:
            return {
                "status": "no_data",
                "message": (
                    "No saved check-in "
                    "history is available."
                ),
            }

        return {
            "status": "ok",
            "check_ins": history,
        }

    # --------------------------------------------------
    # Tool 5 - specific date
    # --------------------------------------------------

    def date_check_in(
        self,
        date_text,
    ):
        if not date_text:
            return {
                "status": "missing_date",
                "message": (
                    "A specific check-in date "
                    "was not identified."
                ),
            }

        check_in = get_check_in_for_date(
            self.user_id,
            date_text,
        )

        if check_in is None:
            return {
                "status": "no_data",
                "date": date_text,
                "message": (
                    "No saved check-in is "
                    "available for this date."
                ),
            }

        return {
            "status": "ok",
            "date": date_text,
            "check_in": check_in,
        }

    # --------------------------------------------------
    # Tool 6 - check-in count
    # --------------------------------------------------

    def check_in_count(self):
        return {
            "status": "ok",
            "count": get_check_in_count(
                self.user_id
            ),
        }

    # --------------------------------------------------
    # Tool 7 - safety support
    # --------------------------------------------------

    @staticmethod
    def safety_support():
        return {
            "status": "safety",

            "message": (
                "Solace cannot provide emergency "
                "or crisis care. "

                "If you may be in immediate danger "
                "or may harm yourself or someone "
                "else, contact local emergency "
                "services or a trusted person who "
                "can stay with you. "

                "For urgent mental-health concerns, "
                "seek help from a qualified "
                "healthcare professional."
            ),
        }

    # --------------------------------------------------
    # Run selected tool
    # --------------------------------------------------

    def run_tool(
        self,
        decision,
    ):
        tool = decision["tool"]

        if tool == "solace_help":
            return {
                "status": "ok",
                "information": SOLACE_HELP,
            }

        if tool == "safety_support":
            return self.safety_support()

        if tool == "general":
            return {
                "status": "ok",
                "message": (
                    "No personal data or Solace "
                    "help data was required."
                ),
            }

        # Personal tools require a logged-in user.
        if self.user_id is None:
            return {
                "status": "no_user",
                "message": (
                    "Personal wellbeing information "
                    "is only available for a "
                    "logged-in user."
                ),
            }

        if tool == "latest_check_in":
            return self.latest_check_in()

        if tool == "recent_scores":
            return self.recent_scores()

        if tool == "wellbeing_context":
            return self.wellbeing_context()

        if tool == "recent_history":
            return self.recent_history()

        if tool == "date_check_in":
            return self.date_check_in(
                decision["date"]
            )

        if tool == "check_in_count":
            return self.check_in_count()

        return {
            "status": "unsupported",
            "message": (
                "The requested Solace tool "
                "is not available."
            ),
        }

    # --------------------------------------------------
    # Qwen creates final answer
    # --------------------------------------------------

    def generate_answer(
        self,
        question,
        tool_name,
        tool_result,
        history=None,
    ):
        generator = self.load_qwen()

        conversation = self.clean_history(
            history
        )

        tool_text = json.dumps(
            tool_result,
            ensure_ascii=False,
        )

        messages = [
            {
                "role": "system",
                "content": ANSWER_SYSTEM,
            },
        ]

        messages.extend(
            conversation
        )

        messages.append(
            {
                "role": "user",
                "content": (
                    f"User question:\n"
                    f"{question}\n\n"

                    f"Tool selected: "
                    f"{tool_name}\n\n"

                    f"Tool result:\n"
                    f"{tool_text}\n\n"

                    "Answer the user's question "
                    "using the tool result and "
                    "the safety rules."
                ),
            }
        )

        result = generator(
            messages,
            max_new_tokens=220,
            do_sample=False,
            pad_token_id=(
                generator
                .tokenizer
                .eos_token_id
            ),
        )

        return self.generated_content(
            result
        )

    # --------------------------------------------------
    # Complete agent workflow
    # --------------------------------------------------

    def answer(
        self,
        question,
        history=None,
    ):
        question = str(
            question
        ).strip()

        if not question:
            return {
                "answer": (
                    "Please enter a question for "
                    "the Solace Assistant."
                ),
                "tool": "none",
            }

        try:
            # Step 1:
            # Qwen decides which tool it needs.
            decision = self.choose_tool(
                question,
                history,
            )

            self.last_tool = decision[
                "tool"
            ]

            # Step 2:
            # The selected read-only tool runs.
            tool_result = self.run_tool(
                decision
            )

            # Step 3:
            # Safety responses remain controlled.
            if (
                decision["tool"]
                == "safety_support"
            ):
                english_answer = (
                    tool_result[
                        "message"
                    ]
                )

            else:
                # Step 4:
                # Qwen answers using the
                # information returned by the tool.
                english_answer = (
                    self.generate_answer(
                        question,
                        decision["tool"],
                        tool_result,
                        history,
                    )
                )

            # Release Qwen before NLLB is loaded.
            self.release_qwen()

            # Step 5:
            # English remains unchanged.
            # Other supported languages use NLLB.
            final_answer = translate_text(
                english_answer,
                self.language_name,
            )

            return {
                "answer": final_answer,
                "tool": decision["tool"],
            }

        except Exception:
            self.release_qwen()
            raise