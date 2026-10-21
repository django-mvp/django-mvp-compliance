"""Stub kinds of record for the FS-012 sketch.

Faked: the build replaces this with kinds the demo declares in its settings.
"""

from datetime import date

PROFILE = {
    "slug": "profile",
    "heading": "Your profile",
    "description": "The details on your account and the profile other members see.",
    "single": True,
    "labels": ["Name", "Email address", "Organisation", "Biography", "Website", "Joined"],
    "records": [
        [
            "Regular User",
            "regular.user@example.com",
            "Institut für Geowissenschaften, Universität Potsdam",
            "Hydrogeologist working on groundwater temperature in the North German Basin. "
            "Previously at the Helmholtz Centre for Environmental Research in Leipzig, "
            "where I spent six years on borehole heat-flow measurements.",
            None,
            date(2024, 3, 2),
        ]
    ],
}

LICENCES = ["CC BY 4.0", "CC0 1.0", "CC BY-SA 4.0"]

DATASETS = {
    "slug": "datasets",
    "heading": "Datasets you uploaded",
    "description": "Every dataset you uploaded, with its file.",
    "single": False,
    "labels": ["Title", "Licence", "Uploaded", "File"],
    "records": [
        [
            title,
            LICENCES[index % 3],
            date(2025, 1 + index % 12, 1 + index),
            {"name": f"{slug}.csv", "path": f"files/datasets/{slug}.csv"}
            if index % 7
            else None,
        ]
        for index, (title, slug) in enumerate(
            [
                (f"Borehole temperature profiles, survey {n}", f"borehole-survey-{n}")
                for n in range(1, 21)
            ]
            + [
                (
                    "Heat-flow density measurements from the Groß Schönebeck research "
                    "site, corrected for palaeoclimate and topography",
                    "gross-schoenebeck-heat-flow",
                ),
                ("Thermal conductivity, core samples", "thermal-conductivity"),
                ("Untitled upload", "upload"),
                ("Untitled upload", "upload-2"),
            ]
        )
    ],
}

COMMENTS = {
    "slug": "comments",
    "heading": "Comments you wrote",
    "description": "Comments you left on other people's datasets.",
    "single": False,
    "labels": ["On", "Comment", "Written"],
    "records": [
        [
            "Borehole temperature profiles, survey 3",
            "The depth column looks like it is in feet rather than metres for the last "
            "forty rows. Could you check against the field notes?",
            date(2025, 6, 14),
        ],
        ["Thermal conductivity, core samples", "Thanks, this is exactly what I needed.", date(2025, 9, 2)],
    ],
}

MESSAGES = {
    "slug": "messages",
    "heading": "Messages sent to you",
    "description": "Messages other members sent you through the site.",
    "single": False,
    "labels": ["From", "Subject", "Sent"],
    "records": [],
}


def sections(nothing: bool = False) -> list[dict]:
    """The project's kinds, as the sketch fakes them.

    Args:
        nothing: Return every kind with no records, for the empty state.
    """
    kinds = [PROFILE, DATASETS, COMMENTS, MESSAGES]
    if nothing:
        return [{**kind, "records": []} for kind in kinds]
    return kinds
