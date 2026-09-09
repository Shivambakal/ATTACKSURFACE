"""Research workspace router — notes, tasks, findings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ResearchFinding, ResearchNote, ResearchTask, User, utcnow
from app.routers.deps import get_current_user
from app.schemas import (
    FindingCreate,
    FindingOut,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(prefix="/api/v1/research", tags=["research"])


# ── Notes ───────────────────────────────────────────────────────────

@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchNote:
    """Create a new research note."""
    note = ResearchNote(
        user_id=current_user.id,
        target_id=body.target_id,
        title=body.title,
        body=body.body,
        tags=body.tags or [],
        linked_change_id=body.linked_change_id,
        linked_asset_id=body.linked_asset_id,
        linked_evidence_id=body.linked_evidence_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes", response_model=list[NoteOut])
def list_notes(
    target_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchNote]:
    """List research notes for the authenticated user, optionally filtered by target."""
    query = db.query(ResearchNote).filter_by(user_id=current_user.id)
    if target_id is not None:
        query = query.filter_by(target_id=target_id)
    return query.order_by(ResearchNote.updated_at.desc()).all()


@router.get("/notes/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchNote:
    """Get a research note by ID."""
    note = db.get(ResearchNote, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchNote:
    """Update a research note."""
    note = db.get(ResearchNote, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")

    if body.title is not None:
        note.title = body.title
    if body.body is not None:
        note.body = body.body
    if body.tags is not None:
        note.tags = body.tags
    if body.target_id is not None:
        note.target_id = body.target_id
    if body.linked_change_id is not None:
        note.linked_change_id = body.linked_change_id
    if body.linked_asset_id is not None:
        note.linked_asset_id = body.linked_asset_id
    if body.linked_evidence_id is not None:
        note.linked_evidence_id = body.linked_evidence_id

    note.updated_at = utcnow()
    db.commit()
    db.refresh(note)
    return note


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a research note."""
    note = db.get(ResearchNote, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")

    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully"}


# ── Tasks ───────────────────────────────────────────────────────────

@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchTask:
    """Create a new research task."""
    task = ResearchTask(
        user_id=current_user.id,
        target_id=body.target_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        related_change_id=body.related_change_id,
        status="open",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    target_id: int | None = Query(default=None),
    task_status: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchTask]:
    """List research tasks for current user."""
    query = db.query(ResearchTask).filter_by(user_id=current_user.id)
    if target_id is not None:
        query = query.filter_by(target_id=target_id)
    if task_status is not None:
        query = query.filter_by(status=task_status)
    return query.order_by(ResearchTask.created_at.desc()).all()


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchTask:
    """Update an existing research task."""
    task = db.get(ResearchTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.status is not None:
        task.status = body.status
    if body.priority is not None:
        task.priority = body.priority
    if body.due_date is not None:
        task.due_date = body.due_date

    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


# ── Findings ────────────────────────────────────────────────────────

@router.post("/findings", response_model=FindingOut, status_code=status.HTTP_201_CREATED)
def create_finding(
    body: FindingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchFinding:
    """Record a new security research finding."""
    finding = ResearchFinding(
        user_id=current_user.id,
        target_id=body.target_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        status="draft",
        evidence_ids=body.evidence_ids or [],
        change_ids=body.change_ids or [],
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    target_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchFinding]:
    """List research findings for current user."""
    query = db.query(ResearchFinding).filter_by(user_id=current_user.id)
    if target_id is not None:
        query = query.filter_by(target_id=target_id)
    return query.order_by(ResearchFinding.created_at.desc()).all()
