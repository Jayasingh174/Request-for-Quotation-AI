from fastapi import APIRouter, Body, Response
import io
import csv

router = APIRouter(prefix="/export", tags=["Export"])

@router.post("/conflicts")
async def export_conflicts_csv(analysis_data: dict = Body(...)):
    """
    Receives the JSON conflict report from the frontend and
    returns it as a downloadable CSV file.
    """
    # Create an in-memory string buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. CSV header
    writer.writerow(["Item Name", "Conflict Status", "Source Quantities"])

    # 2. Extract matrix (Safely fall back to empty list if missing)
    matrix = analysis_data.get("full_matrix") or analysis_data.get("conflict_details") or []

    # 3. Populate rows
    for item in matrix:
        name = item.get("entity", "Unknown")
        status = "⚠️ CONFLICT" if item.get("conflict_detected") else "✅ MATCH"

        # Format quantities cleanly (e.g., "DocA: 5 | DocB: 4")
        quantities = item.get("quantities", {})
        qty_string = " | ".join([f"{source}: {qty}" for source, qty in quantities.items()])

        writer.writerow([name, status, qty_string])

    # 4. Return as a direct file download response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="conflict_report.csv"'}
    )