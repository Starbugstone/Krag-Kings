"""Bounded oral/profile fit from v9p, excluding rejected v9qa orbit compression."""
from pathlib import Path
import sys
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from profile_and_lip import Profile, distances, smooth, member


class OralProfile(Profile):
    oral_translation = np.asarray((0., .010, .008))

    def __init__(self, points, edges, masks, eyes, eye_radii, held_optical):
        super().__init__(points, edges, masks, eyes, eye_radii)
        # The complete closed oral bag must accompany the dental/tongue
        # translation. A lip-only spatial fade pinches its folded inner walls.
        self.oral_distance = distances(points, edges, self.upper | self.lower | member(masks, 7))
        self.oral_support = 1-smooth((self.oral_distance-.012)/.048)
        self.oral_support[self.oral_distance >= .060] = 0
        distance = distances(points, edges, held_optical)
        self.nasal_support = smooth(distance/.012)

    def nasal(self, points):
        delta = super().nasal(points)
        # v9p has not undergone the rejected reference-driven alar shrink.
        delta[:, 0] *= .05/.35
        delta[:, 1] *= .003/.008
        return delta

    def head(self, points):
        p = np.asarray(points, float)
        if len(p) != len(self.oral_support):
            raise RuntimeError('Profile needs actual unchanged Head indexing')
        return p+self.nasal(p)*self.nasal_support[:, None]+self.oral_support[:, None]*self.oral_translation
