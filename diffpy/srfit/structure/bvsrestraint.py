########################################################################
#
# diffpy.srfit      by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Chris Farrow
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
########################################################################
"""Bond-valence sum calculator from SrReal wrapped as a Restraint.

This can be used as an addition to a cost function during a structure
refinement to keep the bond-valence sum within tolerable limits.

"""

__all__ = ["BVSRestraint"]

from diffpy.srfit.fitbase.restraint import Restraint

from diffpy.srreal.bvscalculator import BVSCalculator

class BVSRestraint(Restraint):
    """Wrapping of BVSCalculator.bvmsdiff as a Restraint.

    The restraint penalty is the root-mean-square deviation of the theoretical
    and calculated bond-valence sum of a structure.

    Attributes:
    _calc   --  The SrReal BVSCalculator instance.
    _stru   --  Structure object supported by SrReal. This is the
                structure from which the bond-valence sum is calculated.
    sig     --  The uncertainty on the BVS (default 1).
    scaled  --  A flag indicating if the restraint is scaled (multiplied)
                by the unrestrained point-average chi^2 (chi^2/numpoints)
                (default False).

    """

    def __init__(self, stru, sig = 1, scaled = False):
        """Initialize the Restraint.

        stru    --  Structure object supported by BVSCalculator.
        sig     --  The uncertainty on the BVS (default 1).
        scaled  --  A flag indicating if the restraint is scaled
                    (multiplied) by the unrestrained point-average chi^2
                    (chi^2/numpoints) (bool, default False).

        """
        self._calc = BVSCalculator()
        self._stru = stru
        self.sig = float(sig)
        self.scaled = bool(scaled)
        return

    def penalty(self, w = 1.0):
        """Calculate the penalty of the restraint.

        w   --  The point-average chi^2 which is optionally used to scale the
                penalty (float, default 1.0).
        
        """
        # Get the bvms from the BVSCalculator
        self._calc.eval(self._stru)
        penalty = self._calc.bvmsdiff

        # Scale by the prefactor
        penalty /= self.sig**2

        # Optionally scale by w
        if self.scaled: penalty *= w

        return penalty

    def _validate(self):
        """This evaluates the calculator.

        Raises AttributeError if validation fails.
        
        """
        from numpy import nan
        p = self.penalty()
        if p is None or p is nan:
            raise AttributeError("Cannot evaluate penalty")

        return

    # End of class BVSRestraint

# End of file
