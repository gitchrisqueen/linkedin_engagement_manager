"""Unit tests for the media-variant orchestrator."""

import json
import os
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


def _make_image(tmp_path):
    p = tmp_path / "src_img.webp"
    p.write_bytes(b"img-bytes")
    return str(p)


class TestGenerateMediaVariants:
    def test_happy_path_writes_metadata_and_urls(self, tmp_path):
        img = _make_image(tmp_path)

        def fake_save(url, d):
            path = os.path.join(d, "video.mp4")
            with open(path, "wb") as f:
                f.write(b"vid")
            return path

        with patch("cqc_lem.app.generate_variants.assets_dir", str(tmp_path)), \
             patch("cqc_lem.app.generate_variants.get_flux_image_prompt_from_ai", return_value="img prompt"), \
             patch("cqc_lem.app.generate_variants.generate_flux1_image_from_prompt", return_value=img), \
             patch("cqc_lem.app.generate_variants.get_runway_ml_video_prompt_from_ai", return_value="motion"), \
             patch("cqc_lem.app.generate_variants.create_runway_video", return_value="https://runway/v.mp4"), \
             patch("cqc_lem.app.generate_variants.save_video_url_to_dir", side_effect=fake_save):
            from cqc_lem.app.generate_variants import generate_media_variants
            payload = generate_media_variants(
                text="AI in healthcare",
                combos=[{"image_model": "black-forest-labs/flux-dev", "video_model": "gen4_turbo", "ratio": "1:1"}],
                timestamp=1000,
            )

        assert payload["batch_id"].startswith("1000_")
        v = payload["variants"][0]
        assert v["error"] is None
        assert "/api/assets?file_name=variants/" in v["image_url"]
        assert v["video_url"].endswith("variant_0_video.mp4")
        assert payload["total_estimated_cost_usd"] > 0

        meta_path = os.path.join(str(tmp_path), "variants", payload["batch_id"], "metadata.json")
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            data = json.load(f)
        assert data["request"]["text"] == "AI in healthcare"

    def test_requires_a_source(self):
        from cqc_lem.app.generate_variants import generate_media_variants
        with pytest.raises(ValueError):
            generate_media_variants()

    def test_per_combo_error_isolated(self, tmp_path):
        img = _make_image(tmp_path)
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return img

        with patch("cqc_lem.app.generate_variants.assets_dir", str(tmp_path)), \
             patch("cqc_lem.app.generate_variants.get_flux_image_prompt_from_ai", return_value="p"), \
             patch("cqc_lem.app.generate_variants.generate_flux1_image_from_prompt", side_effect=flaky), \
             patch("cqc_lem.app.generate_variants.get_runway_ml_video_prompt_from_ai", return_value="m"), \
             patch("cqc_lem.app.generate_variants.create_runway_video", return_value=None):
            from cqc_lem.app.generate_variants import generate_media_variants
            payload = generate_media_variants(
                text="x",
                combos=[{"include_video": False}, {"include_video": False}],
                timestamp=1,
            )

        assert payload["variants"][0]["error"] is not None
        assert payload["variants"][1]["error"] is None
        assert payload["variants"][1]["image_url"] is not None
