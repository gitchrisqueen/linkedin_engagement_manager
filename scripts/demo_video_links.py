"""Print the tagged trial link for each of the three demo videos' YouTube descriptions (issue #2379).

    export BRAND_SIGNUP_URL=...   # the BRAND_SIGNUP_URL value in the production deployment's .env
    poetry run python scripts/demo_video_links.py

The three demo videos are the recordings of the three scenes `scripts/seed_demo_account.py` seeds
(`demo1`, `demo2`, `demo3`; see `docs/demo-recording.md`). Each one gets the same link a tutorial
video's description gets from `description_with_cta`: the trial signup URL, tagged
`utm_source=youtube`, `utm_medium=video`, `utm_content=video-description`, with the campaign from
`campaign_for_tutorial(<scene>)`. Nothing is spelled by hand, so a breakdown by campaign reads these
videos the same way it reads every other tutorial.

The landing page is `BRAND_SIGNUP_URL`, else `PUBLIC_BASE_URL`, read from the process environment
only: the script never loads a `.env` file, and `scripts/` is not in the production image. So export
one of the two in the shell first, copying the value from the production deployment's `.env` (if
only `PUBLIC_BASE_URL` is set there, export that instead). With neither set there is no link to
publish: the script prints nothing to stdout, names both variables on stderr and exits 2.

Output is one tab-separated line per video: the scene, a tab, then the URL.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Printing three links is not worth a telemetry event (issue #1661); set before cqc_lem builds its
# handlers at import time.
os.environ.setdefault("LEM_TELEMETRY_MUTED", "1")

from cqc_lem.utilities.marketing.attribution import (  # noqa: E402
    MEDIUM_VIDEO,
    PLACEMENT_VIDEO_DESCRIPTION,
    SOURCE_YOUTUBE,
    campaign_for_tutorial,
    signup_url,
)

EXIT_OK, EXIT_NO_LANDING = 0, 2

#: The three demo videos, one per scene of `scripts/seed_demo_account.py` (its `SCENES`). The scene
#: name is the flow key, so the campaign is `tutorial-demo1` and so on.
DEMO_VIDEOS = ("demo1", "demo2", "demo3")


def demo_video_links() -> dict[str, str]:
    """The tagged description link for each demo video, keyed by scene.

    Returns:
        `{scene: url}` in `DEMO_VIDEOS` order. A value is empty when no landing page is configured.
    """
    return {
        scene: signup_url(SOURCE_YOUTUBE, MEDIUM_VIDEO, campaign_for_tutorial(scene),
                          content=PLACEMENT_VIDEO_DESCRIPTION)
        for scene in DEMO_VIDEOS
    }


def main(argv: Optional[list[str]] = None) -> int:
    """Print one line per demo video: the scene, a tab, then the URL.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `EXIT_OK`, or `EXIT_NO_LANDING` when neither `BRAND_SIGNUP_URL` nor `PUBLIC_BASE_URL` is set.
    """
    argparse.ArgumentParser(description=__doc__.split("\n", 1)[0]).parse_args(argv)
    links = demo_video_links()
    if not all(links.values()):
        sys.stderr.write("No landing page configured: set BRAND_SIGNUP_URL or PUBLIC_BASE_URL.\n")
        return EXIT_NO_LANDING
    for scene, url in links.items():
        sys.stdout.write(f"{scene}\t{url}\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
