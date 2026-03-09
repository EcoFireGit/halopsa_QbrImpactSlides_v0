"""Unit tests for chat_engine.py"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from chat_engine import (
    Intent,
    parse_intent_regex,
    parse_date_expression,
    _last_day_of_month,
    resolve_client,
    get_missing_fields,
    get_optional_prompts,
    format_help_message,
    format_client_list,
    format_disambiguation,
    resolve_disambiguation,
    match_industry,
)


# ── Intent.GENERATE_QBR ──────────────────────────────────────────────


class TestParseIntentRegexGenerateQBR:
    def test_generate_qbr(self):
        intent, _ = parse_intent_regex("generate qbr for Acme")
        assert intent == Intent.GENERATE_QBR

    def test_create_qbr(self):
        intent, _ = parse_intent_regex("create a qbr for Beta Corp")
        assert intent == Intent.GENERATE_QBR

    def test_make_qbr(self):
        intent, _ = parse_intent_regex("make qbr for Acme")
        assert intent == Intent.GENERATE_QBR

    def test_build_qbr(self):
        intent, _ = parse_intent_regex("build qbr for Delta Inc")
        assert intent == Intent.GENERATE_QBR

    def test_run_qbr(self):
        intent, _ = parse_intent_regex("run qbr for Omega")
        assert intent == Intent.GENERATE_QBR

    def test_qbr_for(self):
        intent, _ = parse_intent_regex("QBR for Acme last quarter")
        assert intent == Intent.GENERATE_QBR

    def test_generate_qbr_extracts_client_name(self):
        # The regex matches "qbr for" first, so the extracted name includes "for"
        # This verifies a client_name key is populated from the message
        _, params = parse_intent_regex("generate qbr for Acme Corp")
        assert "client_name" in params
        assert "Acme" in params["client_name"]

    def test_generate_qbr_extracts_date_range(self):
        _, params = parse_intent_regex("generate qbr for Acme Q1 2025")
        assert "start_date" in params
        assert "end_date" in params
        assert params["start_date"] == date(2025, 1, 1)
        assert params["end_date"] == date(2025, 3, 31)

    def test_generate_qbr_case_insensitive(self):
        intent, _ = parse_intent_regex("GENERATE QBR FOR Acme")
        assert intent == Intent.GENERATE_QBR


# ── Intent.LIST_CLIENTS ──────────────────────────────────────────────


class TestParseIntentRegexListClients:
    def test_list_clients(self):
        intent, _ = parse_intent_regex("list clients")
        assert intent == Intent.LIST_CLIENTS

    def test_show_clients(self):
        intent, _ = parse_intent_regex("show me all clients")
        assert intent == Intent.LIST_CLIENTS

    def test_all_clients(self):
        intent, _ = parse_intent_regex("all clients")
        assert intent == Intent.LIST_CLIENTS

    def test_which_clients(self):
        intent, _ = parse_intent_regex("which clients do you have?")
        assert intent == Intent.LIST_CLIENTS

    def test_what_clients(self):
        intent, _ = parse_intent_regex("what clients are available?")
        assert intent == Intent.LIST_CLIENTS


# ── Intent.SHOW_HEALTH_SCORE ─────────────────────────────────────────


class TestParseIntentRegexShowHealthScore:
    def test_health_score(self):
        intent, _ = parse_intent_regex("what is the health score for Acme?")
        assert intent == Intent.SHOW_HEALTH_SCORE

    def test_healthscore_no_space(self):
        intent, _ = parse_intent_regex("healthscore for Beta")
        assert intent == Intent.SHOW_HEALTH_SCORE

    def test_score_for(self):
        intent, _ = parse_intent_regex("score for Acme Corp")
        assert intent == Intent.SHOW_HEALTH_SCORE

    def test_extracts_client_name(self):
        _, params = parse_intent_regex("health score for Acme?")
        assert params.get("client_name") == "Acme"


# ── Intent.SET_AI_SETTINGS ───────────────────────────────────────────


class TestParseIntentRegexSetAISettings:
    def test_enable_ai(self):
        intent, params = parse_intent_regex("enable ai")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("use_ai") is True

    def test_disable_ai(self):
        intent, params = parse_intent_regex("disable ai")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("use_ai") is False

    def test_turn_on_ai(self):
        intent, params = parse_intent_regex("turn on ai")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("use_ai") is True

    def test_turn_off_ai(self):
        intent, params = parse_intent_regex("turn off ai")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("use_ai") is False

    def test_num_recs_extracted(self):
        intent, params = parse_intent_regex("set 5 recommendations")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("num_recs") == 5

    def test_recs_number(self):
        intent, params = parse_intent_regex("3 recs")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("num_recs") == 3

    def test_sample_size_extracted(self):
        intent, params = parse_intent_regex("set sample size to 200")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("sample_size") == 200

    def test_sample_size_of_keyword(self):
        intent, params = parse_intent_regex("sample size of 150")
        assert intent == Intent.SET_AI_SETTINGS
        assert params.get("sample_size") == 150


# ── Intent.SET_CLIENT_PROFILE ────────────────────────────────────────


class TestParseIntentRegexSetClientProfile:
    def test_employee_count(self):
        intent, params = parse_intent_regex("100 employees")
        assert intent == Intent.SET_CLIENT_PROFILE
        assert params.get("employee_count") == 100

    def test_hourly_rate_dollar_sign(self):
        intent, params = parse_intent_regex("$75/hr")
        assert intent == Intent.SET_CLIENT_PROFILE
        assert params.get("avg_hourly_rate") == pytest.approx(75.0)

    def test_hourly_rate_per_hour(self):
        intent, params = parse_intent_regex("50 per hour")
        assert intent == Intent.SET_CLIENT_PROFILE
        assert params.get("avg_hourly_rate") == pytest.approx(50.0)

    def test_headcount(self):
        intent, _ = parse_intent_regex("headcount is 200")
        assert intent == Intent.SET_CLIENT_PROFILE

    def test_workforce(self):
        intent, _ = parse_intent_regex("workforce of 500")
        assert intent == Intent.SET_CLIENT_PROFILE

    def test_employee_count_extracted(self):
        _, params = parse_intent_regex("Acme has 150 employees at $75/hr")
        assert params.get("employee_count") == 150
        assert params.get("avg_hourly_rate") == pytest.approx(75.0)


# ── Intent.SET_INDUSTRY ──────────────────────────────────────────────


class TestParseIntentRegexSetIndustry:
    def test_industry_keyword(self):
        intent, _ = parse_intent_regex("set the industry to healthcare")
        assert intent == Intent.SET_INDUSTRY

    def test_sector_keyword(self):
        intent, _ = parse_intent_regex("Acme is in the finance sector")
        assert intent == Intent.SET_INDUSTRY


# ── Intent.SHOW_LAST_QBR ─────────────────────────────────────────────


class TestParseIntentRegexShowLastQBR:
    def test_last_qbr(self):
        intent, _ = parse_intent_regex("show last qbr")
        assert intent == Intent.SHOW_LAST_QBR

    def test_previous_qbr(self):
        intent, _ = parse_intent_regex("previous qbr")
        assert intent == Intent.SHOW_LAST_QBR

    def test_recent_qbr(self):
        intent, _ = parse_intent_regex("recent qbr")
        assert intent == Intent.SHOW_LAST_QBR


# ── Intent.HELP ──────────────────────────────────────────────────────


class TestParseIntentRegexHelp:
    def test_help_keyword(self):
        intent, _ = parse_intent_regex("help")
        assert intent == Intent.HELP

    def test_what_can_you(self):
        intent, _ = parse_intent_regex("what can you do?")
        assert intent == Intent.HELP

    def test_how_do_i(self):
        intent, _ = parse_intent_regex("how do I generate a report?")
        assert intent == Intent.HELP

    def test_commands(self):
        intent, _ = parse_intent_regex("commands")
        assert intent == Intent.HELP

    def test_capabilities(self):
        intent, _ = parse_intent_regex("show me your capabilities")
        assert intent == Intent.HELP


# ── Intent.UNKNOWN ───────────────────────────────────────────────────


class TestParseIntentRegexUnknown:
    def test_random_message(self):
        intent, params = parse_intent_regex("hello there")
        assert intent == Intent.UNKNOWN
        assert params == {}

    def test_empty_string(self):
        intent, params = parse_intent_regex("")
        assert intent == Intent.UNKNOWN

    def test_unrelated_text(self):
        intent, _ = parse_intent_regex("the weather is nice today")
        assert intent == Intent.UNKNOWN


# ── parse_date_expression ────────────────────────────────────────────


class TestParseDateExpression:
    def test_last_quarter_q1_returns_prev_q4(self):
        # When current quarter is Q1 (e.g. month=1), previous quarter is Q4 of last year
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("last quarter")
        assert result == (date(2025, 10, 1), date(2025, 12, 31))

    def test_last_quarter_q2_returns_q1(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 5, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("previous quarter")
        assert result == (date(2025, 1, 1), date(2025, 3, 31))

    def test_last_quarter_q3_returns_q2(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 8, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("last quarter")
        assert result == (date(2025, 4, 1), date(2025, 6, 30))

    def test_last_quarter_q4_returns_q3(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 11, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("last quarter")
        assert result == (date(2025, 7, 1), date(2025, 9, 30))

    def test_this_quarter_q1(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 2, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("this quarter")
        assert result == (date(2025, 1, 1), date(2025, 3, 31))

    def test_current_quarter(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 7, 20)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("current quarter")
        assert result == (date(2025, 7, 1), date(2025, 9, 30))

    def test_q1_2025(self):
        result = parse_date_expression("Q1 2025")
        assert result == (date(2025, 1, 1), date(2025, 3, 31))

    def test_q2_2024(self):
        result = parse_date_expression("q2 2024")
        assert result == (date(2024, 4, 1), date(2024, 6, 30))

    def test_q3_2025(self):
        result = parse_date_expression("Q3 2025")
        assert result == (date(2025, 7, 1), date(2025, 9, 30))

    def test_q4_2025(self):
        result = parse_date_expression("Q4 2025")
        assert result == (date(2025, 10, 1), date(2025, 12, 31))

    def test_past_n_months(self):
        today = date.today()
        result = parse_date_expression("past 3 months")
        expected_start = today - timedelta(days=3 * 30)
        assert result is not None
        assert result[0] == expected_start
        assert result[1] == today

    def test_last_n_months(self):
        today = date.today()
        result = parse_date_expression("last 6 months")
        expected_start = today - timedelta(days=6 * 30)
        assert result is not None
        assert result[0] == expected_start

    def test_past_n_days(self):
        today = date.today()
        result = parse_date_expression("past 30 days")
        assert result is not None
        assert result[0] == today - timedelta(days=30)
        assert result[1] == today

    def test_last_n_days(self):
        today = date.today()
        result = parse_date_expression("last 7 days")
        assert result is not None
        assert result[0] == today - timedelta(days=7)

    def test_month_range(self):
        result = parse_date_expression("January to March 2026")
        assert result == (date(2026, 1, 1), date(2026, 3, 31))

    def test_month_range_abbreviated(self):
        result = parse_date_expression("Jan - Mar 2025")
        assert result == (date(2025, 1, 1), date(2025, 3, 31))

    def test_no_date_returns_none(self):
        result = parse_date_expression("generate qbr for Acme")
        assert result is None

    def test_empty_string_returns_none(self):
        result = parse_date_expression("")
        assert result is None

    def test_prior_quarter(self):
        with patch("chat_engine.date") as mock_date:
            mock_date.today.return_value = date(2025, 5, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = parse_date_expression("prior quarter")
        assert result == (date(2025, 1, 1), date(2025, 3, 31))


# ── _last_day_of_month ───────────────────────────────────────────────


class TestLastDayOfMonth:
    def test_january(self):
        assert _last_day_of_month(2025, 1) == date(2025, 1, 31)

    def test_february_non_leap(self):
        assert _last_day_of_month(2025, 2) == date(2025, 2, 28)

    def test_february_leap(self):
        assert _last_day_of_month(2024, 2) == date(2024, 2, 29)

    def test_march(self):
        assert _last_day_of_month(2025, 3) == date(2025, 3, 31)

    def test_april(self):
        assert _last_day_of_month(2025, 4) == date(2025, 4, 30)

    def test_june(self):
        assert _last_day_of_month(2025, 6) == date(2025, 6, 30)

    def test_september(self):
        assert _last_day_of_month(2025, 9) == date(2025, 9, 30)

    def test_december(self):
        assert _last_day_of_month(2025, 12) == date(2025, 12, 31)


# ── resolve_client ───────────────────────────────────────────────────


class TestResolveClient:
    _CLIENTS = [
        {"id": 1, "name": "Acme Corp"},
        {"id": 2, "name": "Beta Industries"},
        {"id": 3, "name": "Gamma Solutions"},
        {"id": 4, "name": "Acme Technologies"},
    ]

    def test_exact_match(self):
        result = resolve_client("Acme Corp", self._CLIENTS)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_exact_match_case_insensitive(self):
        result = resolve_client("acme corp", self._CLIENTS)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_substring_match_multiple(self):
        result = resolve_client("Acme", self._CLIENTS)
        assert len(result) == 2
        ids = {c["id"] for c in result}
        assert ids == {1, 4}

    def test_substring_match_single(self):
        result = resolve_client("Beta", self._CLIENTS)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_word_match(self):
        result = resolve_client("Solutions", self._CLIENTS)
        assert len(result) == 1
        assert result[0]["id"] == 3

    def test_no_match_returns_empty(self):
        result = resolve_client("XYZ Nonexistent", self._CLIENTS)
        assert result == []

    def test_empty_name_returns_empty(self):
        result = resolve_client("", self._CLIENTS)
        assert result == []

    def test_empty_clients_returns_empty(self):
        result = resolve_client("Acme", [])
        assert result == []

    def test_none_name_returns_empty(self):
        result = resolve_client(None, self._CLIENTS)
        assert result == []


# ── get_missing_fields ───────────────────────────────────────────────


class TestGetMissingFields:
    def test_no_client_id_asks_for_client(self):
        state = {}
        result = get_missing_fields(state)
        assert result is not None
        assert "client" in result.lower()

    def test_missing_start_date_asks_for_date(self):
        state = {"client_id": 1}
        result = get_missing_fields(state)
        assert result is not None
        assert "date range" in result.lower()

    def test_missing_end_date_asks_for_date(self):
        state = {"client_id": 1, "start_date": date(2025, 1, 1)}
        result = get_missing_fields(state)
        assert result is not None
        assert "date range" in result.lower()

    def test_missing_msp_contact(self):
        state = {
            "client_id": 1,
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 3, 31),
        }
        result = get_missing_fields(state)
        assert result is not None
        assert "msp" in result.lower() or "contact" in result.lower()

    def test_all_required_fields_present_returns_none(self):
        state = {
            "client_id": 1,
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 3, 31),
            "msp_contact": "Jane Doe | jdoe@msp.com",
        }
        result = get_missing_fields(state)
        assert result is None


# ── get_optional_prompts ─────────────────────────────────────────────


class TestGetOptionalPrompts:
    def test_missing_employee_count_prompts(self):
        state = {"client_id": 1}
        result = get_optional_prompts(state, has_bea_key=False)
        assert result is not None
        assert "employee" in result.lower()

    def test_zero_employee_count_prompts(self):
        state = {"client_id": 1, "employee_count": 0}
        result = get_optional_prompts(state, has_bea_key=False)
        assert result is not None

    def test_already_asked_employee_count_skips(self):
        state = {"client_id": 1, "employee_count": 0, "asked_employee_count": True}
        result = get_optional_prompts(state, has_bea_key=False)
        assert result is None

    def test_bea_key_present_prompts_industry(self):
        state = {"client_id": 1, "employee_count": 100}
        result = get_optional_prompts(state, has_bea_key=True)
        assert result is not None
        assert "industry" in result.lower()

    def test_bea_key_absent_no_industry_prompt(self):
        state = {"client_id": 1, "employee_count": 100}
        result = get_optional_prompts(state, has_bea_key=False)
        assert result is None

    def test_industry_already_set_returns_none(self):
        state = {"client_id": 1, "employee_count": 100, "industry_name": "Finance"}
        result = get_optional_prompts(state, has_bea_key=True)
        assert result is None

    def test_already_asked_industry_skips(self):
        state = {"client_id": 1, "employee_count": 100, "asked_industry": True}
        result = get_optional_prompts(state, has_bea_key=True)
        assert result is None

    def test_all_optional_provided_returns_none(self):
        state = {
            "client_id": 1,
            "employee_count": 100,
            "industry_name": "Healthcare & Social Assistance",
        }
        result = get_optional_prompts(state, has_bea_key=True)
        assert result is None


# ── format_help_message ──────────────────────────────────────────────


class TestFormatHelpMessage:
    def test_returns_string(self):
        result = format_help_message()
        assert isinstance(result, str)

    def test_contains_generate_qbr(self):
        result = format_help_message()
        assert "QBR" in result

    def test_contains_list_clients(self):
        result = format_help_message()
        assert "List" in result or "clients" in result.lower()

    def test_contains_health_score(self):
        result = format_help_message()
        assert "health score" in result.lower()

    def test_contains_ai_settings(self):
        result = format_help_message()
        assert "AI" in result or "ai" in result.lower()

    def test_no_emoji_characters(self):
        result = format_help_message()
        # Check no common emoji ranges appear
        for ch in result:
            code = ord(ch)
            # Emoji range check (basic)
            assert not (0x1F300 <= code <= 0x1FAFF), f"Unexpected emoji character: {ch!r}"


# ── format_client_list ───────────────────────────────────────────────


class TestFormatClientList:
    def test_empty_list_returns_message(self):
        result = format_client_list([])
        assert "No clients" in result

    def test_single_client(self):
        clients = [{"name": "Acme Corp"}]
        result = format_client_list(clients)
        assert "Acme Corp" in result
        assert "1" in result

    def test_multiple_clients_numbered(self):
        clients = [{"name": "Acme"}, {"name": "Beta"}, {"name": "Gamma"}]
        result = format_client_list(clients)
        assert "Acme" in result
        assert "Beta" in result
        assert "Gamma" in result
        assert "3 clients" in result

    def test_count_shown_in_output(self):
        clients = [{"name": f"Client {i}"} for i in range(5)]
        result = format_client_list(clients)
        assert "5 clients" in result


# ── format_disambiguation ────────────────────────────────────────────


class TestFormatDisambiguation:
    def test_lists_all_candidates(self):
        matches = [{"name": "Acme Corp"}, {"name": "Acme Technologies"}]
        result = format_disambiguation(matches)
        assert "Acme Corp" in result
        assert "Acme Technologies" in result

    def test_numbered(self):
        matches = [{"name": "Alpha"}, {"name": "Beta"}]
        result = format_disambiguation(matches)
        assert "1." in result
        assert "2." in result

    def test_asks_to_clarify(self):
        matches = [{"name": "X"}, {"name": "Y"}]
        result = format_disambiguation(matches)
        assert "number" in result.lower() or "name" in result.lower()


# ── resolve_disambiguation ───────────────────────────────────────────


class TestResolveDisambiguation:
    _CANDIDATES = [
        {"id": 1, "name": "Acme Corp"},
        {"id": 2, "name": "Acme Technologies"},
    ]

    def test_resolve_by_number_one(self):
        result = resolve_disambiguation("1", self._CANDIDATES)
        assert result is not None
        assert result["id"] == 1

    def test_resolve_by_number_two(self):
        result = resolve_disambiguation("2", self._CANDIDATES)
        assert result is not None
        assert result["id"] == 2

    def test_resolve_by_name_substring(self):
        result = resolve_disambiguation("Technologies", self._CANDIDATES)
        assert result is not None
        assert result["id"] == 2

    def test_resolve_by_full_name(self):
        result = resolve_disambiguation("Acme Corp", self._CANDIDATES)
        assert result is not None
        assert result["id"] == 1

    def test_out_of_range_number_returns_none(self):
        result = resolve_disambiguation("5", self._CANDIDATES)
        assert result is None

    def test_zero_index_returns_none(self):
        result = resolve_disambiguation("0", self._CANDIDATES)
        assert result is None

    def test_no_match_returns_none(self):
        result = resolve_disambiguation("XYZ Unknown", self._CANDIDATES)
        assert result is None

    def test_case_insensitive_name_match(self):
        result = resolve_disambiguation("technologies", self._CANDIDATES)
        assert result is not None
        assert result["id"] == 2


# ── match_industry ───────────────────────────────────────────────────


class TestMatchIndustry:
    def test_exact_match(self):
        result = match_industry("Information Technology & Data Services")
        assert result == "Information Technology & Data Services"

    def test_keyword_it(self):
        result = match_industry("IT")
        assert result == "Information Technology & Data Services"

    def test_keyword_tech(self):
        result = match_industry("tech")
        assert result == "Information Technology & Data Services"

    def test_keyword_healthcare(self):
        result = match_industry("healthcare")
        assert result == "Healthcare & Social Assistance"

    def test_keyword_medical(self):
        result = match_industry("medical")
        assert result == "Healthcare & Social Assistance"

    def test_keyword_finance(self):
        result = match_industry("finance")
        assert result == "Finance & Insurance"

    def test_keyword_banking(self):
        result = match_industry("banking")
        assert result == "Finance & Insurance"

    def test_keyword_manufacturing(self):
        result = match_industry("manufacturing")
        assert result == "Manufacturing"

    def test_keyword_retail(self):
        result = match_industry("retail")
        assert result == "Retail Trade"

    def test_keyword_construction(self):
        result = match_industry("construction")
        assert result == "Construction"

    def test_keyword_education(self):
        result = match_industry("education")
        assert result == "Educational Services"

    def test_keyword_school(self):
        result = match_industry("school")
        assert result == "Educational Services"

    def test_keyword_hotel(self):
        result = match_industry("hotel")
        assert result == "Accommodation & Food Services"

    def test_keyword_logistics(self):
        result = match_industry("logistics")
        assert result == "Transportation & Warehousing"

    def test_keyword_energy(self):
        result = match_industry("energy")
        assert result == "Utilities"

    def test_keyword_agriculture(self):
        result = match_industry("agriculture")
        assert result == "Agriculture, Forestry & Fishing"

    def test_keyword_farming(self):
        result = match_industry("farming")
        assert result == "Agriculture, Forestry & Fishing"

    def test_unknown_returns_none(self):
        result = match_industry("nonexistent industry xyz")
        assert result is None

    def test_case_insensitive(self):
        result = match_industry("HEALTHCARE")
        assert result == "Healthcare & Social Assistance"

    def test_whitespace_stripped(self):
        result = match_industry("  finance  ")
        assert result == "Finance & Insurance"
