"""Unit tests for slack_schema.py and populate_slack_data.py"""

import json
import os
import uuid
from unittest.mock import patch

import pytest

import slack_schema
import populate_slack_data
from slack_schema import SlackMessage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_slack_data(tmp_path):
    """Redirect _SLACK_DATA_PATH to a temp file for every test."""
    tmp_file = str(tmp_path / "slack_data.json")
    with patch.object(slack_schema, "_SLACK_DATA_PATH", tmp_file):
        yield tmp_file


@pytest.fixture()
def sample_message():
    return SlackMessage(
        message_id="test-id-001",
        client_id=42,
        client_name="Acme Corporation",
        channel="support-alerts",
        sender_id="U0CLI001",
        sender_name="Acme IT Lead",
        sender_type="client_user",
        message_text="Our email server is down.",
        timestamp="2025-01-15T10:30:00Z",
        sentiment="negative",
        ticket_reference=12345,
        tags=["email", "outage"],
    )


@pytest.fixture()
def msp_message():
    return SlackMessage(
        message_id="test-id-002",
        client_id=42,
        client_name="Acme Corporation",
        channel="support-alerts",
        sender_id="U0MSP001",
        sender_name="Alex Rivera",
        sender_type="msp_agent",
        message_text="Ticket #12345 resolved: Email server restored.",
        timestamp="2025-01-15T11:00:00Z",
        sentiment="positive",
        ticket_reference=12345,
        tags=["email", "resolved"],
    )


# ---------------------------------------------------------------------------
# SlackMessage dataclass
# ---------------------------------------------------------------------------


class TestSlackMessageDataclass:
    def test_defaults_assigned(self):
        msg = SlackMessage(
            client_id=1,
            client_name="Test Co",
            channel="general",
            sender_id="U001",
            sender_name="Alice",
            sender_type="msp_agent",
            message_text="Hello",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert msg.is_reply is False
        assert msg.sentiment == "neutral"
        assert msg.ticket_reference is None
        assert msg.tags == []
        assert msg.thread_ts is None
        assert len(msg.message_id) == 36  # UUID4 format

    def test_message_id_unique_per_instance(self):
        m1 = SlackMessage(1, "Co", "general", "U1", "Alice", "msp_agent", "Hi", "2025-01-01T00:00:00Z")
        m2 = SlackMessage(1, "Co", "general", "U2", "Bob", "msp_agent", "Hi", "2025-01-01T00:00:00Z")
        assert m1.message_id != m2.message_id

    def test_to_dict_round_trip(self, sample_message):
        d = sample_message.to_dict()
        assert d["client_id"] == 42
        assert d["channel"] == "support-alerts"
        assert d["tags"] == ["email", "outage"]
        assert d["ticket_reference"] == 12345

    def test_from_dict_round_trip(self, sample_message):
        d = sample_message.to_dict()
        restored = SlackMessage.from_dict(d)
        assert restored.message_id == sample_message.message_id
        assert restored.client_id == sample_message.client_id
        assert restored.sentiment == sample_message.sentiment
        assert restored.tags == sample_message.tags

    def test_from_dict_generates_id_if_missing(self):
        d = {
            "client_id": 1,
            "client_name": "Co",
            "channel": "general",
            "sender_id": "U1",
            "sender_name": "Alice",
            "sender_type": "msp_agent",
            "message_text": "Hi",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        msg = SlackMessage.from_dict(d)
        assert len(msg.message_id) == 36


# ---------------------------------------------------------------------------
# Persistence: load_slack_data / save_slack_data
# ---------------------------------------------------------------------------


class TestLoadSlackData:
    def test_missing_file_returns_empty_list(self):
        result = slack_schema.load_slack_data()
        assert result == []

    def test_loads_valid_messages(self, sample_message):
        slack_schema.save_slack_data([sample_message])
        loaded = slack_schema.load_slack_data()
        assert len(loaded) == 1
        assert loaded[0].message_id == sample_message.message_id

    def test_corrupt_json_returns_empty_list(self, isolated_slack_data):
        with open(isolated_slack_data, "w") as f:
            f.write("not valid json {{{")
        result = slack_schema.load_slack_data()
        assert result == []

    def test_missing_messages_key_returns_empty_list(self, isolated_slack_data):
        with open(isolated_slack_data, "w") as f:
            json.dump({}, f)
        result = slack_schema.load_slack_data()
        assert result == []


class TestSaveSlackData:
    def test_writes_multiple_messages(self, sample_message, msp_message):
        slack_schema.save_slack_data([sample_message, msp_message])
        loaded = slack_schema.load_slack_data()
        assert len(loaded) == 2

    def test_overwrites_existing_data(self, sample_message, msp_message):
        slack_schema.save_slack_data([sample_message])
        slack_schema.save_slack_data([msp_message])
        loaded = slack_schema.load_slack_data()
        assert len(loaded) == 1
        assert loaded[0].message_id == msp_message.message_id

    def test_empty_list_clears_all(self, sample_message):
        slack_schema.save_slack_data([sample_message])
        slack_schema.save_slack_data([])
        assert slack_schema.load_slack_data() == []


# ---------------------------------------------------------------------------
# CRUD: add_message
# ---------------------------------------------------------------------------


class TestAddMessage:
    def test_adds_new_message(self, sample_message):
        slack_schema.add_message(sample_message)
        result = slack_schema.load_slack_data()
        assert len(result) == 1
        assert result[0].message_id == sample_message.message_id

    def test_raises_on_duplicate_id(self, sample_message):
        slack_schema.add_message(sample_message)
        with pytest.raises(ValueError, match="already exists"):
            slack_schema.add_message(sample_message)

    def test_adds_multiple_distinct_messages(self, sample_message, msp_message):
        slack_schema.add_message(sample_message)
        slack_schema.add_message(msp_message)
        assert len(slack_schema.load_slack_data()) == 2


# ---------------------------------------------------------------------------
# CRUD: upsert_message
# ---------------------------------------------------------------------------


class TestUpsertMessage:
    def test_inserts_new_message(self, sample_message):
        slack_schema.upsert_message(sample_message)
        assert len(slack_schema.load_slack_data()) == 1

    def test_replaces_existing_message(self, sample_message):
        slack_schema.upsert_message(sample_message)
        updated = SlackMessage.from_dict({
            **sample_message.to_dict(),
            "message_text": "Updated text",
            "sentiment": "positive",
        })
        slack_schema.upsert_message(updated)
        loaded = slack_schema.load_slack_data()
        assert len(loaded) == 1
        assert loaded[0].message_text == "Updated text"
        assert loaded[0].sentiment == "positive"

    def test_preserves_other_messages(self, sample_message, msp_message):
        slack_schema.upsert_message(sample_message)
        slack_schema.upsert_message(msp_message)
        updated = SlackMessage.from_dict({**sample_message.to_dict(), "sentiment": "neutral"})
        slack_schema.upsert_message(updated)
        loaded = slack_schema.load_slack_data()
        assert len(loaded) == 2


# ---------------------------------------------------------------------------
# CRUD: get_message_by_id
# ---------------------------------------------------------------------------


class TestGetMessageById:
    def test_returns_correct_message(self, sample_message):
        slack_schema.add_message(sample_message)
        result = slack_schema.get_message_by_id(sample_message.message_id)
        assert result is not None
        assert result.message_id == sample_message.message_id

    def test_returns_none_for_unknown_id(self):
        result = slack_schema.get_message_by_id("nonexistent-id")
        assert result is None


# ---------------------------------------------------------------------------
# CRUD: get_messages_for_client
# ---------------------------------------------------------------------------


class TestGetMessagesForClient:
    def test_returns_messages_for_client(self, sample_message, msp_message):
        other = SlackMessage(
            client_id=99,
            client_name="Other Co",
            channel="general",
            sender_id="U999",
            sender_name="Other",
            sender_type="client_user",
            message_text="Hi",
            timestamp="2025-01-01T00:00:00Z",
        )
        slack_schema.save_slack_data([sample_message, msp_message, other])
        result = slack_schema.get_messages_for_client(42)
        assert len(result) == 2
        assert all(m.client_id == 42 for m in result)

    def test_returns_empty_for_unknown_client(self, sample_message):
        slack_schema.add_message(sample_message)
        result = slack_schema.get_messages_for_client(999)
        assert result == []


# ---------------------------------------------------------------------------
# CRUD: get_messages_by_channel
# ---------------------------------------------------------------------------


class TestGetMessagesByChannel:
    def test_returns_matching_channel(self, sample_message, msp_message):
        other = SlackMessage(
            client_id=1,
            client_name="Co",
            channel="general",
            sender_id="U1",
            sender_name="A",
            sender_type="msp_agent",
            message_text="Hi",
            timestamp="2025-01-01T00:00:00Z",
        )
        slack_schema.save_slack_data([sample_message, msp_message, other])
        result = slack_schema.get_messages_by_channel("support-alerts")
        assert len(result) == 2

    def test_case_insensitive_match(self, sample_message):
        slack_schema.add_message(sample_message)
        result = slack_schema.get_messages_by_channel("SUPPORT-ALERTS")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# CRUD: get_messages_by_sentiment
# ---------------------------------------------------------------------------


class TestGetMessagesBySentiment:
    def test_filters_by_sentiment(self, sample_message, msp_message):
        # sample_message = negative, msp_message = positive
        slack_schema.save_slack_data([sample_message, msp_message])
        neg = slack_schema.get_messages_by_sentiment("negative")
        pos = slack_schema.get_messages_by_sentiment("positive")
        assert len(neg) == 1
        assert len(pos) == 1
        assert neg[0].message_id == sample_message.message_id

    def test_returns_empty_for_unmatched_sentiment(self, sample_message):
        slack_schema.add_message(sample_message)
        result = slack_schema.get_messages_by_sentiment("positive")
        assert result == []


# ---------------------------------------------------------------------------
# CRUD: delete_message
# ---------------------------------------------------------------------------


class TestDeleteMessage:
    def test_deletes_existing_message(self, sample_message):
        slack_schema.add_message(sample_message)
        deleted = slack_schema.delete_message(sample_message.message_id)
        assert deleted is True
        assert slack_schema.load_slack_data() == []

    def test_returns_false_for_nonexistent(self):
        result = slack_schema.delete_message("fake-id")
        assert result is False

    def test_preserves_other_messages(self, sample_message, msp_message):
        slack_schema.save_slack_data([sample_message, msp_message])
        slack_schema.delete_message(sample_message.message_id)
        remaining = slack_schema.load_slack_data()
        assert len(remaining) == 1
        assert remaining[0].message_id == msp_message.message_id


# ---------------------------------------------------------------------------
# CRUD: delete_messages_for_client
# ---------------------------------------------------------------------------


class TestDeleteMessagesForClient:
    def test_deletes_all_client_messages(self, sample_message, msp_message):
        slack_schema.save_slack_data([sample_message, msp_message])
        count = slack_schema.delete_messages_for_client(42)
        assert count == 2
        assert slack_schema.load_slack_data() == []

    def test_returns_zero_for_unknown_client(self, sample_message):
        slack_schema.add_message(sample_message)
        count = slack_schema.delete_messages_for_client(999)
        assert count == 0
        assert len(slack_schema.load_slack_data()) == 1

    def test_preserves_other_client_messages(self, sample_message):
        other = SlackMessage(
            client_id=7,
            client_name="Other",
            channel="general",
            sender_id="U7",
            sender_name="User",
            sender_type="client_user",
            message_text="Hi",
            timestamp="2025-01-01T00:00:00Z",
        )
        slack_schema.save_slack_data([sample_message, other])
        slack_schema.delete_messages_for_client(42)
        remaining = slack_schema.load_slack_data()
        assert len(remaining) == 1
        assert remaining[0].client_id == 7


# ---------------------------------------------------------------------------
# populate_slack_data: generate_messages_for_client
# ---------------------------------------------------------------------------


class TestGenerateMessagesForClient:
    def test_generates_correct_count(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme Corp", rng, 10)
        assert len(msgs) == 10

    def test_all_messages_linked_to_client(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(5, "Globex", rng, 8)
        assert all(m.client_id == 5 for m in msgs)
        assert all(m.client_name == "Globex" for m in msgs)

    def test_messages_sorted_by_timestamp(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 15)
        timestamps = [m.timestamp for m in msgs]
        assert timestamps == sorted(timestamps)

    def test_sender_type_valid(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 20)
        assert all(m.sender_type in slack_schema.VALID_SENDER_TYPES for m in msgs)

    def test_sentiment_valid(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 20)
        assert all(m.sentiment in slack_schema.VALID_SENTIMENTS for m in msgs)

    def test_channels_from_valid_set(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 20)
        assert all(m.channel in populate_slack_data.CHANNELS for m in msgs)

    def test_ticket_reference_matches_text(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 50)
        for m in msgs:
            if m.ticket_reference is not None:
                assert str(m.ticket_reference) in m.message_text

    def test_no_template_placeholder_remaining(self):
        import random
        rng = random.Random(42)
        msgs = populate_slack_data.generate_messages_for_client(1, "Acme", rng, 50)
        for m in msgs:
            assert "{{TICKET}}" not in m.message_text


# ---------------------------------------------------------------------------
# populate_slack_data: populate()
# ---------------------------------------------------------------------------


class TestPopulate:
    @pytest.fixture(autouse=True)
    def patch_slack_path(self, isolated_slack_data):
        """Also patch the populate module's reference to the data file."""
        with patch.object(slack_schema, "_SLACK_DATA_PATH", isolated_slack_data):
            yield

    def test_populate_writes_messages(self):
        clients = [
            {"id": 1, "name": "Acme"},
            {"id": 2, "name": "Globex"},
        ]
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            result = populate_slack_data.populate(messages_per_client=5, seed=99)
        assert len(result) == 10  # 2 clients * 5 messages

    def test_populate_reset_clears_existing(self, sample_message):
        slack_schema.add_message(sample_message)
        clients = [{"id": 1, "name": "NewCo"}]
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            populate_slack_data.populate(reset=True, messages_per_client=3, seed=1)
        all_msgs = slack_schema.load_slack_data()
        # After reset, only newly generated messages for client 1 should exist
        assert all(m.client_id == 1 for m in all_msgs)
        assert len(all_msgs) == 3

    def test_populate_idempotent_with_reset(self):
        clients = [{"id": 10, "name": "Initech"}]
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            populate_slack_data.populate(reset=True, messages_per_client=4, seed=7)
            populate_slack_data.populate(reset=True, messages_per_client=4, seed=7)
        all_msgs = slack_schema.load_slack_data()
        assert len(all_msgs) == 4

    def test_populate_without_reset_replaces_client_data(self, sample_message):
        # sample_message is for client 42
        slack_schema.add_message(sample_message)
        clients = [{"id": 42, "name": "Acme Corporation"}]
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            populate_slack_data.populate(reset=False, messages_per_client=3, seed=5)
        all_msgs = slack_schema.load_slack_data()
        # Old message replaced; 3 new ones
        assert len(all_msgs) == 3

    def test_populate_uses_fallback_clients_when_no_profiles(self):
        with patch.object(populate_slack_data, "_CLIENT_PROFILES_PATH", "/nonexistent/path.json"):
            clients = populate_slack_data.get_clients(use_fallback_if_empty=True)
        assert len(clients) > 0
        assert clients == populate_slack_data._FALLBACK_CLIENTS

    def test_populate_reproducible_with_same_seed(self):
        clients = [{"id": 1, "name": "Acme"}]
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            r1 = populate_slack_data.populate(reset=True, messages_per_client=5, seed=42)
        slack_schema.save_slack_data([])
        with patch.object(populate_slack_data, "get_clients", return_value=clients):
            r2 = populate_slack_data.populate(reset=True, messages_per_client=5, seed=42)
        texts1 = [m.message_text for m in r1]
        texts2 = [m.message_text for m in r2]
        assert texts1 == texts2


# ---------------------------------------------------------------------------
# populate_slack_data: get_clients
# ---------------------------------------------------------------------------


class TestGetClients:
    def test_returns_fallback_when_no_profile_file(self, tmp_path):
        fake_path = str(tmp_path / "nonexistent.json")
        with patch.object(populate_slack_data, "_CLIENT_PROFILES_PATH", fake_path):
            clients = populate_slack_data.get_clients()
        assert clients == populate_slack_data._FALLBACK_CLIENTS

    def test_loads_from_profiles_when_available(self, tmp_path):
        profiles = {"1": {"employee_count": 50, "avg_hourly_rate": 60}, "2": {}}
        path = str(tmp_path / "client_profiles.json")
        with open(path, "w") as f:
            json.dump(profiles, f)
        with patch.object(populate_slack_data, "_CLIENT_PROFILES_PATH", path):
            clients = populate_slack_data.get_clients()
        ids = {c["id"] for c in clients}
        assert ids == {1, 2}

    def test_corrupt_profiles_returns_fallback(self, tmp_path):
        path = str(tmp_path / "client_profiles.json")
        with open(path, "w") as f:
            f.write("{{invalid json")
        with patch.object(populate_slack_data, "_CLIENT_PROFILES_PATH", path):
            clients = populate_slack_data.get_clients()
        assert clients == populate_slack_data._FALLBACK_CLIENTS

    def test_empty_profiles_returns_fallback(self, tmp_path):
        path = str(tmp_path / "client_profiles.json")
        with open(path, "w") as f:
            json.dump({}, f)
        with patch.object(populate_slack_data, "_CLIENT_PROFILES_PATH", path):
            clients = populate_slack_data.get_clients(use_fallback_if_empty=True)
        assert clients == populate_slack_data._FALLBACK_CLIENTS
