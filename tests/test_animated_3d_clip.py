import math
import sys
from pathlib import Path
import pytest
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.engine_3d import Engine3D


def test_3d_rotation_cache():
    """Verify 3D rotation caching without full video rendering."""
    steps = 4
    radius = 60
    cache = Engine3D.preload_3d_rotation_cache(planet_type="saturn", steps=steps, radius=radius)
    assert len(cache) == steps
    assert all(isinstance(f, Image.Image) for f in cache)


@pytest.mark.slow
def test_animated_3d_single_frame():
    """Verify single-frame composition of 3D layered scene."""
    width, height = 540, 960
    radius = 120
    cx, cy = width // 2, int(height * 0.42)
    px, py = cx - radius, cy - radius

    base_space = Engine3D.create_space_backdrop(width, height, t=0.0)
    assert base_space.size == (width, height)

    cache = Engine3D.preload_3d_rotation_cache(planet_type="saturn", steps=2, radius=radius)
    frame = base_space.copy()
    planet_img = cache[0].resize((radius * 2, radius * 2))
    frame.paste(planet_img, (px, py), planet_img)
    arr = np.array(frame)
    assert arr.shape == (height, width, 4) or arr.shape == (height, width, 3)
