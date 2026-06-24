from dataclasses import dataclass
from enum import Enum
from typing import Any


class Operator(Enum):
    """Type of query operator used in GeoNetwork queries."""

    MATCH = "match"
    TERM = "term"
    TERMS = "terms"
    RANGE = "range"


class Field(Enum):
    """Fields available for querying the GeoNetwork catalog."""

    DATA_CENTER = "th_odatis_centre_donnees.default"
    PLATFORMS = "platforms"
    ID = "_id"
    TITLE = "title"
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"
    DATE = "date"


class ClauseType(Enum):
    """Logical clause types used in boolean queries."""

    MUST = "must"
    MUST_NOT = "must_not"
    SHOULD = "should"
    FILTER = "filter"


@dataclass
class Clause:
    """Represents a single clause in a GeoNetwork query."""

    clause_type: ClauseType
    operator: Operator
    field: Field
    value: Any


class GeoNetworkQueryBuilder:
    """Builds a GeoNetwork-compatible Elasticsearch query.

    Supports combinations of `must`, `must_not`, `should`, and `filter` clauses
    using various operators (match, term, range).

    Methods allow chaining for fluent query construction.
    """

    def __init__(self):
        """Initializes a new empty query with default pagination (`from`=0,
        `size`=20)."""
        self._from = 0
        self._size = 20
        self.clauses: dict[ClauseType, list[dict[str, Any]]] = {
            ct: [] for ct in ClauseType
        }

    def _add_clause(
        self, clause_type: ClauseType, operator: Operator, field: Field, value: Any
    ):
        """Adds a clause to the query.

        Parameters
        ----------
        clause_type: ClauseType
            Logical operator type (must, should, etc.).
        operator: Operator
            Elasticsearch operator (match, term, range).
        field: Field
            Target field.
        value: Any
            Value to query (may be dict for range).

        Returns
        -------
            The builder instance (for chaining).
        """
        self.clauses[clause_type].append({operator.value: {field.value: value}})
        return self

    def must_match(self, field: Field, value: Any):
        """Adds a `must` clause with `match` operator."""
        return self._add_clause(ClauseType.MUST, Operator.MATCH, field, value)

    def must_term(self, field: Field, value: Any):
        """Adds a `must` clause with `term` operator."""
        return self._add_clause(ClauseType.MUST, Operator.TERM, field, value)

    def must_terms(self, field: Field, value: Any):
        """Adds a `must` clause with `term` operator."""
        return self._add_clause(ClauseType.MUST, Operator.TERMS, field, value)

    def must_not_match(self, field: Field, value: Any):
        """Adds a `must_not` clause with `match` operator."""
        return self._add_clause(ClauseType.MUST_NOT, Operator.MATCH, field, value)

    def must_not_term(self, field: Field, value: Any):
        """Adds a `must_not` clause with `term` operator."""
        return self._add_clause(ClauseType.MUST_NOT, Operator.TERM, field, value)

    def should_match(self, field: Field, value: Any):
        """Adds a `should` clause with `match` operator."""
        return self._add_clause(ClauseType.SHOULD, Operator.MATCH, field, value)

    def should_term(self, field: Field, value: Any):
        """Adds a `should` clause with `term` operator."""
        return self._add_clause(ClauseType.SHOULD, Operator.TERM, field, value)

    def filter_term(self, field: Field, value: Any):
        """Adds a `filter` clause with `term` operator."""
        return self._add_clause(ClauseType.FILTER, Operator.TERM, field, value)

    def filter_range(self, field: Field, range_query: dict[str, Any]):
        """Adds a `filter` clause with a `range` operator.

        Parameters
        ----------
        field: Field
            Field to apply the range on.
        range_query: dict[str, Any]
            Range specification, e.g. {'gte': '2023-01-01', 'lte': '2023-12-31'}.

        Returns
        -------
            The builder instance (for chaining).
        """
        return self._add_clause(ClauseType.FILTER, Operator.RANGE, field, range_query)

    def build(self) -> dict[str, Any]:
        """Builds and returns the final Elasticsearch query.

        Returns
        -------
            Elasticsearch-compatible query structure.
        """
        bool_query = {
            clause_type.value: clauses
            for clause_type, clauses in self.clauses.items()
            if clauses
        }

        return {"from": self._from, "size": self._size, "query": {"bool": bool_query}}
