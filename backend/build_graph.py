import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Note, Link

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Knowledge Graph Engine"])

# PARA Framework Color Palette
PARA_COLORS = {
    "Projects": {"background": "#8b5cf6", "border": "#a78bfa", "highlight": "#c4b5fd"},
    "Areas": {"background": "#06b6d4", "border": "#22d3ee", "highlight": "#67e8f9"},
    "Resources": {"background": "#10b981", "border": "#34d399", "highlight": "#6ee7b7"},
    "Archives": {"background": "#f59e0b", "border": "#fbbf24", "highlight": "#fde68a"},
    "Default": {"background": "#6b7280", "border": "#9ca3af", "highlight": "#d1d5db"}
}

SOURCE_ICONS = {
    "pdf": "📄",
    "docx": "📝",
    "image": "🖼️",
    "audio": "🎙️",
    "csv": "📊",
    "link": "🌐",
    "note": "✍️"
}

@router.get("")
async def get_graph_topology(
    category: Optional[str] = Query(None, description="Filter by PARA Category"),
    source_type: Optional[str] = Query(None, description="Filter by source format"),
    search: Optional[str] = Query(None, description="Filter by search query"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Serialize knowledge graph topology for vis-network rendering:
    - Nodes with PARA color schemes, degree-based radius, and metadata tooltips.
    - Edges with similarity weights and interactive hover labels.
    """
    # 1. Query Notes
    stmt = select(Note)
    if category and category.lower() != "all":
        stmt = stmt.where(Note.category == category)
    if source_type and source_type.lower() != "all":
        stmt = stmt.where(Note.source_type == source_type)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Note.title.ilike(search_pattern),
                Note.summary.ilike(search_pattern)
            )
        )

    res = await db.execute(stmt)
    notes = res.scalars().all()
    note_ids = {n.id for n in notes}

    if not notes:
        return {
            "nodes": [],
            "edges": [],
            "stats": {
                "total_nodes": 0,
                "total_edges": 0,
                "categories": {}
            }
        }

    # 2. Query Links between visible notes
    links_stmt = select(Link).where(
        Link.source_note_id.in_(note_ids) & Link.target_note_id.in_(note_ids)
    )
    links_res = await db.execute(links_stmt)
    links = links_res.scalars().all()

    # Calculate node degrees
    node_degrees: Dict[str, int] = {n.id: 0 for n in notes}
    for link in links:
        node_degrees[link.source_note_id] = node_degrees.get(link.source_note_id, 0) + 1
        node_degrees[link.target_note_id] = node_degrees.get(link.target_note_id, 0) + 1

    # 3. Format Nodes for vis-network
    nodes_data = []
    category_counts: Dict[str, int] = {"Projects": 0, "Areas": 0, "Resources": 0, "Archives": 0}

    for note in notes:
        cat = note.category or "Resources"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        color_scheme = PARA_COLORS.get(cat, PARA_COLORS["Default"])
        icon = SOURCE_ICONS.get(note.source_type, "📄")
        degree = node_degrees.get(note.id, 0)

        # Label truncate
        display_label = note.title if len(note.title) <= 22 else f"{note.title[:20]}..."

        tooltip_html = (
            f"<b>{icon} {note.title}</b><br/>"
            f"<i>Category:</i> {cat}<br/>"
            f"<i>Format:</i> {note.source_type.upper()}<br/>"
            f"<i>Degree:</i> {degree} connections<br/>"
            f"<hr/>{note.summary[:150] if note.summary else 'No summary'}..."
        )

        nodes_data.append({
            "id": note.id,
            "label": display_label,
            "title": tooltip_html,
            "category": cat,
            "source_type": note.source_type,
            "full_title": note.title,
            "summary": note.summary or "",
            "shape": "dot",
            "value": 12 + min(degree * 4, 30),  # Node size scaling with degree
            "color": {
                "background": color_scheme["background"],
                "border": color_scheme["border"],
                "highlight": {
                    "background": color_scheme["highlight"],
                    "border": "#ffffff"
                },
                "hover": {
                    "background": color_scheme["highlight"],
                    "border": color_scheme["border"]
                }
            },
            "font": {
                "color": "#f3f4f6",
                "size": 13,
                "face": "Inter, sans-serif"
            },
            "shadow": {
                "enabled": True,
                "color": "rgba(0,0,0,0.5)",
                "size": 6
            }
        })

    # 4. Format Edges
    edges_data = []
    for link in links:
        score = link.similarity_score
        edges_data.append({
            "id": link.id,
            "from": link.source_note_id,
            "to": link.target_note_id,
            "value": max(1, int(score * 5)),
            "title": f"Cosine Similarity: {score:.2f}",
            "color": {
                "color": "rgba(139, 92, 246, 0.45)",
                "highlight": "#c4b5fd",
                "hover": "#a78bfa"
            },
            "smooth": {
                "type": "continuous",
                "roundness": 0.2
            }
        })

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "stats": {
            "total_nodes": len(nodes_data),
            "total_edges": len(edges_data),
            "categories": category_counts
        }
    }
