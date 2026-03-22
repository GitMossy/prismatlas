"""
Link Template Applier — FR-4.5.4

Applies active LinkTemplates to a newly created Object by auto-creating
Relationship rows (subject to cycle detection).

Called from the objects POST endpoint after the new object is committed.
"""
from sqlalchemy.orm import Session

from app.models.link_template import LinkTemplate
from app.models.object import Object
from app.models.dependency import Relationship
from app.engines.cycle_detection import assert_no_cycle


def apply(new_object: Object, db: Session) -> None:
    """
    Query all active LinkTemplates scoped to new_object.project_id and
    auto-create Relationship rows where:
      1. Template source_object_type matches new_object.object_type
         → create edges: new_object → each existing target-typed object
      2. Template target_object_type matches new_object.object_type
         → create edges: each existing source-typed object → new_object

    Cycle-safe: calls assert_no_cycle before each creation; skips with a
    warning if a cycle would result.
    """
    templates = (
        db.query(LinkTemplate)
        .filter(
            LinkTemplate.project_id == new_object.project_id,
            LinkTemplate.is_active.is_(True),
        )
        .all()
    )

    for tmpl in templates:
        # Case 1: new_object is the source
        if tmpl.source_object_type == new_object.object_type:
            targets = (
                db.query(Object)
                .filter(
                    Object.project_id == new_object.project_id,
                    Object.object_type == tmpl.target_object_type,
                    Object.id != new_object.id,
                )
                .all()
            )
            for target in targets:
                try:
                    assert_no_cycle(new_object.id, target.id, db)
                except ValueError as exc:
                    print(
                        f"[link_template_applier] Skipping {new_object.id} → {target.id} "
                        f"(template '{tmpl.name}'): {exc}"
                    )
                    continue
                rel = Relationship(
                    source_entity_type="object",
                    source_entity_id=new_object.id,
                    target_entity_type="object",
                    target_entity_id=target.id,
                    relationship_type="object_to_object",
                    is_mandatory=False,
                    notes=f"Auto-created by LinkTemplate '{tmpl.name}'",
                )
                db.add(rel)

        # Case 2: new_object is the target
        if tmpl.target_object_type == new_object.object_type:
            sources = (
                db.query(Object)
                .filter(
                    Object.project_id == new_object.project_id,
                    Object.object_type == tmpl.source_object_type,
                    Object.id != new_object.id,
                )
                .all()
            )
            for source in sources:
                try:
                    assert_no_cycle(source.id, new_object.id, db)
                except ValueError as exc:
                    print(
                        f"[link_template_applier] Skipping {source.id} → {new_object.id} "
                        f"(template '{tmpl.name}'): {exc}"
                    )
                    continue
                rel = Relationship(
                    source_entity_type="object",
                    source_entity_id=source.id,
                    target_entity_type="object",
                    target_entity_id=new_object.id,
                    relationship_type="object_to_object",
                    is_mandatory=False,
                    notes=f"Auto-created by LinkTemplate '{tmpl.name}'",
                )
                db.add(rel)

    db.commit()
