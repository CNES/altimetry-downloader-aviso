import pytest

from altimetry_downloader_aviso.catalog_client.geonetwork.query_builder import (
    ClauseType,
    Field,
    GeoNetworkQueryBuilder,
    Operator,
)

VALID_FIELD = "platforms"
INVALID_FIELD = "invalid_field"


def test_must_match_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.must_match(Field.PLATFORMS, "SWOT").build()

    assert "must" in payload["query"]["bool"]
    assert payload["query"]["bool"]["must"][0] == {"match": {"platforms": "SWOT"}}


def test_not_match_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.must_not_match(Field.PLATFORMS, "SWOT").build()

    assert "must_not" in payload["query"]["bool"]
    assert payload["query"]["bool"]["must_not"][0] == {"match": {"platforms": "SWOT"}}


def test_must_term_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.must_term(Field.ID, "some-id").build()

    assert "must" in payload["query"]["bool"]
    assert payload["query"]["bool"]["must"][0] == {"term": {"_id": "some-id"}}


def test_must_terms_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.must_terms(Field.ID, ["id1", "id2"]).build()

    assert "must" in payload["query"]["bool"]
    assert payload["query"]["bool"]["must"][0] == {"terms": {"_id": ["id1", "id2"]}}


def test_must_not_term_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.must_not_term(Field.ID, "some-id").build()

    assert "must_not" in payload["query"]["bool"]
    assert payload["query"]["bool"]["must_not"][0] == {"term": {"_id": "some-id"}}


def test_should_match_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.should_match(Field.PLATFORMS, "Sentinel-3").build()

    assert "should" in payload["query"]["bool"]
    assert payload["query"]["bool"]["should"][0] == {
        "match": {"platforms": "Sentinel-3"}
    }


def test_filter_range_clause():
    builder = GeoNetworkQueryBuilder()
    payload = builder.filter_range(
        Field.DATE, {"gte": "2020-01-01", "lte": "2022-01-01"}
    ).build()

    assert "filter" in payload["query"]["bool"]
    assert payload["query"]["bool"]["filter"][0] == {
        "range": {"date": {"gte": "2020-01-01", "lte": "2022-01-01"}}
    }


def test_combined_clauses():
    builder = GeoNetworkQueryBuilder()
    payload = (
        builder.must_match(Field.PLATFORMS, "SWOT")
        .must_not_term(Field.ID, "123")
        .should_term(Field.PLATFORMS, "Sentinel-3")
        .filter_term(Field.DATA_CENTER, "CDS-AVISO")
        .build()
    )

    bool_query = payload["query"]["bool"]
    assert "must" in bool_query
    assert "must_not" in bool_query
    assert "should" in bool_query
    assert "filter" in bool_query

    assert bool_query["must"][0]["match"]["platforms"] == "SWOT"
    assert bool_query["must_not"][0]["term"]["_id"] == "123"


def test_invalid_field_raises_error():
    builder = GeoNetworkQueryBuilder()
    with pytest.raises(AttributeError):
        builder.must_match("bad", "test")


def test_invalid_operator_raises_error():
    builder = GeoNetworkQueryBuilder()
    with pytest.raises(AttributeError):
        builder._add_clause(
            ClauseType.MUST, "unsupported_operator", Field.PLATFORMS, "test"
        )


def test_invalid_clause_type_raises_error():
    builder = GeoNetworkQueryBuilder()
    with pytest.raises(KeyError):
        builder._add_clause("invalid_clause", Operator.MATCH, Field.PLATFORMS, "test")
