"""
Circular Dependency Detection — FR-4.5.3

Performs a DFS over the Relationship graph to detect cycles before a new
relationship or dependency rule is committed.  Returns the cycle path as a
list of entity IDs if found, or an empty list if the graph is acyclic.

Usage (in API handler, before db.commit()):
    cycle = find_cycle(source_id, target_id, entity_type, db)
    if cycle:
        raise HTTPException(400, detail=f"Circular dependency detected: {cycle}")
"""
import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.dependency import Relationship, DependencyRule


def _build_dependency_rule_adjacency(db: Session) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Build adjacency from DependencyRule rows where BOTH source_entity_id and target_entity_id are non-null.
    Type-level rules (null entity IDs) are skipped — only concrete entity-to-entity rules are included."""
    adjacency: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for rule in db.query(DependencyRule).filter(
        DependencyRule.source_entity_id.isnot(None),
        DependencyRule.target_entity_id.isnot(None),
    ).all():
        adjacency[rule.source_entity_id].append(rule.target_entity_id)
    return adjacency


def _build_adjacency(db: Session) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Load all Relationship rows AND entity-level DependencyRule rows into an adjacency list (source → [targets])."""
    adjacency: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for rel in db.query(Relationship).all():
        adjacency[rel.source_entity_id].append(rel.target_entity_id)
    # Merge DependencyRule edges (entity-level only, where both IDs are non-null)
    for node, neighbours in _build_dependency_rule_adjacency(db).items():
        adjacency[node].extend(neighbours)
    return adjacency


def find_cycle(
    new_source: uuid.UUID,
    new_target: uuid.UUID,
    db: Session,
) -> list[uuid.UUID]:
    """
    Return the cycle path (list of entity IDs) if adding an edge
    new_source → new_target would create a cycle.  Returns [] if safe.

    The check works by asking: can we reach new_source starting from new_target?
    If yes, adding new_source → new_target closes a cycle.
    """
    adjacency = _build_adjacency(db)
    # Temporarily add the proposed edge
    adjacency[new_source].append(new_target)

    visited: set[uuid.UUID] = set()
    path: list[uuid.UUID] = []

    def dfs(node: uuid.UUID) -> bool:
        if node in path:
            # Cycle detected — trim path to the cycle
            cycle_start = path.index(node)
            path[:] = path[cycle_start:]
            return True
        if node in visited:
            return False
        visited.add(node)
        path.append(node)
        for neighbour in adjacency.get(node, []):
            if dfs(neighbour):
                return True
        path.pop()
        return False

    # Check reachability from new_target back to new_source
    if dfs(new_target):
        return path
    return []


def assert_no_cycle(new_source: uuid.UUID, new_target: uuid.UUID, db: Session) -> None:
    """
    Raise ValueError with the cycle path if adding this edge would create a cycle.
    Call this before committing a new Relationship or DependencyRule.
    """
    cycle = find_cycle(new_source, new_target, db)
    if cycle:
        ids_str = " → ".join(str(eid) for eid in cycle)
        raise ValueError(f"Circular dependency detected: {ids_str}")
