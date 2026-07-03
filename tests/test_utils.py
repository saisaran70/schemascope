"""Tests for utils/ modules — Step 2."""
import pytest

# ---------------------------------------------------------------------------
# errors.py
# ---------------------------------------------------------------------------
from utils.errors import (
    AnalysisError,
    AuthenticationError,
    ConnectionError,
    DependencyError,
    ExportError,
    InvalidFileError,
    PermissionError,
    SchemaError,
    user_message_for,
    ERROR_MESSAGES,
)


class TestSchemaErrorHierarchy:
    def test_schema_error_is_exception(self):
        e = SchemaError("something went wrong")
        assert isinstance(e, Exception)

    def test_user_message_stored(self):
        e = SchemaError("user-facing text", technical_detail="stack trace here")
        assert e.user_message == "user-facing text"
        assert e.technical_detail == "stack trace here"

    def test_str_returns_user_message(self):
        e = SchemaError("display this")
        assert str(e) == "display this"

    def test_technical_detail_defaults_to_empty(self):
        e = SchemaError("msg")
        assert e.technical_detail == ""

    def test_connection_error_is_schema_error(self):
        assert issubclass(ConnectionError, SchemaError)

    def test_authentication_error_is_schema_error(self):
        assert issubclass(AuthenticationError, SchemaError)

    def test_permission_error_is_schema_error(self):
        assert issubclass(PermissionError, SchemaError)

    def test_invalid_file_error_is_schema_error(self):
        assert issubclass(InvalidFileError, SchemaError)

    def test_analysis_error_is_schema_error(self):
        assert issubclass(AnalysisError, SchemaError)

    def test_export_error_is_schema_error(self):
        assert issubclass(ExportError, SchemaError)

    def test_dependency_error_is_schema_error(self):
        assert issubclass(DependencyError, SchemaError)

    def test_can_raise_and_catch_subclass_as_schema_error(self):
        with pytest.raises(SchemaError):
            raise ConnectionError("cannot connect")

    def test_each_subclass_carries_user_message(self):
        for cls in (
            ConnectionError,
            AuthenticationError,
            PermissionError,
            InvalidFileError,
            AnalysisError,
            ExportError,
            DependencyError,
        ):
            e = cls("test message")
            assert e.user_message == "test message"

    def test_technical_detail_on_subclass(self):
        e = AnalysisError("could not read", technical_detail="PRAGMA failed")
        assert e.technical_detail == "PRAGMA failed"


class TestUserMessageFor:
    def test_known_code_returns_prd_message(self):
        msg = user_message_for("invalid_sqlite_file")
        assert "not a valid" in msg.lower()

    def test_unsupported_extension(self):
        msg = user_message_for("unsupported_extension")
        assert ".db" in msg or ".sqlite" in msg

    def test_file_locked(self):
        msg = user_message_for("file_locked")
        assert "lock" in msg.lower()

    def test_auth_failed(self):
        msg = user_message_for("auth_failed")
        assert "password" in msg.lower() or "username" in msg.lower() or "credentials" in msg.lower() or "verify" in msg.lower()

    def test_host_unreachable(self):
        msg = user_message_for("host_unreachable")
        assert "host" in msg.lower() or "port" in msg.lower() or "network" in msg.lower()

    def test_database_not_found(self):
        msg = user_message_for("database_not_found")
        assert "database" in msg.lower()

    def test_mongodb_uri_invalid(self):
        msg = user_message_for("mongodb_uri_invalid")
        assert "uri" in msg.lower() or "format" in msg.lower()

    def test_permission_denied(self):
        msg = user_message_for("permission_denied")
        assert "permission" in msg.lower() or "read" in msg.lower() or "account" in msg.lower()

    def test_driver_missing(self):
        msg = user_message_for("driver_missing")
        assert "install" in msg.lower() or "driver" in msg.lower()

    def test_timeout(self):
        msg = user_message_for("timeout")
        assert "timeout" in msg.lower() or "network" in msg.lower()

    def test_unknown_code_returns_fallback(self):
        msg = user_message_for("totally_unknown_code")
        assert msg == "An unexpected error occurred."

    def test_custom_fallback(self):
        msg = user_message_for("nonexistent", fallback="Custom fallback.")
        assert msg == "Custom fallback."

    def test_all_prd_codes_present(self):
        expected_codes = {
            "invalid_sqlite_file", "unsupported_extension", "file_locked",
            "auth_failed", "host_unreachable", "database_not_found",
            "mongodb_uri_invalid", "permission_denied", "driver_missing", "timeout",
        }
        assert expected_codes.issubset(set(ERROR_MESSAGES.keys()))


# ---------------------------------------------------------------------------
# type_normalization.py
# ---------------------------------------------------------------------------
from utils.type_normalization import (
    normalize_sql_type,
    is_likely_date_type,
    is_likely_numeric_type,
    is_text_type,
)


class TestNormalizeSqlType:
    # Integer family
    def test_integer(self):
        assert normalize_sql_type("INTEGER") == "integer"

    def test_int(self):
        assert normalize_sql_type("INT") == "integer"

    def test_tinyint(self):
        assert normalize_sql_type("TINYINT") == "integer"

    def test_smallint(self):
        assert normalize_sql_type("SMALLINT") == "integer"

    def test_bigint(self):
        assert normalize_sql_type("BIGINT") == "integer"

    def test_int2(self):
        assert normalize_sql_type("INT2") == "integer"

    def test_int8(self):
        assert normalize_sql_type("INT8") == "integer"

    # Real family
    def test_real(self):
        assert normalize_sql_type("REAL") == "real"

    def test_float(self):
        assert normalize_sql_type("FLOAT") == "real"

    def test_double(self):
        assert normalize_sql_type("DOUBLE") == "real"

    def test_double_precision(self):
        assert normalize_sql_type("DOUBLE PRECISION") == "real"

    # Numeric / decimal
    def test_numeric(self):
        assert normalize_sql_type("NUMERIC") == "numeric"

    def test_decimal_with_precision(self):
        assert normalize_sql_type("DECIMAL(10,2)") == "numeric"

    def test_decimal_plain(self):
        assert normalize_sql_type("DECIMAL") == "numeric"

    # Text family
    def test_text(self):
        assert normalize_sql_type("TEXT") == "text"

    def test_varchar_with_length(self):
        assert normalize_sql_type("VARCHAR(255)") == "text"

    def test_nvarchar(self):
        assert normalize_sql_type("NVARCHAR(100)") == "text"

    def test_char(self):
        assert normalize_sql_type("CHAR(1)") == "text"

    def test_clob(self):
        assert normalize_sql_type("CLOB") == "text"

    def test_string(self):
        assert normalize_sql_type("STRING") == "text"

    # Boolean
    def test_boolean(self):
        assert normalize_sql_type("BOOLEAN") == "boolean"

    def test_bool(self):
        assert normalize_sql_type("BOOL") == "boolean"

    # Blob
    def test_blob(self):
        assert normalize_sql_type("BLOB") == "blob"

    def test_binary(self):
        assert normalize_sql_type("BINARY") == "blob"

    # Temporal
    def test_datetime(self):
        assert normalize_sql_type("DATETIME") == "datetime"

    def test_timestamp(self):
        assert normalize_sql_type("TIMESTAMP") == "datetime"

    def test_date(self):
        assert normalize_sql_type("DATE") == "date"

    def test_time(self):
        assert normalize_sql_type("TIME") == "time"

    # JSON
    def test_json(self):
        assert normalize_sql_type("JSON") == "json"

    def test_jsonb(self):
        assert normalize_sql_type("JSONB") == "json"

    # Case insensitivity
    def test_lowercase_input(self):
        assert normalize_sql_type("integer") == "integer"

    def test_mixed_case_input(self):
        assert normalize_sql_type("Varchar(50)") == "text"

    # Edge cases
    def test_empty_string_returns_unknown(self):
        assert normalize_sql_type("") == "unknown"

    def test_whitespace_only_returns_unknown(self):
        assert normalize_sql_type("   ") == "unknown"

    def test_completely_unknown_type(self):
        assert normalize_sql_type("GEOMETRY") == "unknown"

    def test_leading_trailing_whitespace_stripped(self):
        assert normalize_sql_type("  INTEGER  ") == "integer"


class TestIsLikelyDateType:
    def test_datetime_is_date_type(self):
        assert is_likely_date_type("DATETIME") is True

    def test_date_is_date_type(self):
        assert is_likely_date_type("DATE") is True

    def test_time_is_date_type(self):
        assert is_likely_date_type("TIME") is True

    def test_timestamp_is_date_type(self):
        assert is_likely_date_type("TIMESTAMP") is True

    def test_text_is_not_date_type(self):
        assert is_likely_date_type("TEXT") is False

    def test_integer_is_not_date_type(self):
        assert is_likely_date_type("INTEGER") is False


class TestIsLikelyNumericType:
    def test_integer_is_numeric(self):
        assert is_likely_numeric_type("INTEGER") is True

    def test_real_is_numeric(self):
        assert is_likely_numeric_type("REAL") is True

    def test_decimal_is_numeric(self):
        assert is_likely_numeric_type("DECIMAL") is True

    def test_text_is_not_numeric(self):
        assert is_likely_numeric_type("TEXT") is False

    def test_blob_is_not_numeric(self):
        assert is_likely_numeric_type("BLOB") is False


class TestIsTextType:
    def test_text_is_text(self):
        assert is_text_type("TEXT") is True

    def test_varchar_is_text(self):
        assert is_text_type("VARCHAR(100)") is True

    def test_integer_is_not_text(self):
        assert is_text_type("INTEGER") is False

    def test_blob_is_not_text(self):
        assert is_text_type("BLOB") is False


# ---------------------------------------------------------------------------
# masking.py
# ---------------------------------------------------------------------------
from utils.masking import mask_uri, mask_kv, mask_connection_string, safe_source_name, MASK


class TestMaskUri:
    def test_mysql_uri_password_masked(self):
        result = mask_uri("mysql://user:s3cr3t@localhost/db")
        assert "s3cr3t" not in result
        assert MASK in result
        assert "user" in result
        assert "localhost" in result

    def test_mongodb_uri_password_masked(self):
        result = mask_uri("mongodb://admin:p%40ss@cluster.net/mydb")
        assert "p%40ss" not in result
        assert MASK in result

    def test_mongodb_srv_uri_password_masked(self):
        result = mask_uri("mongodb+srv://user:hunter2@cluster0.mongodb.net/prod")
        assert "hunter2" not in result
        assert MASK in result

    def test_sqlite_uri_no_password_unchanged(self):
        uri = "sqlite:///path/to/file.db"
        result = mask_uri(uri)
        assert result == uri

    def test_uri_without_password_unchanged(self):
        uri = "http://example.com/api"
        result = mask_uri(uri)
        assert result == uri

    def test_empty_string_unchanged(self):
        assert mask_uri("") == ""

    def test_mask_token_appears_once(self):
        result = mask_uri("mysql://user:secret@host/db")
        assert result.count(MASK) == 1

    def test_username_preserved(self):
        result = mask_uri("mysql://alice:password@host/db")
        assert "alice" in result

    def test_host_preserved(self):
        result = mask_uri("mysql://user:pw@myhost.example.com/db")
        assert "myhost.example.com" in result

    def test_database_name_preserved(self):
        result = mask_uri("mysql://user:pw@host/mydatabase")
        assert "mydatabase" in result


class TestMaskKv:
    def test_password_kv_masked(self):
        result = mask_kv("host=localhost;password=mysecret;port=3306")
        assert "mysecret" not in result
        assert MASK in result

    def test_passwd_kv_masked(self):
        result = mask_kv("passwd=abc123")
        assert "abc123" not in result

    def test_pwd_kv_masked(self):
        result = mask_kv("user=root;pwd=topsecret")
        assert "topsecret" not in result

    def test_secret_kv_masked(self):
        result = mask_kv("secret=xyzzy")
        assert "xyzzy" not in result

    def test_non_credential_keys_unchanged(self):
        text = "host=localhost;port=3306;database=mydb"
        assert mask_kv(text) == text

    def test_case_insensitive_key_matching(self):
        result = mask_kv("PASSWORD=Secret123")
        assert "Secret123" not in result

    def test_empty_string_unchanged(self):
        assert mask_kv("") == ""


class TestMaskConnectionString:
    def test_uri_with_password(self):
        result = mask_connection_string("mysql://user:secret@host/db")
        assert "secret" not in result

    def test_kv_password(self):
        result = mask_connection_string("host=localhost;password=topsecret")
        assert "topsecret" not in result

    def test_plain_text_no_credentials_unchanged(self):
        text = "Just a plain description"
        assert mask_connection_string(text) == text

    def test_empty_string_unchanged(self):
        assert mask_connection_string("") == ""


class TestSafeSourceName:
    def test_bare_filename_unchanged(self):
        assert safe_source_name("mydb.sqlite") == "mydb.sqlite"

    def test_unix_path_stripped_to_filename(self):
        assert safe_source_name("/home/user/data/mydb.db") == "mydb.db"

    def test_windows_path_stripped_to_filename(self):
        assert safe_source_name("C:\\Users\\saisa\\data\\test.sqlite") == "test.sqlite"

    def test_database_name_no_path(self):
        assert safe_source_name("production_db") == "production_db"

    def test_empty_string_unchanged(self):
        assert safe_source_name("") == ""

    def test_single_slash_edge_case(self):
        result = safe_source_name("/mydb.db")
        assert result == "mydb.db"
