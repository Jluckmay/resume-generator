"""Helpers for mapping generated resume content into editable form fields."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def manual_editor_state_from_cv(
    cv: Mapping[str, Any],
    extracted_sources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return Streamlit widget values corresponding to a generated structured CV."""

    def text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value if item is not None)
        return str(value)

    def records(key: str) -> list[Mapping[str, Any]]:
        value = cv.get(key)
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, Mapping)]

    education = records("education")
    experience = records("experience")
    projects = records("projects")
    publications = records("publications")
    awards = cv.get("awards")
    if not isinstance(awards, list):
        awards = []
    skills = records("skills")

    values: dict[str, Any] = {
        "manual_user_name": text(cv.get("name")),
        "manual_user_role": text(cv.get("title")),
        "manual_user_email": text(cv.get("email")),
        "manual_user_phone": text(cv.get("phone")),
        "manual_user_location": text(cv.get("location")),
        "man_summary": text(cv.get("summary")),
        "man_skills": "\n".join(
            f"{text(skill.get('category') or 'Habilidades')}: {text(skill.get('items'))}"
            for skill in skills
            if skill.get("items")
        ),
        "man_languages": (
            ", ".join(text(language) for language in cv.get("languages", []) if language)
            if isinstance(cv.get("languages"), list)
            else text(cv.get("languages"))
        ),
        "man_edu_count": max(1, len(education)),
        "man_exp_count": max(1, len(experience)),
        "man_proj_count": max(1, len(projects)),
        "man_pubs_count": max(1, len(publications)),
        "man_awards_count": max(1, len(awards)),
    }

    for index, item in enumerate(education):
        values.update({
            f"edu_deg_{index}": text(item.get("degree")),
            f"edu_inst_{index}": text(item.get("institution")),
            f"edu_period_{index}": text(item.get("period")),
            f"edu_det_{index}": text(item.get("details")),
        })

    for index, item in enumerate(experience):
        values.update({
            f"exp_role_{index}": text(item.get("role")),
            f"exp_org_{index}": text(item.get("organization")),
            f"exp_period_{index}": text(item.get("period")),
            f"exp_loc_{index}": text(item.get("location")),
            f"exp_desc_{index}": text(item.get("description") or item.get("bullets")),
        })

    for index, item in enumerate(projects):
        values.update({
            f"proj_name_{index}": text(item.get("name")),
            f"proj_tech_{index}": text(item.get("tech")),
            f"proj_url_{index}": text(item.get("url")),
            f"proj_desc_{index}": text(item.get("description")),
        })

    for index, item in enumerate(publications):
        values.update({
            f"pub_title_{index}": text(item.get("title")),
            f"pub_venue_{index}": text(item.get("venue")),
            f"pub_year_{index}": text(item.get("year")),
            f"pub_authors_{index}": text(item.get("authors")),
            f"pub_doi_{index}": text(item.get("doi")),
        })

    for index, award in enumerate(awards):
        if isinstance(award, Mapping):
            values.update({
                f"award_title_{index}": text(award.get("title")),
                f"award_year_{index}": text(award.get("year")),
                f"award_det_{index}": text(award.get("details")),
            })
        else:
            values.update({
                f"award_title_{index}": text(award),
                f"award_year_{index}": "",
                f"award_det_{index}": "",
            })

    links = (extracted_sources or {}).get("links", {})
    if isinstance(links, Mapping):
        values.update({
            "man_port": text(links.get("portfolio")),
            "man_gh": text(links.get("github")),
            "man_orcid": text(links.get("orcid")),
            "man_li": text(links.get("linkedin")),
            "man_lattes": text(links.get("lattes")),
        })

    return values
