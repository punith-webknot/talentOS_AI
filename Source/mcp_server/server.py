import os
import random
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

# 1. Initialize the FastMCP server
mcp = FastMCP("CombinedServer")


@mcp.tool()
def get_benched_employee_data(
    department: Optional[str] = None,
    skill: Optional[str] = None,
    min_days_on_bench: int = 0
) -> List[Dict[str, Any]]:
    """Fetch the list of employees currently on the bench, optionally filtered by department, skill, or tenure on bench."""
    mock_data = [
        {"emp_id": "E1001", "name": "Alice Smith", "department": "Engineering", "skills": ["Python", "AWS"], "days_on_bench": 12},
        {"emp_id": "E1002", "name": "Bob Jones", "department": "Design", "skills": ["Figma", "UI/UX"], "days_on_bench": 5},
        {"emp_id": "E1003", "name": "Charlie Davis", "department": "Engineering", "skills": ["Java", "Spring"], "days_on_bench": 21},
        {"emp_id": "E1004", "name": "Diana Prince", "department": "Data", "skills": ["SQL", "Python", "Tableau"], "days_on_bench": 8}
    ]

    filtered_data = mock_data
    if department:
        filtered_data = [emp for emp in filtered_data if emp["department"].lower() == department.lower()]
    if skill:
        filtered_data = [emp for emp in filtered_data if skill.lower() in [s.lower() for s in emp["skills"]]]
    if min_days_on_bench > 0:
        filtered_data = [emp for emp in filtered_data if emp["days_on_bench"] >= min_days_on_bench]
        
    return filtered_data


@mcp.tool()
def get_query_band_levels(
    department: Optional[str] = None, 
    role_type: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve standard band levels, optionally filtered by department or role type (e.g., Technical, Management)."""
    mock_bands = [
        {"band": "Band 1", "title": "Junior Engineer", "department": "Engineering", "type": "Technical"},
        {"band": "Band 2", "title": "Mid-Level Engineer", "department": "Engineering", "type": "Technical"},
        {"band": "Band 3", "title": "Senior Engineer", "department": "Engineering", "type": "Technical"},
        {"band": "Band 3", "title": "Engineering Manager", "department": "Engineering", "type": "Management"},
        {"band": "Band 1", "title": "Junior Designer", "department": "Design", "type": "Creative"},
    ]
    
    filtered_bands = mock_bands
    if department:
        filtered_bands = [b for b in filtered_bands if b["department"].lower() == department.lower()]
    if role_type:
        filtered_bands = [b for b in filtered_bands if b["type"].lower() == role_type.lower()]
        
    return {
        "filters_applied": {"department": department, "role_type": role_type},
        "band_levels": filtered_bands
    }


@mcp.tool()
def post_job_post(
    title: str, 
    band_level: str, 
    job_description: str,
    screening_questions: List[str]
) -> Dict[str, Any]:
    """Create a new job posting with a comprehensive job description and dynamic AI-generated screening questions."""
    job_id = f"JOB-{(len(title) * 314) % 9999}"
    
    return {
        "status": "success",
        "message": f"Job post '{title}' created successfully.",
        "job_id": job_id,
        "details": {
            "title": title,
            "band_level": band_level,
            "job_description_snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description,
            "screening_questions_count": len(screening_questions),
            "questions_configured": screening_questions
        }
    }


@mcp.tool()
def delete_job_post(job_id: str) -> Dict[str, str]:
    """Delete an existing job posting by its ID."""
    return {
        "status": "success",
        "message": f"Job post with ID {job_id} has been deleted."
    }

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))
    
    # Run the server using the latest streamable HTTP transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)